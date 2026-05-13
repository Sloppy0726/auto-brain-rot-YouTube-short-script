from __future__ import annotations

import json
import mimetypes
import os
import shutil
import subprocess
import uuid
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .captions import captions_to_srt, make_captions
from .models import Caption


class AudioError(RuntimeError):
    pass


OPENAI_TRANSCRIPTIONS_URL = "https://api.openai.com/v1/audio/transcriptions"


def probe_audio_duration(audio_path: Path) -> float:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise AudioError("ffprobe is not installed. Install ffmpeg with: brew install ffmpeg")
    if not audio_path.exists():
        raise AudioError(f"Audio file does not exist: {audio_path}")

    command = [
        ffprobe,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(audio_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise AudioError(result.stderr.strip() or f"Could not read audio duration: {audio_path}")

    try:
        duration = float(result.stdout.strip())
    except ValueError as exc:
        raise AudioError(f"Invalid audio duration from ffprobe: {result.stdout!r}") from exc

    if duration <= 0:
        raise AudioError(f"Audio duration must be greater than zero: {audio_path}")
    return round(duration, 2)


def sync_script_file_to_voiceover(
    script_json: Path,
    audio_path: Path,
    mode: str = "duration",
    transcription_model: str = "whisper-1",
    transcription_prompt: Optional[str] = None,
) -> Tuple[Dict[str, Any], float]:
    script = json.loads(script_json.read_text(encoding="utf-8"))
    if mode == "none":
        return script, float(script.get("estimated_seconds", 0.0))
    if mode == "word":
        return sync_script_file_to_word_timestamps(
            script_json=script_json,
            audio_path=audio_path,
            transcription_model=transcription_model,
            transcription_prompt=transcription_prompt,
        )
    if mode != "duration":
        raise AudioError(f"Unknown caption sync mode: {mode}")

    duration = probe_audio_duration(audio_path)
    captions = make_captions(str(script.get("narration", "")), duration)

    script["estimated_seconds"] = duration
    script["captions"] = [caption.to_dict() for caption in captions]
    script["caption_sync"] = {
        "method": "duration-proportional",
        "audio_path": str(audio_path),
        "audio_duration_seconds": duration,
        "note": "Caption chunks are spread across the actual voiceover duration. Use word-level transcription for tighter sync.",
    }

    script_json.write_text(json.dumps(script, indent=2), encoding="utf-8")
    srt_path = script_json.with_suffix(".srt")
    srt_path.write_text(captions_to_srt(captions), encoding="utf-8")
    return script, duration


def sync_script_file_to_word_timestamps(
    script_json: Path,
    audio_path: Path,
    transcription_model: str = "whisper-1",
    transcription_prompt: Optional[str] = None,
) -> Tuple[Dict[str, Any], float]:
    script = json.loads(script_json.read_text(encoding="utf-8"))
    transcription = transcribe_word_timestamps(
        audio_path=audio_path,
        model=transcription_model,
        prompt=transcription_prompt or str(script.get("narration", ""))[:220],
    )
    words = normalize_transcription_words(transcription.get("words", []))
    if not words:
        raise AudioError("Whisper did not return word timestamps for this audio.")

    duration = round(max(float(word["end"]) for word in words), 2)
    captions = make_captions_from_words(words)
    script["estimated_seconds"] = duration
    script["transcript_text"] = transcription.get("text", "")
    script["captions"] = [caption.to_dict() for caption in captions]
    script["caption_sync"] = {
        "method": "whisper-word",
        "model": transcription_model,
        "audio_path": str(audio_path),
        "audio_duration_seconds": duration,
        "word_count": len(words),
        "note": "Caption chunks are timed from Whisper word timestamps.",
    }

    script_json.write_text(json.dumps(script, indent=2), encoding="utf-8")
    srt_path = script_json.with_suffix(".srt")
    srt_path.write_text(captions_to_srt(captions), encoding="utf-8")
    transcript_path = script_json.with_suffix(".transcript.json")
    transcript_path.write_text(json.dumps(transcription, indent=2), encoding="utf-8")
    return script, duration


def transcribe_word_timestamps(
    audio_path: Path,
    model: str = "whisper-1",
    prompt: Optional[str] = None,
) -> Dict[str, Any]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise AudioError("OPENAI_API_KEY is not set. Required for --caption-sync word.")
    if model != "whisper-1":
        raise AudioError("Word timestamp transcription requires model='whisper-1'.")
    if not audio_path.exists():
        raise AudioError(f"Audio file does not exist: {audio_path}")

    fields = {
        "model": model,
        "response_format": "verbose_json",
        "timestamp_granularities[]": "word",
    }
    if prompt:
        fields["prompt"] = prompt

    body, content_type = multipart_body(fields=fields, file_path=audio_path)
    request = urllib.request.Request(
        OPENAI_TRANSCRIPTIONS_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": content_type,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise AudioError(f"OpenAI transcription error {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise AudioError(f"OpenAI transcription request failed: {exc.reason}") from exc


def multipart_body(fields: Dict[str, str], file_path: Path) -> Tuple[bytes, str]:
    boundary = f"----brainrot-{uuid.uuid4().hex}"
    chunks: List[bytes] = []
    for name, value in fields.items():
        chunks.extend(
            [
                f"--{boundary}\r\n".encode("utf-8"),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"),
                str(value).encode("utf-8"),
                b"\r\n",
            ]
        )

    mime_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
    chunks.extend(
        [
            f"--{boundary}\r\n".encode("utf-8"),
            (
                f'Content-Disposition: form-data; name="file"; filename="{file_path.name}"\r\n'
                f"Content-Type: {mime_type}\r\n\r\n"
            ).encode("utf-8"),
            file_path.read_bytes(),
            b"\r\n",
            f"--{boundary}--\r\n".encode("utf-8"),
        ]
    )
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def normalize_transcription_words(raw_words: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    words = []
    for item in raw_words:
        word = str(item.get("word", "")).strip()
        if not word:
            continue
        try:
            start = float(item["start"])
            end = float(item["end"])
        except (KeyError, TypeError, ValueError):
            continue
        if end <= start:
            continue
        words.append({"word": word, "start": start, "end": end})
    return words


def make_captions_from_words(
    words: List[Dict[str, Any]],
    max_words: int = 4,
    max_chars: int = 24,
    max_seconds: float = 1.8,
) -> List[Caption]:
    captions: List[Caption] = []
    chunk: List[Dict[str, Any]] = []

    def should_flush(next_word: Dict[str, Any]) -> bool:
        if not chunk:
            return False
        text = " ".join(str(item["word"]) for item in [*chunk, next_word])
        duration = float(next_word["end"]) - float(chunk[0]["start"])
        return len(chunk) >= max_words or len(text) > max_chars or duration > max_seconds

    def flush() -> None:
        if not chunk:
            return
        text = " ".join(str(item["word"]) for item in chunk).upper()
        captions.append(
            Caption(
                index=len(captions) + 1,
                start=round(float(chunk[0]["start"]), 2),
                end=round(float(chunk[-1]["end"]), 2),
                text=text,
            )
        )
        chunk.clear()

    for word in words:
        if should_flush(word):
            flush()
        chunk.append(word)
    flush()

    return captions


def captions_from_script(script: Dict[str, Any]):
    return [
        Caption(
            index=int(item["index"]),
            start=float(item["start"]),
            end=float(item["end"]),
            text=str(item["text"]),
        )
        for item in script.get("captions", [])
    ]

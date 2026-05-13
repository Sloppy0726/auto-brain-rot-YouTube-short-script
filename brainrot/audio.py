from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, Tuple

from .captions import captions_to_srt, make_captions
from .models import Caption


class AudioError(RuntimeError):
    pass


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


def sync_script_file_to_voiceover(script_json: Path, audio_path: Path) -> Tuple[Dict[str, Any], float]:
    script = json.loads(script_json.read_text(encoding="utf-8"))
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

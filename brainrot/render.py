from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

from .captions import captions_to_srt
from .files import slugify
from .models import Caption


class RenderError(RuntimeError):
    pass


def write_srt_from_json(script: Dict[str, Any], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    captions = [
        Caption(
            index=int(item["index"]),
            start=float(item["start"]),
            end=float(item["end"]),
            text=str(item["text"]),
        )
        for item in script.get("captions", [])
    ]
    path = out_dir / f"{slugify(script['title'])}.srt"
    path.write_text(captions_to_srt(captions), encoding="utf-8")
    return path


def render_short(
    script: Dict[str, Any],
    gameplay_path: Path,
    output_path: Path,
    audio_path: Optional[Path] = None,
    font_name: str = "Arial Black",
) -> Path:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RenderError("ffmpeg is not installed. Install it with: brew install ffmpeg")

    if not gameplay_path.exists():
        raise RenderError(f"Gameplay file does not exist: {gameplay_path}")
    if audio_path and not audio_path.exists():
        raise RenderError(f"Audio file does not exist: {audio_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    srt_path = write_srt_from_json(script, output_path.parent)
    duration = float(script.get("estimated_seconds", 55.0))

    subtitle_path = escape_filter_path(srt_path)
    force_style = (
        "FontName={font},FontSize=72,PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00000000,BorderStyle=1,Outline=4,Shadow=1,"
        "Alignment=5,MarginV=20"
    ).format(font=font_name)

    filter_complex = (
        f"[0:v]scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960[game];"
        f"color=c=#111111:s=1080x960:d={duration}[panel];"
        f"[panel]subtitles='{subtitle_path}':force_style='{force_style}'[caps];"
        f"[caps][game]vstack=inputs=2[v]"
    )

    command = [
        ffmpeg,
        "-y",
        "-stream_loop",
        "-1",
        "-i",
        str(gameplay_path),
    ]
    if audio_path:
        command.extend(["-i", str(audio_path)])

    command.extend(
        [
            "-t",
            str(duration),
            "-filter_complex",
            filter_complex,
            "-map",
            "[v]",
        ]
    )
    if audio_path:
        command.extend(["-map", "1:a", "-shortest"])
    else:
        command.append("-an")

    command.extend(
        [
            "-r",
            "30",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
    )

    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RenderError(result.stderr.strip() or "ffmpeg render failed")

    return output_path


def escape_filter_path(path: Path) -> str:
    return str(path).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")

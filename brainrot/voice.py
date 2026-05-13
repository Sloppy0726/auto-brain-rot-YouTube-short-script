from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

from .files import slugify


class VoiceError(RuntimeError):
    pass


def make_voiceover(script: Dict[str, Any], out_dir: Path, voice: Optional[str] = None) -> Path:
    say = shutil.which("say")
    if not say:
        raise VoiceError("macOS 'say' command was not found.")

    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / f"{slugify(script['title'])}.aiff"
    command = [say]
    if voice:
        command.extend(["-v", voice])
    command.extend(["-o", str(output_path), script["narration"]])

    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise VoiceError(result.stderr.strip() or "Voice generation failed")
    return output_path

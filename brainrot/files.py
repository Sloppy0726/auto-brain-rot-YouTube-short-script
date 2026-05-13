from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict

from .captions import captions_to_srt
from .models import ShortScript


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:80] or "short"


def write_script_bundle(script: ShortScript, out_dir: Path) -> Dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = slugify(script.title)
    json_path = out_dir / f"{slug}.json"
    md_path = out_dir / f"{slug}.md"
    srt_path = out_dir / f"{slug}.srt"

    json_path.write_text(json.dumps(script.to_dict(), indent=2), encoding="utf-8")
    md_path.write_text(script_to_markdown(script), encoding="utf-8")
    srt_path.write_text(captions_to_srt(script.captions), encoding="utf-8")
    return {"json": json_path, "markdown": md_path, "srt": srt_path}


def load_script(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def script_to_markdown(script: ShortScript) -> str:
    hashtags = " ".join(script.hashtags)
    source_ideas = "\n".join(f"- {source}" for source in script.source_ideas)
    notes = "\n".join(f"- {note}" for note in script.fact_check_notes)
    captions = "\n".join(
        f"- {caption.start:05.2f}-{caption.end:05.2f}: {caption.text}" for caption in script.captions
    )

    return f"""# {script.title}

Niche: {script.niche}
Estimated length: {script.estimated_seconds:.1f}s

## Hook

{script.hook}

## Narration

{script.narration}

## Hashtags

{hashtags}

## Source Ideas

{source_ideas}

## Fact Check Notes

{notes}

## Captions

{captions}
"""

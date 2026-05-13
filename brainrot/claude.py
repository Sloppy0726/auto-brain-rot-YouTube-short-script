from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any, Dict

from .captions import estimate_duration_seconds, make_captions
from .models import Brief, ShortScript
from .topics import NICHE_HASHTAGS


ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
DEFAULT_MODEL = "claude-sonnet-4-5"


class ClaudeError(RuntimeError):
    pass


def make_claude_script(brief: Brief, model: str = DEFAULT_MODEL) -> ShortScript:
    payload = call_claude(prompt_for_brief(brief), model=model)
    data = parse_json_payload(payload)

    narration = require_string(data, "narration")
    duration = estimate_duration_seconds(narration)
    captions = make_captions(narration, duration)

    hashtags = data.get("hashtags") or default_hashtags(brief)
    fact_check_notes = data.get("fact_check_notes") or default_fact_check_notes(brief)
    source_ideas = data.get("source_ideas") or ([] if brief.content_mode == "fiction" else brief.source_ideas)

    return ShortScript(
        title=require_string(data, "title", fallback=brief.title),
        niche=brief.niche,
        hook=require_string(data, "hook", fallback=brief.hook),
        narration=narration,
        hashtags=[str(item) for item in hashtags][:6],
        fact_check_notes=[str(item) for item in fact_check_notes],
        source_ideas=[str(item) for item in source_ideas],
        estimated_seconds=duration,
        captions=captions,
        content_mode=brief.content_mode,
        fiction_genre=brief.fiction_genre,
    )


def default_hashtags(brief: Brief):
    if brief.content_mode == "fiction":
        return {
            "micro-horror": ["#horrorstory", "#scarystory", "#shorts"],
            "sci-fi-ai": ["#scifi", "#aitok", "#shorts"],
            "moral-dilemma": ["#storytime", "#mystory", "#shorts"],
            "workplace-drama": ["#workstory", "#corporatestories", "#shorts"],
            "relationship-drama": ["#storytime", "#drama", "#shorts"],
        }.get(brief.fiction_genre, ["#storytime", "#shorts"])
    return NICHE_HASHTAGS.get(brief.niche, ["#shorts"])


def default_fact_check_notes(brief: Brief):
    if brief.content_mode == "fiction":
        return [
            "Fiction. Do not present this as a true event.",
            "Check for accidental similarity to existing stories before publishing.",
            "Keep titles/descriptions clear that the channel publishes original fiction.",
        ]
    return [
        "Verify every factual claim before publishing.",
        "Add source URLs before upload.",
    ]


def call_claude(user_prompt: str, model: str) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ClaudeError("ANTHROPIC_API_KEY is not set.")

    body = {
        "model": os.environ.get("CLAUDE_MODEL", model),
        "max_tokens": 1400,
        "temperature": 0.8,
        "system": (
            "You write original YouTube Shorts scripts for an infotainment channel. "
            "You avoid plagiarism, unsupported specifics, and copyrighted text. "
            "You return strict JSON only."
        ),
        "messages": [{"role": "user", "content": user_prompt}],
    }
    request = urllib.request.Request(
        ANTHROPIC_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "content-type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": ANTHROPIC_VERSION,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            response_data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise ClaudeError(f"Claude API error {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise ClaudeError(f"Claude API request failed: {exc.reason}") from exc

    content = response_data.get("content", [])
    text_blocks = [block.get("text", "") for block in content if block.get("type") == "text"]
    text = "\n".join(text_blocks).strip()
    if not text:
        raise ClaudeError("Claude returned no text content.")
    return text


def prompt_for_brief(brief: Brief) -> str:
    if brief.content_mode == "fiction":
        return fiction_prompt_for_brief(brief)

    source_ideas = ", ".join(brief.source_ideas)
    return f"""
Create one original brain-rot style YouTube Short script.

Topic: {brief.title}
Niche: {brief.niche}
Starting hook idea: {brief.hook}
Angle: {brief.angle}
Source ideas to verify later: {source_ideas}

Rules:
- 45 to 58 seconds when read quickly.
- First sentence must be a strong hook.
- Use simple language and short sentences.
- Make it feel curious, useful, and slightly dramatic.
- Do not claim exact statistics unless the brief gives them.
- Do not copy Reddit posts, articles, or viral videos.
- End with a practical takeaway or memorable twist.
- Return JSON only, with this shape:
{{
  "title": "string",
  "hook": "string",
  "narration": "string",
  "hashtags": ["#shorts"],
  "fact_check_notes": ["string"],
  "source_ideas": ["string"]
}}
""".strip()


def fiction_prompt_for_brief(brief: Brief) -> str:
    return f"""
Create one original fictional YouTube Short story script.

Content mode: fiction
Fiction genre: {brief.fiction_genre}
Story seed: {brief.title}
Starting hook idea: {brief.hook}
Angle: {brief.angle}

Rules:
- 45 to 58 seconds when read quickly.
- First sentence must be a strong story hook.
- Use first person or close third person.
- Use simple language and short sentences.
- Build tension quickly: hook, setup, escalation, twist, final line.
- Do not present the story as a true event.
- Do not copy Reddit posts, creepypasta, articles, movies, games, or viral videos.
- No graphic gore, sexual content, hate, or real-person accusations.
- End with a memorable twist or unresolved final line.
- Return JSON only, with this shape:
{{
  "title": "string",
  "hook": "string",
  "narration": "string",
  "hashtags": ["#shorts"],
  "fact_check_notes": ["Fiction. Check for accidental similarity to existing stories."],
  "source_ideas": []
}}
""".strip()


def parse_json_payload(text: str) -> Dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise ClaudeError("Claude did not return JSON.")
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise ClaudeError(f"Claude returned invalid JSON: {exc}") from exc


def require_string(data: Dict[str, Any], key: str, fallback: str = "") -> str:
    value = data.get(key, fallback)
    if not isinstance(value, str) or not value.strip():
        raise ClaudeError(f"Claude JSON is missing '{key}'.")
    return value.strip()

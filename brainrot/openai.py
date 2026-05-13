from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any, Dict, List

from .captions import estimate_duration_seconds, make_captions
from .models import Brief, ShortScript
from .scriptgen import hashtags_for_brief, source_ideas_for_brief, fact_check_notes


OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
DEFAULT_MODEL = "gpt-5-mini"


class OpenAIError(RuntimeError):
    pass


def make_openai_script(brief: Brief, model: str = DEFAULT_MODEL) -> ShortScript:
    payload = call_openai(prompt_for_brief(brief), model=model)
    data = parse_json_payload(payload)

    narration = require_string(data, "narration")
    duration = estimate_duration_seconds(narration)
    captions = make_captions(narration, duration)

    hashtags = data.get("hashtags") or hashtags_for_brief(brief)
    notes = data.get("fact_check_notes") or fact_check_notes(brief)
    sources = data.get("source_ideas") or source_ideas_for_brief(brief)

    return ShortScript(
        title=require_string(data, "title", fallback=brief.title),
        niche=brief.niche,
        hook=require_string(data, "hook", fallback=brief.hook),
        narration=narration,
        hashtags=[str(item) for item in hashtags][:6],
        fact_check_notes=[str(item) for item in notes],
        source_ideas=[str(item) for item in sources],
        estimated_seconds=duration,
        captions=captions,
        content_mode=brief.content_mode,
        fiction_genre=brief.fiction_genre,
    )


def call_openai(user_prompt: str, model: str) -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise OpenAIError("OPENAI_API_KEY is not set.")

    body = {
        "model": os.environ.get("OPENAI_SCRIPT_MODEL", model),
        "instructions": (
            "You write original YouTube Shorts scripts for an infotainment channel. "
            "Avoid plagiarism, unsupported specifics, and copyrighted text. "
            "Return only valid JSON matching the requested shape."
        ),
        "input": user_prompt,
        "max_output_tokens": 1400,
        "text": {
            "format": {
                "type": "json_schema",
                "name": "short_script",
                "strict": True,
                "schema": script_schema(),
            }
        },
    }
    request = urllib.request.Request(
        OPENAI_RESPONSES_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            response_data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise OpenAIError(f"OpenAI API error {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise OpenAIError(f"OpenAI API request failed: {exc.reason}") from exc

    text = extract_response_text(response_data)
    if not text:
        raise OpenAIError("OpenAI returned no text content.")
    return text


def extract_response_text(response_data: Dict[str, Any]) -> str:
    if isinstance(response_data.get("output_text"), str):
        return str(response_data["output_text"]).strip()

    chunks: List[str] = []
    for item in response_data.get("output", []):
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []):
            if not isinstance(content, dict):
                continue
            if content.get("type") in {"output_text", "text"} and isinstance(content.get("text"), str):
                chunks.append(str(content["text"]))
    return "\n".join(chunks).strip()


def script_schema() -> Dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["title", "hook", "narration", "hashtags", "fact_check_notes", "source_ideas"],
        "properties": {
            "title": {"type": "string"},
            "hook": {"type": "string"},
            "narration": {"type": "string"},
            "hashtags": {"type": "array", "items": {"type": "string"}},
            "fact_check_notes": {"type": "array", "items": {"type": "string"}},
            "source_ideas": {"type": "array", "items": {"type": "string"}},
        },
    }


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
            raise OpenAIError("OpenAI did not return JSON.")
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise OpenAIError(f"OpenAI returned invalid JSON: {exc}") from exc


def require_string(data: Dict[str, Any], key: str, fallback: str = "") -> str:
    value = data.get(key, fallback)
    if not isinstance(value, str) or not value.strip():
        raise OpenAIError(f"OpenAI JSON is missing '{key}'.")
    return value.strip()

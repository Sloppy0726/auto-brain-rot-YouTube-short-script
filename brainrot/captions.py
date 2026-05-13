from __future__ import annotations

import re
from typing import Iterable, List

from .models import Caption


def estimate_duration_seconds(narration: str) -> float:
    words = re.findall(r"\b[\w']+\b", narration)
    seconds = len(words) / 2.65
    return round(max(35.0, min(59.0, seconds)), 1)


def make_captions(narration: str, duration: float) -> List[Caption]:
    words = re.findall(r"[A-Za-z0-9'$%.-]+", narration)
    if not words:
        return []

    chunks = list(chunk_words(words))
    step = duration / len(chunks)
    captions: List[Caption] = []
    for index, chunk in enumerate(chunks, start=1):
        start = round((index - 1) * step, 2)
        end = round(index * step, 2)
        captions.append(Caption(index=index, start=start, end=end, text=" ".join(chunk).upper()))
    return captions


def chunk_words(words: List[str]) -> Iterable[List[str]]:
    index = 0
    while index < len(words):
        remaining = len(words) - index
        size = 3 if remaining < 6 else 4
        chunk = words[index : index + size]
        index += size
        yield chunk


def srt_timestamp(seconds: float) -> str:
    millis = int(round(seconds * 1000))
    hours, remainder = divmod(millis, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"


def captions_to_srt(captions: List[Caption]) -> str:
    blocks = []
    for caption in captions:
        blocks.append(
            "\n".join(
                [
                    str(caption.index),
                    f"{srt_timestamp(caption.start)} --> {srt_timestamp(caption.end)}",
                    caption.text,
                ]
            )
        )
    return "\n\n".join(blocks) + "\n"

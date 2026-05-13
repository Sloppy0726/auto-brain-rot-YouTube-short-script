from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List


@dataclass
class Brief:
    title: str
    niche: str
    hook: str
    angle: str
    why_it_might_work: str
    risk_level: str
    source_ideas: List[str] = field(default_factory=list)
    content_mode: str = "nonfiction"
    fiction_genre: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Caption:
    index: int
    start: float
    end: float
    text: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ShortScript:
    title: str
    niche: str
    hook: str
    narration: str
    hashtags: List[str]
    fact_check_notes: List[str]
    source_ideas: List[str]
    estimated_seconds: float
    captions: List[Caption]
    content_mode: str = "nonfiction"
    fiction_genre: str = ""

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["captions"] = [caption.to_dict() for caption in self.captions]
        return data

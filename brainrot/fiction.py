from __future__ import annotations

import random
from typing import Dict, List, Optional

from .models import Brief


FICTION_GENRES: Dict[str, Dict[str, object]] = {
    "micro-horror": {
        "label": "Micro Horror",
        "promise": "one unsettling story under 60 seconds",
        "hooks": [
            "My phone got a notification from tomorrow.",
            "The elevator opened on a floor that was not in the building.",
            "My smart speaker answered a question I had not asked yet.",
            "The baby monitor picked up a voice in an empty room.",
            "A stranger texted me a photo of my own front door.",
        ],
    },
    "sci-fi-ai": {
        "label": "Sci-Fi AI",
        "promise": "tiny stories about technology going wrong",
        "hooks": [
            "The AI assistant started canceling meetings before people died.",
            "The first robot lawyer refused to defend its client.",
            "A company hired an AI CEO for thirty days.",
            "Everyone got a prediction score except one person.",
            "The dating app matched him with someone who had not been born yet.",
        ],
    },
    "moral-dilemma": {
        "label": "Moral Dilemma",
        "promise": "one impossible decision every day",
        "hooks": [
            "He found ten thousand dollars in a used couch, then the owner called.",
            "A boss fired one employee to save five others.",
            "She lied on her resume and accidentally saved the company.",
            "A student used AI to pass, then got hired to catch AI cheaters.",
            "He exposed his best friend's scam and lost everyone.",
        ],
    },
    "workplace-drama": {
        "label": "Workplace Drama",
        "promise": "corporate stories that feel illegal but are fictional",
        "hooks": [
            "The intern found the spreadsheet nobody was supposed to open.",
            "A fake employee collected paychecks for three years.",
            "The layoff list accidentally got sent to everyone.",
            "The office had a Slack channel with one member who was not alive.",
            "The new manager banned one word and exposed the whole company.",
        ],
    },
    "relationship-drama": {
        "label": "Relationship Drama",
        "promise": "one messy secret in 60 seconds",
        "hooks": [
            "She found her wedding vows in another woman's notes app.",
            "He tested his friends with a fake lottery ticket.",
            "A roommate charged rent for a room she did not own.",
            "Her boyfriend had a second calendar named work.",
            "The family group chat exposed the real inheritance plan.",
        ],
    },
}


DEFAULT_FICTION_GENRES = ["micro-horror", "sci-fi-ai", "moral-dilemma", "workplace-drama"]


def list_fiction_genres() -> List[str]:
    return sorted(FICTION_GENRES.keys())


def make_fiction_briefs(
    count: int,
    genres: Optional[List[str]] = None,
    seed: Optional[int] = None,
) -> List[Brief]:
    selected_genres = normalize_fiction_genres(genres)
    rng = random.Random(seed)
    briefs: List[Brief] = []

    for index in range(count):
        genre = selected_genres[index % len(selected_genres)]
        config = FICTION_GENRES[genre]
        hook = rng.choice(list(config["hooks"]))
        briefs.append(
            Brief(
                title=hook.rstrip("."),
                niche="fiction",
                hook=hook,
                angle=(
                    f"Write an original {config['label']} story. Channel promise: {config['promise']}. "
                    "Make it feel complete, punchy, and clearly fictional."
                ),
                why_it_might_work="Fiction hooks create retention because viewers wait for the twist.",
                risk_level="low: keep it original and clearly fictional",
                source_ideas=[],
                content_mode="fiction",
                fiction_genre=genre,
            )
        )

    return briefs


def normalize_fiction_genres(genres: Optional[List[str]]) -> List[str]:
    if not genres or "all" in genres:
        return DEFAULT_FICTION_GENRES

    normalized = []
    for genre in genres:
        key = genre.strip().lower()
        if key not in FICTION_GENRES:
            valid = ", ".join(list_fiction_genres())
            raise ValueError(f"Unknown fiction genre '{genre}'. Valid genres: {valid}")
        normalized.append(key)
    return normalized

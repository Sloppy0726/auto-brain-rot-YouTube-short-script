from __future__ import annotations

import hashlib
from typing import List

from .captions import estimate_duration_seconds, make_captions
from .models import Brief, ShortScript
from .topics import NICHE_HASHTAGS, source_ideas


def make_script(brief: Brief) -> ShortScript:
    narration = generate_narration(brief)
    duration = estimate_duration_seconds(narration)
    captions = make_captions(narration, duration)
    return ShortScript(
        title=brief.title,
        niche=brief.niche,
        hook=brief.hook,
        narration=narration,
        hashtags=NICHE_HASHTAGS.get(brief.niche, ["#shorts"]),
        fact_check_notes=fact_check_notes(brief),
        source_ideas=brief.source_ideas or source_ideas(brief.niche),
        estimated_seconds=duration,
        captions=captions,
    )


def generate_narration(brief: Brief) -> str:
    templates = [
        "{hook} Here is the part most people miss. {setup} {mechanic} {twist} {takeaway}",
        "{hook} It sounds simple, but the trick is the timing. {setup} {mechanic} {twist} {takeaway}",
        "{hook} The reason it works is not complicated. {setup} {mechanic} {twist} {takeaway}",
    ]
    template = deterministic_choice(templates, brief.title)
    parts = story_parts(brief)
    return template.format(hook=brief.hook, **parts)


def story_parts(brief: Brief) -> dict:
    title = brief.title.lower()

    if brief.niche == "scams":
        return {
            "setup": f"The setup is built to feel normal: {brief.angle.lower()}",
            "mechanic": "The victim is pushed to act quickly, before they search for the official website or ask someone else.",
            "twist": "That tiny moment of panic is the product. The link, form, or dashboard only exists to collect trust and payment details.",
            "takeaway": "The safe move is boring: leave the message, search the organization yourself, and pay only through the official page.",
        }

    if brief.niche == "business":
        return {
            "setup": f"The promise was easy to understand: {brief.angle.lower()}",
            "mechanic": "But a great story does not fix bad unit economics, weak margins, or a product people stop trusting.",
            "twist": "Once customers notice the gap between the promise and the reality, growth can turn into evidence against the company.",
            "takeaway": "That is why the most dangerous business model is one that gets more expensive as it gets more popular.",
        }

    if brief.niche == "ai":
        return {
            "setup": f"The useful version is practical: {brief.angle.lower()}",
            "mechanic": "It saves time by turning messy human input into a clean next action, draft, summary, or workflow.",
            "twist": "The risk is that automation can also make bad information move faster and look more polished.",
            "takeaway": "So the winning setup is AI for speed, human review for judgment, and receipts for anything factual.",
        }

    if brief.niche == "law":
        return {
            "setup": f"The viral version usually skips the important detail: {brief.angle.lower()}",
            "mechanic": "Legal stories depend on exact facts, exact wording, and the boring context that does not fit in a meme.",
            "twist": "That is why the internet version can be funny and still be wrong in the way that matters.",
            "takeaway": "Before repeating a legal story, check the original case or a reliable legal summary.",
        }

    if brief.niche == "money":
        return {
            "setup": f"The behavior is ordinary: {brief.angle.lower()}",
            "mechanic": "Small design choices change how expensive, urgent, or safe a purchase feels in the moment.",
            "twist": "No single trick controls everyone, but enough tiny nudges can change what people choose.",
            "takeaway": "The defense is to slow the decision down and ask what the page is trying to make feel obvious.",
        }

    if "giveaway" in title:
        twist = "The prize is not the business. Your attention, login, or payment detail is."
    else:
        twist = "The mystery works because the missing piece feels just close enough to keep you watching."

    return {
        "setup": f"The interesting part is the curiosity loop: {brief.angle.lower()}",
        "mechanic": "People keep watching because every answer creates one more question.",
        "twist": twist,
        "takeaway": "That is the secret behind half the internet: make the next detail feel impossible to ignore.",
    }


def fact_check_notes(brief: Brief) -> List[str]:
    return [
        "Replace any broad claim with a checked detail before publishing.",
        "Add at least one source URL to the JSON after research.",
        "Avoid naming real people or companies unless the source is strong.",
        f"Risk: {brief.risk_level}",
    ]


def deterministic_choice(options: List[str], key: str) -> str:
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    index = int(digest[:8], 16) % len(options)
    return options[index]

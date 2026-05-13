from __future__ import annotations

import random
from typing import Dict, Iterable, List, Optional

from .models import Brief


NICHE_HASHTAGS: Dict[str, List[str]] = {
    "scams": ["#scamalert", "#cybersafety", "#moneytips", "#shorts"],
    "business": ["#business", "#startups", "#marketing", "#shorts"],
    "ai": ["#aitools", "#automation", "#tech", "#shorts"],
    "internet": ["#internetmystery", "#weirdweb", "#storytime", "#shorts"],
    "law": ["#lawtok", "#courtcase", "#explained", "#shorts"],
    "money": ["#moneypsychology", "#personalfinance", "#marketing", "#shorts"],
}


TOPIC_BANK: Dict[str, List[Dict[str, str]]] = {
    "scams": [
        {
            "title": "How fake QR code parking tickets work",
            "hook": "If a parking ticket tells you to scan a QR code, pause first.",
            "angle": "Explain the panic-payment trick and the safest way to pay.",
        },
        {
            "title": "The fake job interview that steals your identity",
            "hook": "A dream remote job can become an identity theft trap in one message.",
            "angle": "Show the fake onboarding flow and what documents scammers ask for.",
        },
        {
            "title": "Why romance scams move victims into crypto",
            "hook": "The romance scam usually does not start with money. It starts with trust.",
            "angle": "Break down the emotional pacing and the fake investment dashboard.",
        },
        {
            "title": "The missed delivery text scam",
            "hook": "That tiny delivery fee text can cost a lot more than two dollars.",
            "angle": "Explain card capture pages and why the fee feels believable.",
        },
    ],
    "business": [
        {
            "title": "Why MoviePass collapsed",
            "hook": "This company sold unlimited movie tickets for less than one ticket cost.",
            "angle": "Tell the business model problem in simple terms.",
        },
        {
            "title": "The $400 juicer that did not need the machine",
            "hook": "A startup raised millions for a machine people could replace with their hands.",
            "angle": "Explain the product promise, the discovery, and the trust collapse.",
        },
        {
            "title": "Why restaurants put the profitable food in the right places",
            "hook": "A menu is not just a list. It is a sales page.",
            "angle": "Explain menu engineering without pretending every restaurant uses one trick.",
        },
        {
            "title": "How free trials become forgotten subscriptions",
            "hook": "Free trials are not free if the product is counting on you to forget.",
            "angle": "Explain default billing, reminders, and why friction matters.",
        },
    ],
    "ai": [
        {
            "title": "The AI agent that turns meetings into tasks",
            "hook": "The boring AI tools are the ones companies may actually pay for.",
            "angle": "Explain why turning messy meetings into structured work is valuable.",
        },
        {
            "title": "How one article becomes twenty social posts",
            "hook": "One long article can quietly become an entire week of content.",
            "angle": "Show the repurposing chain and why human review still matters.",
        },
        {
            "title": "The browser agent that shops for you",
            "hook": "The next AI assistant might not answer your question. It might click for you.",
            "angle": "Explain browser agents through a simple shopping or booking example.",
        },
        {
            "title": "Why AI voice clones are dangerous",
            "hook": "A few seconds of audio can be enough to fake a familiar voice.",
            "angle": "Explain the scam risk and a family verification phrase.",
        },
    ],
    "internet": [
        {
            "title": "The fake influencer who never existed",
            "hook": "Some influencers are not hiding their real life. They do not have one.",
            "angle": "Explain virtual influencers and why brands use them.",
        },
        {
            "title": "The lost song the internet tried to identify",
            "hook": "Sometimes the whole internet can hear a song and still not know what it is.",
            "angle": "Tell the search mechanics: clips, forums, databases, and false leads.",
        },
        {
            "title": "Why people fall for impossible giveaways",
            "hook": "A fake giveaway only needs one thing to work: urgency.",
            "angle": "Explain social proof, fake comments, and prize bait.",
        },
        {
            "title": "The website that looks broken on purpose",
            "hook": "Some websites are designed to feel like a puzzle before they sell you anything.",
            "angle": "Explain mystery marketing and curiosity loops.",
        },
    ],
    "law": [
        {
            "title": "The McDonald's coffee case explained correctly",
            "hook": "The famous coffee lawsuit was much stranger than the punchline.",
            "angle": "Avoid the meme version and explain why the case mattered.",
        },
        {
            "title": "The lawsuit over one comma",
            "hook": "One comma helped decide a multimillion-dollar argument.",
            "angle": "Explain how unclear writing can become expensive.",
        },
        {
            "title": "Why a Terms of Service checkbox matters",
            "hook": "That checkbox you skip can become evidence later.",
            "angle": "Explain clickwrap agreements in plain language.",
        },
        {
            "title": "The burglar lawsuit stories are usually misleading",
            "hook": "Those viral burglar lawsuit stories usually leave out the boring part.",
            "angle": "Debunk the genre and explain why context changes the story.",
        },
    ],
    "money": [
        {
            "title": "Why $9.99 still works",
            "hook": "Your brain knows $9.99 is basically ten dollars. It still reacts.",
            "angle": "Explain left-digit pricing and when it matters.",
        },
        {
            "title": "Why casinos do not want you tracking time",
            "hook": "A casino is designed to make time feel slippery.",
            "angle": "Talk about environment design without overclaiming a single trick.",
        },
        {
            "title": "How stores make the cheap option feel risky",
            "hook": "Sometimes the middle option is the product they wanted you to buy.",
            "angle": "Explain decoy pricing with a simple example.",
        },
        {
            "title": "Why paying with a card feels less painful",
            "hook": "Swiping a card can feel less real than handing over cash.",
            "angle": "Explain payment friction and spending awareness.",
        },
    ],
}


def list_niches() -> List[str]:
    return sorted(TOPIC_BANK.keys())


def iter_topics(niche: Optional[str] = None) -> Iterable[Dict[str, str]]:
    if niche and niche != "all":
        yield from TOPIC_BANK[niche]
        return

    for topic_list in TOPIC_BANK.values():
        yield from topic_list


def make_briefs(count: int = 3, niche: Optional[str] = None, seed: Optional[int] = None) -> List[Brief]:
    if niche and niche != "all" and niche not in TOPIC_BANK:
        valid = ", ".join(list_niches())
        raise ValueError(f"Unknown niche '{niche}'. Valid niches: {valid}")

    rng = random.Random(seed)
    candidates = list(iter_topics(niche))
    rng.shuffle(candidates)
    chosen = candidates[:count]

    briefs: List[Brief] = []
    for item in chosen:
        resolved_niche = niche_for_title(item["title"])
        briefs.append(
            Brief(
                title=item["title"],
                niche=resolved_niche,
                hook=item["hook"],
                angle=item["angle"],
                why_it_might_work=why_it_works(resolved_niche),
                risk_level=risk_level(resolved_niche),
                source_ideas=source_ideas(resolved_niche),
            )
        )
    return briefs


def niche_for_title(title: str) -> str:
    for niche, items in TOPIC_BANK.items():
        if any(item["title"] == title for item in items):
            return niche
    return "internet"


def source_ideas(niche: str) -> List[str]:
    defaults = {
        "scams": ["FTC consumer alerts", "local police or city notices", "bank fraud education pages"],
        "business": ["company filings", "credible business reporting", "founder interviews"],
        "ai": ["product docs", "company blogs", "security research", "credible tech reporting"],
        "internet": ["archived pages", "creator statements", "credible explainers"],
        "law": ["court opinions", "legal explainers", "law school or bar association resources"],
        "money": ["behavioral economics research", "consumer finance explainers", "retail pricing examples"],
    }
    return defaults.get(niche, ["credible reporting", "primary sources"])


def risk_level(niche: str) -> str:
    if niche in {"law", "scams", "ai"}:
        return "medium: fact-check carefully before publishing"
    return "low-medium: avoid unsupported specifics"


def why_it_works(niche: str) -> str:
    reasons = {
        "scams": "Useful fear plus a practical warning usually earns comments and shares.",
        "business": "Rise-and-fall stories have built-in curiosity and a clean twist.",
        "ai": "Viewers want to know what tools are changing work right now.",
        "internet": "Mystery framing creates retention because viewers wait for the reveal.",
        "law": "Legal stories work when they correct a common misconception.",
        "money": "People like learning the hidden mechanics behind everyday spending.",
    }
    return reasons.get(niche, "It has a clear hook, simple stakes, and a shareable takeaway.")

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from .claude import DEFAULT_MODEL, make_claude_script
from .files import load_script, write_script_bundle
from .models import Brief, ShortScript
from .render import RenderError, render_short
from .scriptgen import make_script
from .topics import make_briefs, source_ideas
from .voice import VoiceError, make_voiceover
from .youtube import YouTubeAgent, YouTubeError, make_upload_description


SUBREDDITS_BY_NICHE = {
    "scams": [
        "scams",
        "cybersecurity",
        "privacy",
        "IdentityTheft",
        "RBI",
        "Catfish",
        "phishing",
    ],
    "business": [
        "business",
        "entrepreneur",
        "startups",
        "smallbusiness",
        "marketing",
        "ecommerce",
        "ProductManagement",
        "SaaS",
        "economics",
    ],
    "ai": [
        "technology",
        "technews",
        "Futurology",
        "ArtificialIntelligence",
        "artificial",
        "singularity",
        "MachineLearning",
        "LocalLLaMA",
        "ChatGPT",
        "OpenAI",
        "ClaudeAI",
    ],
    "internet": [
        "todayilearned",
        "OutOfTheLoop",
        "InternetIsBeautiful",
        "DataIsBeautiful",
        "interestingasfuck",
        "mildlyinteresting",
        "InternetMysteries",
        "UnresolvedMysteries",
        "AskReddit",
    ],
    "law": [
        "legaladviceofftopic",
        "law",
        "Ask_Lawyers",
        "LawSchool",
        "privacy",
        "technology",
    ],
    "money": [
        "personalfinance",
        "financialindependence",
        "Frugal",
        "CreditCards",
        "povertyfinance",
        "Bogleheads",
        "investing",
        "Money",
    ],
}


DEFAULT_NICHES = ["scams", "business", "ai", "internet", "law", "money"]
DEFAULT_SUBREDDITS = []
for niche in DEFAULT_NICHES:
    for subreddit in SUBREDDITS_BY_NICHE[niche]:
        if subreddit not in DEFAULT_SUBREDDITS:
            DEFAULT_SUBREDDITS.append(subreddit)


SUBREDDIT_NICHES = {
    "scams": "scams",
    "technology": "ai",
    "business": "business",
    "todayilearned": "internet",
    "internetisbeautiful": "internet",
    "artificialintelligence": "ai",
    "personalfinance": "money",
    "legaladviceofftopic": "law",
}

for _niche, _subreddits in SUBREDDITS_BY_NICHE.items():
    for _subreddit in _subreddits:
        SUBREDDIT_NICHES.setdefault(_subreddit.lower(), _niche)


@dataclass
class PipelineItem:
    title: str
    script_json: Path
    script_markdown: Path
    captions_srt: Path
    audio: Optional[Path] = None
    video: Optional[Path] = None
    youtube_video_id: Optional[str] = None
    youtube_url: Optional[str] = None
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return {
            "title": self.title,
            "script_json": str(self.script_json),
            "script_markdown": str(self.script_markdown),
            "captions_srt": str(self.captions_srt),
            "audio": str(self.audio) if self.audio else None,
            "video": str(self.video) if self.video else None,
            "youtube_video_id": self.youtube_video_id,
            "youtube_url": self.youtube_url,
            "warnings": self.warnings,
        }


class IdeaAgent:
    def __init__(
        self,
        subreddits: Optional[List[str]] = None,
        per_subreddit: int = 8,
        reddit_sort: str = "hot",
        reddit_time: str = "day",
    ) -> None:
        self.subreddits = subreddits or DEFAULT_SUBREDDITS
        self.per_subreddit = per_subreddit
        self.reddit_sort = reddit_sort
        self.reddit_time = reddit_time

    def find_ideas(self, count: int) -> List[Brief]:
        candidates: List[Dict[str, object]] = []
        for subreddit in self.subreddits:
            candidates.extend(self._fetch_subreddit(subreddit))

        if not candidates:
            return make_briefs(count=count, niche="all")

        candidates.sort(key=lambda item: int(item["score"]), reverse=True)
        briefs: List[Brief] = []
        for item in candidates[:count]:
            subreddit = str(item["subreddit"])
            niche = SUBREDDIT_NICHES.get(subreddit.lower(), "internet")
            title = str(item["title"])
            url = str(item["url"])
            briefs.append(
                Brief(
                    title=title,
                    niche=niche,
                    hook=f"{title} sounds simple, but the important detail is easy to miss.",
                    angle=(
                        "Use the Reddit post only as a lead. Rewrite the story, verify it from stronger sources, "
                        "and turn it into a useful explanation."
                    ),
                    why_it_might_work="Reddit velocity suggests the topic already has curiosity and discussion.",
                    risk_level="medium: do not copy the post; verify before upload",
                    source_ideas=[url, *source_ideas(niche)],
                )
            )
        return briefs

    def _fetch_subreddit(self, subreddit: str) -> List[Dict[str, object]]:
        encoded = urllib.parse.quote(subreddit)
        query = {"limit": str(self.per_subreddit)}
        if self.reddit_sort == "top":
            query["t"] = self.reddit_time
        endpoint = urllib.parse.quote(self.reddit_sort)
        url = f"https://www.reddit.com/r/{encoded}/{endpoint}.json?{urllib.parse.urlencode(query)}"
        request = urllib.request.Request(url, headers={"User-Agent": "brainrot-agent/0.1"})
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                data = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            return []

        posts: List[Dict[str, object]] = []
        for child in data.get("data", {}).get("children", []):
            post = child.get("data", {})
            title = str(post.get("title", "")).strip()
            if not title or post.get("stickied") or post.get("over_18"):
                continue
            if len(title) < 25 or len(title) > 145:
                continue
            permalink = post.get("permalink") or ""
            score = int(post.get("score", 0)) + int(post.get("num_comments", 0)) * 3
            posts.append(
                {
                    "title": title,
                    "subreddit": subreddit,
                    "score": score,
                    "url": f"https://www.reddit.com{permalink}",
                }
            )
        return posts


class PublisherAgent:
    def __init__(
        self,
        client_secrets: Path,
        token_path: Path,
        privacy_status: str = "private",
        category_id: str = "22",
    ) -> None:
        self.client_secrets = client_secrets
        self.token_path = token_path
        self.privacy_status = privacy_status
        self.category_id = category_id

    def publish(self, script_json: Path, video_path: Optional[Path]) -> Dict[str, Optional[str]]:
        if not video_path:
            return {"youtube_video_id": None, "youtube_url": None, "warning": "No rendered video to upload."}

        script = load_script(script_json)
        agent = YouTubeAgent(client_secrets=self.client_secrets, token_path=self.token_path)
        try:
            upload = agent.upload_video(
                video_path=video_path,
                title=str(script["title"]),
                description=make_upload_description(script),
                tags=[tag.lstrip("#") for tag in script.get("hashtags", [])],
                privacy_status=self.privacy_status,
                category_id=self.category_id,
            )
        except YouTubeError as exc:
            return {"youtube_video_id": None, "youtube_url": None, "warning": str(exc)}
        return {"youtube_video_id": upload.video_id, "youtube_url": upload.url, "warning": None}


class ScriptAgent:
    def __init__(self, backend: str = "template", model: str = DEFAULT_MODEL) -> None:
        self.backend = backend
        self.model = model

    def write_script(self, brief: Brief) -> ShortScript:
        if self.backend == "claude":
            return make_claude_script(brief, model=self.model)
        return make_script(brief)


class VideoAgent:
    def __init__(
        self,
        make_voice: bool = False,
        voice: Optional[str] = None,
        gameplay: Optional[Path] = None,
    ) -> None:
        self.make_voice = make_voice
        self.voice = voice
        self.gameplay = gameplay

    def produce(self, script_json: Path, out_dir: Path) -> Dict[str, object]:
        script = load_script(script_json)
        result: Dict[str, object] = {"audio": None, "video": None, "warnings": []}
        audio_path: Optional[Path] = None

        if self.make_voice:
            try:
                audio_path = make_voiceover(script, out_dir, voice=self.voice)
                result["audio"] = audio_path
            except VoiceError as exc:
                result["warnings"].append(str(exc))

        if self.gameplay:
            try:
                video_path = render_short(
                    script,
                    gameplay_path=self.gameplay,
                    audio_path=audio_path,
                    output_path=out_dir / f"{script_json.stem}.mp4",
                )
                result["video"] = video_path
            except RenderError as exc:
                result["warnings"].append(str(exc))

        return result


def run_pipeline(
    count: int,
    out_dir: Path,
    backend: str = "template",
    model: str = DEFAULT_MODEL,
    subreddits: Optional[List[str]] = None,
    per_subreddit: int = 8,
    reddit_sort: str = "hot",
    reddit_time: str = "day",
    make_voice: bool = False,
    voice: Optional[str] = None,
    gameplay: Optional[Path] = None,
    publish: bool = False,
    privacy_status: str = "private",
    category_id: str = "22",
    client_secrets: Path = Path("client_secrets.json"),
    token_path: Path = Path(".secrets/youtube-token.json"),
) -> List[PipelineItem]:
    out_dir.mkdir(parents=True, exist_ok=True)
    idea_agent = IdeaAgent(
        subreddits=subreddits,
        per_subreddit=per_subreddit,
        reddit_sort=reddit_sort,
        reddit_time=reddit_time,
    )
    script_agent = ScriptAgent(backend=backend, model=model)
    video_agent = VideoAgent(make_voice=make_voice, voice=voice, gameplay=gameplay)
    publisher_agent = (
        PublisherAgent(
            client_secrets=client_secrets,
            token_path=token_path,
            privacy_status=privacy_status,
            category_id=category_id,
        )
        if publish
        else None
    )

    items: List[PipelineItem] = []
    for brief in idea_agent.find_ideas(count=count):
        script = script_agent.write_script(brief)
        paths = write_script_bundle(script, out_dir)
        produced = video_agent.produce(paths["json"], out_dir)
        upload = {"youtube_video_id": None, "youtube_url": None, "warning": None}
        if publisher_agent:
            upload = publisher_agent.publish(paths["json"], produced["video"])
        items.append(
            PipelineItem(
                title=script.title,
                script_json=paths["json"],
                script_markdown=paths["markdown"],
                captions_srt=paths["srt"],
                audio=produced["audio"],
                video=produced["video"],
                youtube_video_id=upload["youtube_video_id"],
                youtube_url=upload["youtube_url"],
                warnings=[
                    *[str(item) for item in produced["warnings"]],
                    *([str(upload["warning"])] if upload["warning"] else []),
                ],
            )
        )

    manifest_path = out_dir / "pipeline-manifest.json"
    manifest_path.write_text(json.dumps([item.to_dict() for item in items], indent=2), encoding="utf-8")
    return items


def resolve_subreddits(
    niches: Optional[List[str]] = None,
    subreddits: Optional[List[str]] = None,
    extra_subreddits: Optional[List[str]] = None,
    max_subreddits: int = 60,
) -> List[str]:
    selected: List[str] = []

    if subreddits:
        selected.extend(subreddits)
    else:
        selected_niches = [niche.lower() for niche in (niches or DEFAULT_NICHES)]
        if "all" in selected_niches:
            selected_niches = DEFAULT_NICHES
        for niche in selected_niches:
            selected.extend(SUBREDDITS_BY_NICHE.get(niche, []))

    if extra_subreddits:
        selected.extend(extra_subreddits)

    unique: List[str] = []
    seen = set()
    for subreddit in selected:
        normalized = subreddit.strip().strip("/")
        if normalized.startswith("r/"):
            normalized = normalized[2:]
        key = normalized.lower()
        if normalized and key not in seen:
            seen.add(key)
            unique.append(normalized)

    return unique[:max_subreddits]

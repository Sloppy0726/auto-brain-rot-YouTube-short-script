from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

from .agents import DEFAULT_NICHES, run_pipeline, resolve_subreddits
from .claude import ClaudeError, DEFAULT_MODEL, make_claude_script
from .files import load_script, slugify, write_script_bundle
from .models import Brief
from .render import RenderError, render_short
from .scriptgen import make_script
from .topics import list_niches, make_briefs, source_ideas
from .voice import VoiceError, make_voiceover
from .youtube import (
    YouTubeAgent,
    YouTubeError,
    default_date_range,
    make_upload_description,
    normalize_tags,
    parse_csv,
    table_preview,
    write_report,
)


def main() -> None:
    parser = argparse.ArgumentParser(prog="brainrot", description="Generate original brain-rot style Shorts.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_parser = subparsers.add_parser("create", help="Generate a batch of Short scripts.")
    create_parser.add_argument("--count", type=int, default=3)
    create_parser.add_argument("--niche", default="all", choices=["all"] + list_niches())
    create_parser.add_argument("--seed", type=int)
    create_parser.add_argument("--out-dir", default="output/today")
    create_parser.add_argument("--backend", choices=["template", "claude"], default="template")
    create_parser.add_argument("--model", default=DEFAULT_MODEL)

    script_parser = subparsers.add_parser("script", help="Generate one Short script from a topic.")
    script_parser.add_argument("--topic", required=True)
    script_parser.add_argument("--niche", default="internet", choices=list_niches())
    script_parser.add_argument("--hook")
    script_parser.add_argument("--angle")
    script_parser.add_argument("--out-dir", default="output/script")
    script_parser.add_argument("--backend", choices=["template", "claude"], default="template")
    script_parser.add_argument("--model", default=DEFAULT_MODEL)

    voice_parser = subparsers.add_parser("voice", help="Generate macOS say voiceover audio from a script JSON.")
    voice_parser.add_argument("script_json")
    voice_parser.add_argument("--voice")
    voice_parser.add_argument("--out-dir")

    render_parser = subparsers.add_parser("render", help="Render a split-screen Short with ffmpeg.")
    render_parser.add_argument("script_json")
    render_parser.add_argument("--gameplay", required=True)
    render_parser.add_argument("--audio")
    render_parser.add_argument("--out")
    render_parser.add_argument("--font", default="Arial Black")

    pipeline_parser = subparsers.add_parser("pipeline", help="Run idea, script, and optional video agents.")
    pipeline_parser.add_argument("--count", type=int, default=3)
    pipeline_parser.add_argument("--out-dir", default="output/today")
    pipeline_parser.add_argument("--backend", choices=["template", "claude"], default="claude")
    pipeline_parser.add_argument("--model", default=DEFAULT_MODEL)
    pipeline_parser.add_argument("--niches", default="all")
    pipeline_parser.add_argument("--subreddits")
    pipeline_parser.add_argument("--extra-subreddits", default="")
    pipeline_parser.add_argument("--max-subreddits", type=int, default=60)
    pipeline_parser.add_argument("--per-subreddit", type=int, default=8)
    pipeline_parser.add_argument("--reddit-sort", choices=["hot", "top", "rising", "new"], default="hot")
    pipeline_parser.add_argument("--reddit-time", choices=["hour", "day", "week", "month", "year", "all"], default="day")
    pipeline_parser.add_argument("--make-voice", action="store_true")
    pipeline_parser.add_argument("--voice")
    pipeline_parser.add_argument("--gameplay")
    pipeline_parser.add_argument("--publish", action="store_true")
    pipeline_parser.add_argument("--privacy-status", choices=["private", "unlisted", "public"], default="private")
    pipeline_parser.add_argument("--category-id", default="22")
    pipeline_parser.add_argument("--client-secrets", default="client_secrets.json")
    pipeline_parser.add_argument("--token-path", default=".secrets/youtube-token.json")

    publish_parser = subparsers.add_parser("publish", help="Upload a rendered Short to YouTube.")
    publish_parser.add_argument("--video", required=True)
    publish_parser.add_argument("--script-json", required=True)
    publish_parser.add_argument("--privacy-status", choices=["private", "unlisted", "public"], default="private")
    publish_parser.add_argument("--category-id", default="22")
    publish_parser.add_argument("--title")
    publish_parser.add_argument("--description")
    publish_parser.add_argument("--tags", default="")
    publish_parser.add_argument("--made-for-kids", action="store_true")
    publish_parser.add_argument("--client-secrets", default="client_secrets.json")
    publish_parser.add_argument("--token-path", default=".secrets/youtube-token.json")

    analytics_parser = subparsers.add_parser("analytics", help="Report YouTube channel or Short analytics.")
    analytics_parser.add_argument("--start-date")
    analytics_parser.add_argument("--end-date")
    analytics_parser.add_argument("--days", type=int, default=7)
    analytics_parser.add_argument(
        "--metrics",
        default="views,estimatedMinutesWatched,averageViewDuration,likes,subscribersGained",
    )
    analytics_parser.add_argument("--dimensions", default="video")
    analytics_parser.add_argument("--video-ids", default="")
    analytics_parser.add_argument("--manifest")
    analytics_parser.add_argument("--sort", default="-views")
    analytics_parser.add_argument("--max-results", type=int, default=25)
    analytics_parser.add_argument("--currency", default="USD")
    analytics_parser.add_argument("--out", default="output/analytics/report.json")
    analytics_parser.add_argument("--client-secrets", default="client_secrets.json")
    analytics_parser.add_argument("--token-path", default=".secrets/youtube-token.json")

    args = parser.parse_args()

    if args.command == "create":
        create_batch(
            count=args.count,
            niche=args.niche,
            seed=args.seed,
            out_dir=Path(args.out_dir),
            backend=args.backend,
            model=args.model,
        )
    elif args.command == "script":
        create_single(
            topic=args.topic,
            niche=args.niche,
            hook=args.hook,
            angle=args.angle,
            out_dir=Path(args.out_dir),
            backend=args.backend,
            model=args.model,
        )
    elif args.command == "voice":
        create_voice(Path(args.script_json), voice=args.voice, out_dir=args.out_dir)
    elif args.command == "render":
        create_render(
            script_json=Path(args.script_json),
            gameplay=Path(args.gameplay),
            audio=Path(args.audio) if args.audio else None,
            out=Path(args.out) if args.out else None,
            font=args.font,
        )
    elif args.command == "pipeline":
        create_pipeline(
            count=args.count,
            out_dir=Path(args.out_dir),
            backend=args.backend,
            model=args.model,
            niches=args.niches,
            subreddits=args.subreddits,
            extra_subreddits=args.extra_subreddits,
            max_subreddits=args.max_subreddits,
            per_subreddit=args.per_subreddit,
            reddit_sort=args.reddit_sort,
            reddit_time=args.reddit_time,
            make_voice=args.make_voice,
            voice=args.voice,
            gameplay=Path(args.gameplay) if args.gameplay else None,
            publish=args.publish,
            privacy_status=args.privacy_status,
            category_id=args.category_id,
            client_secrets=Path(args.client_secrets),
            token_path=Path(args.token_path),
        )
    elif args.command == "publish":
        publish_video(
            video=Path(args.video),
            script_json=Path(args.script_json),
            privacy_status=args.privacy_status,
            category_id=args.category_id,
            title=args.title,
            description=args.description,
            tags=args.tags,
            made_for_kids=args.made_for_kids,
            client_secrets=Path(args.client_secrets),
            token_path=Path(args.token_path),
        )
    elif args.command == "analytics":
        report_analytics(
            start_date=args.start_date,
            end_date=args.end_date,
            days=args.days,
            metrics=args.metrics,
            dimensions=args.dimensions,
            video_ids=args.video_ids,
            manifest=Path(args.manifest) if args.manifest else None,
            sort=args.sort,
            max_results=args.max_results,
            currency=args.currency,
            out=Path(args.out),
            client_secrets=Path(args.client_secrets),
            token_path=Path(args.token_path),
        )


def create_batch(count: int, niche: str, seed: Optional[int], out_dir: Path, backend: str, model: str) -> None:
    briefs = make_briefs(count=count, niche=niche, seed=seed)
    manifest = []
    for brief in briefs:
        script = build_script(brief, backend=backend, model=model)
        paths = write_script_bundle(script, out_dir)
        manifest.append({"title": script.title, "paths": {key: str(value) for key, value in paths.items()}})

    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Generated {len(manifest)} script bundle(s) in {out_dir}")
    print(f"Manifest: {manifest_path}")


def create_single(
    topic: str,
    niche: str,
    hook: Optional[str],
    angle: Optional[str],
    out_dir: Path,
    backend: str,
    model: str,
) -> None:
    brief = Brief(
        title=topic,
        niche=niche,
        hook=hook or default_hook(topic),
        angle=angle or f"explain {topic.lower()} in a clear, useful, surprising way",
        why_it_might_work="Specific curiosity plus a practical takeaway makes this easy to watch.",
        risk_level="medium: verify the details before publishing",
        source_ideas=source_ideas(niche),
    )
    script = build_script(brief, backend=backend, model=model)
    paths = write_script_bundle(script, out_dir)
    print(f"Generated script: {paths['markdown']}")
    print(f"JSON: {paths['json']}")
    print(f"SRT: {paths['srt']}")


def create_voice(script_json: Path, voice: Optional[str], out_dir: Optional[str]) -> None:
    script = load_script(script_json)
    target_dir = Path(out_dir) if out_dir else script_json.parent
    try:
        audio_path = make_voiceover(script, target_dir, voice=voice)
    except VoiceError as exc:
        raise SystemExit(str(exc))
    print(f"Generated voiceover: {audio_path}")


def create_render(
    script_json: Path,
    gameplay: Path,
    audio: Optional[Path],
    out: Optional[Path],
    font: str,
) -> None:
    script = load_script(script_json)
    output_path = out or script_json.parent / f"{slugify(script['title'])}.mp4"
    try:
        rendered = render_short(script, gameplay_path=gameplay, audio_path=audio, output_path=output_path, font_name=font)
    except RenderError as exc:
        raise SystemExit(str(exc))
    print(f"Rendered Short: {rendered}")


def create_pipeline(
    count: int,
    out_dir: Path,
    backend: str,
    model: str,
    niches: str,
    subreddits: Optional[str],
    extra_subreddits: str,
    max_subreddits: int,
    per_subreddit: int,
    reddit_sort: str,
    reddit_time: str,
    make_voice: bool,
    voice: Optional[str],
    gameplay: Optional[Path],
    publish: bool,
    privacy_status: str,
    category_id: str,
    client_secrets: Path,
    token_path: Path,
) -> None:
    niche_list = parse_csv(niches) or DEFAULT_NICHES
    subreddit_list = resolve_subreddits(
        niches=niche_list,
        subreddits=parse_csv(subreddits),
        extra_subreddits=parse_csv(extra_subreddits),
        max_subreddits=max_subreddits,
    )
    try:
        items = run_pipeline(
            count=count,
            out_dir=out_dir,
            backend=backend,
            model=model,
            subreddits=subreddit_list,
            per_subreddit=per_subreddit,
            reddit_sort=reddit_sort,
            reddit_time=reddit_time,
            make_voice=make_voice,
            voice=voice,
            gameplay=gameplay,
            publish=publish,
            privacy_status=privacy_status,
            category_id=category_id,
            client_secrets=client_secrets,
            token_path=token_path,
        )
    except (ClaudeError, YouTubeError) as exc:
        raise SystemExit(str(exc))

    print(f"Pipeline created {len(items)} Short bundle(s) in {out_dir}")
    print(f"Searched {len(subreddit_list)} subreddit(s): {', '.join(subreddit_list[:12])}{'...' if len(subreddit_list) > 12 else ''}")
    print(f"Manifest: {out_dir / 'pipeline-manifest.json'}")
    for item in items:
        print(f"- {item.title}")
        if item.youtube_url:
            print(f"  uploaded: {item.youtube_url}")
        for warning in item.warnings:
            print(f"  warning: {warning}")


def publish_video(
    video: Path,
    script_json: Path,
    privacy_status: str,
    category_id: str,
    title: Optional[str],
    description: Optional[str],
    tags: str,
    made_for_kids: bool,
    client_secrets: Path,
    token_path: Path,
) -> None:
    script = load_script(script_json)
    agent = YouTubeAgent(client_secrets=client_secrets, token_path=token_path)
    resolved_title = title or str(script["title"])
    resolved_description = description or make_upload_description(script)
    resolved_tags = normalize_tags([*script.get("hashtags", []), *parse_csv(tags)])
    try:
        result = agent.upload_video(
            video_path=video,
            title=resolved_title,
            description=resolved_description,
            tags=resolved_tags,
            privacy_status=privacy_status,
            category_id=category_id,
            made_for_kids=made_for_kids,
        )
    except YouTubeError as exc:
        raise SystemExit(str(exc))

    out_path = script_json.parent / f"{script_json.stem}-youtube-upload.json"
    out_path.write_text(json.dumps(result.response, indent=2), encoding="utf-8")
    print(f"Uploaded: {result.url}")
    print(f"Upload response: {out_path}")


def report_analytics(
    start_date: Optional[str],
    end_date: Optional[str],
    days: int,
    metrics: str,
    dimensions: str,
    video_ids: str,
    manifest: Optional[Path],
    sort: str,
    max_results: int,
    currency: str,
    out: Path,
    client_secrets: Path,
    token_path: Path,
) -> None:
    if not start_date or not end_date:
        date_range = default_date_range(days=days)
        start_date = start_date or date_range["start_date"]
        end_date = end_date or date_range["end_date"]

    agent = YouTubeAgent(client_secrets=client_secrets, token_path=token_path)
    resolved_video_ids = parse_csv(video_ids)
    if manifest and not resolved_video_ids:
        resolved_video_ids = video_ids_from_manifest(manifest)
    try:
        report = agent.analytics_report(
            start_date=start_date,
            end_date=end_date,
            metrics=metrics,
            dimensions=dimensions or None,
            video_ids=resolved_video_ids,
            sort=sort,
            max_results=max_results,
            currency=currency,
        )
    except YouTubeError as exc:
        raise SystemExit(str(exc))

    write_report(report, out)
    print(f"Analytics report: {out}")
    print(table_preview(report))


def video_ids_from_manifest(manifest: Path) -> list:
    if not manifest.exists():
        raise SystemExit(f"Manifest does not exist: {manifest}")
    data = json.loads(manifest.read_text(encoding="utf-8"))
    return [
        str(item["youtube_video_id"])
        for item in data
        if isinstance(item, dict) and item.get("youtube_video_id")
    ]


def default_hook(topic: str) -> str:
    cleaned = topic.rstrip(".")
    return f"{cleaned} sounds simple, but the interesting part is what happens next."


def build_script(brief: Brief, backend: str, model: str):
    if backend == "template":
        return make_script(brief)
    try:
        return make_claude_script(brief, model=model)
    except ClaudeError as exc:
        raise SystemExit(str(exc))


if __name__ == "__main__":
    main()

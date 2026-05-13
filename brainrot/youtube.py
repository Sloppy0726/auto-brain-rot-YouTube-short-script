from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


YOUTUBE_UPLOAD_SCOPE = "https://www.googleapis.com/auth/youtube.upload"
YOUTUBE_READONLY_SCOPE = "https://www.googleapis.com/auth/youtube.readonly"
YOUTUBE_ANALYTICS_READONLY_SCOPE = "https://www.googleapis.com/auth/yt-analytics.readonly"
YOUTUBE_SCOPES = [
    YOUTUBE_UPLOAD_SCOPE,
    YOUTUBE_READONLY_SCOPE,
    YOUTUBE_ANALYTICS_READONLY_SCOPE,
]


class YouTubeError(RuntimeError):
    pass


@dataclass
class UploadResult:
    video_id: str
    url: str
    response: Dict[str, Any]


class YouTubeAgent:
    def __init__(
        self,
        client_secrets: Path = Path("client_secrets.json"),
        token_path: Path = Path(".secrets/youtube-token.json"),
    ) -> None:
        self.client_secrets = client_secrets
        self.token_path = token_path

    def upload_video(
        self,
        video_path: Path,
        title: str,
        description: str,
        tags: Optional[List[str]] = None,
        privacy_status: str = "private",
        category_id: str = "22",
        made_for_kids: bool = False,
    ) -> UploadResult:
        if privacy_status not in {"private", "unlisted", "public"}:
            raise YouTubeError("privacy_status must be one of: private, unlisted, public")
        if not video_path.exists():
            raise YouTubeError(f"Video file does not exist: {video_path}")

        _, _, _, build, MediaFileUpload, HttpError = import_google_clients()
        youtube = build_service(
            api_name="youtube",
            api_version="v3",
            client_secrets=self.client_secrets,
            token_path=self.token_path,
            scopes=YOUTUBE_SCOPES,
            build=build,
        )

        body = {
            "snippet": {
                "title": truncate(title, 100),
                "description": description,
                "tags": tags or [],
                "categoryId": category_id,
            },
            "status": {
                "privacyStatus": privacy_status,
                "selfDeclaredMadeForKids": made_for_kids,
            },
        }
        media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True, mimetype="video/*")
        request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

        response = None
        while response is None:
            try:
                _, response = request.next_chunk()
            except HttpError as exc:
                raise YouTubeError(f"YouTube upload failed: {exc}") from exc

        video_id = response.get("id")
        if not video_id:
            raise YouTubeError(f"Upload finished without a video id: {response}")
        return UploadResult(
            video_id=video_id,
            url=f"https://www.youtube.com/watch?v={video_id}",
            response=response,
        )

    def analytics_report(
        self,
        start_date: str,
        end_date: str,
        metrics: str = "views,estimatedMinutesWatched,averageViewDuration,likes,subscribersGained",
        dimensions: Optional[str] = "video",
        video_ids: Optional[List[str]] = None,
        sort: str = "-views",
        max_results: int = 25,
        currency: str = "USD",
    ) -> Dict[str, Any]:
        _, _, _, build, _, HttpError = import_google_clients()
        analytics = build_service(
            api_name="youtubeAnalytics",
            api_version="v2",
            client_secrets=self.client_secrets,
            token_path=self.token_path,
            scopes=YOUTUBE_SCOPES,
            build=build,
        )

        params: Dict[str, Any] = {
            "ids": "channel==MINE",
            "startDate": start_date,
            "endDate": end_date,
            "metrics": metrics,
            "sort": sort,
            "maxResults": max_results,
            "currency": currency,
        }
        if dimensions:
            params["dimensions"] = dimensions
        if video_ids:
            params["filters"] = "video==" + ",".join(video_ids)
            if dimensions and "video" not in [item.strip() for item in dimensions.split(",")]:
                params["dimensions"] = f"{dimensions},video"

        try:
            return analytics.reports().query(**params).execute()
        except HttpError as exc:
            raise YouTubeError(f"YouTube analytics query failed: {exc}") from exc


def default_date_range(days: int = 7) -> Dict[str, str]:
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=days - 1)
    return {"start_date": start.isoformat(), "end_date": end.isoformat()}


def make_upload_description(script: Dict[str, Any]) -> str:
    narration = str(script.get("narration", "")).strip()
    hashtags = " ".join(str(tag) for tag in script.get("hashtags", []))
    notes = [
        "Original short-form explainer.",
        "Sources should be checked before public release.",
    ]
    parts = [narration, hashtags, "\n".join(notes)]
    return "\n\n".join(part for part in parts if part).strip()


def write_report(report: Dict[str, Any], out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.suffix.lower() == ".csv":
        write_report_csv(report, out_path)
    else:
        out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return out_path


def write_report_csv(report: Dict[str, Any], out_path: Path) -> None:
    headers = [column["name"] for column in report.get("columnHeaders", [])]
    rows = report.get("rows", [])
    with out_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        if headers:
            writer.writerow(headers)
        writer.writerows(rows)


def import_google_clients():
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError
        from googleapiclient.http import MediaFileUpload
    except ImportError as exc:
        raise YouTubeError("Install YouTube support with: pip install -e '.[youtube]'") from exc
    return Request, Credentials, InstalledAppFlow, build, MediaFileUpload, HttpError


def build_service(
    api_name: str,
    api_version: str,
    client_secrets: Path,
    token_path: Path,
    scopes: List[str],
    build,
):
    credentials = get_credentials(client_secrets=client_secrets, token_path=token_path, scopes=scopes)
    return build(api_name, api_version, credentials=credentials, cache_discovery=False)


def get_credentials(client_secrets: Path, token_path: Path, scopes: List[str]):
    Request, Credentials, InstalledAppFlow, _, _, _ = import_google_clients()

    credentials = None
    if token_path.exists():
        credentials = Credentials.from_authorized_user_file(str(token_path), scopes)
        if hasattr(credentials, "has_scopes") and not credentials.has_scopes(scopes):
            credentials = None

    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())

    if not credentials or not credentials.valid:
        if not client_secrets.exists():
            raise YouTubeError(
                f"Missing OAuth client secrets at {client_secrets}. "
                "Create an OAuth desktop client in Google Cloud and download it as client_secrets.json."
            )
        flow = InstalledAppFlow.from_client_secrets_file(str(client_secrets), scopes)
        credentials = flow.run_local_server(port=0)
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(credentials.to_json(), encoding="utf-8")

    return credentials


def parse_csv(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def truncate(value: str, limit: int) -> str:
    clean = " ".join(value.split())
    if len(clean) <= limit:
        return clean
    return clean[: limit - 1].rstrip() + "..."


def table_preview(report: Dict[str, Any], limit: int = 10) -> str:
    headers = [column["name"] for column in report.get("columnHeaders", [])]
    rows = report.get("rows", [])[:limit]
    if not headers:
        return "No columns returned."
    lines = [" | ".join(headers)]
    lines.append(" | ".join("---" for _ in headers))
    for row in rows:
        lines.append(" | ".join(str(value) for value in row))
    if not rows:
        lines.append("No rows returned.")
    return "\n".join(lines)


def normalize_tags(tags: Iterable[str]) -> List[str]:
    seen = set()
    normalized: List[str] = []
    for tag in tags:
        clean = tag.strip().lstrip("#")
        key = clean.lower()
        if clean and key not in seen:
            seen.add(key)
            normalized.append(clean)
    return normalized

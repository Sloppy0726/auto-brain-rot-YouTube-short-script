# Auto Brain Rot YouTube Short Script

A small local pipeline for making "interesting narration + satisfying gameplay" Shorts without copying other people's videos or scripts.

It can:

- Run a simple three-agent workflow: Idea Agent, Script Agent, Video Agent.
- Run a Publisher Agent for YouTube upload and analytics reporting.
- Generate 3 daily Short briefs across monetizable niches.
- Pull topic leads from many Reddit communities, then mark them for verification.
- Write 45-60 second narration scripts.
- Estimate punchy caption timing and export `.srt`.
- Generate macOS `say` voiceover audio.
- Render a 1080x1920 split-screen Short with captions on top and your gameplay on the bottom using `ffmpeg`.
- Use either the offline template backend or Claude through Anthropic's Messages API.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

For YouTube upload and analytics support:

```bash
pip install -e '.[youtube]'
```

For rendering final videos:

```bash
brew install ffmpeg
```

## Quick Start

Generate three scripts:

```bash
python -m brainrot create --count 3 --out-dir output/today
```

Generate three scripts with Claude:

```bash
export ANTHROPIC_API_KEY="your_api_key"
python -m brainrot create \
  --count 3 \
  --backend claude \
  --model claude-sonnet-4-5 \
  --out-dir output/today
```

Run the full agent pipeline:

```bash
export ANTHROPIC_API_KEY="your_api_key"
python -m brainrot pipeline \
  --count 3 \
  --backend claude \
  --niches scams,business,ai,internet,money \
  --extra-subreddits SideProject,ProductivityApps \
  --max-subreddits 60 \
  --out-dir output/today
```

Add voice and rendering when you have gameplay footage:

```bash
python -m brainrot pipeline \
  --count 3 \
  --backend claude \
  --make-voice \
  --voice Samantha \
  --gameplay assets/gameplay/example.mp4 \
  --out-dir output/today
```

Upload a rendered Short to YouTube:

```bash
python -m brainrot publish \
  --video output/today/final.mp4 \
  --script-json output/today/how-fake-qr-code-parking-tickets-work.json \
  --privacy-status private
```

Run the pipeline and publish any rendered videos:

```bash
python -m brainrot pipeline \
  --count 3 \
  --backend claude \
  --make-voice \
  --gameplay assets/gameplay/example.mp4 \
  --publish \
  --privacy-status private \
  --out-dir output/today
```

Report recent YouTube analytics:

```bash
python -m brainrot analytics \
  --days 7 \
  --dimensions video \
  --metrics views,estimatedMinutesWatched,averageViewDuration,likes,subscribersGained \
  --out output/analytics/last-7-days.csv
```

Report analytics for videos uploaded by a pipeline run:

```bash
python -m brainrot analytics \
  --manifest output/today/pipeline-manifest.json \
  --days 7 \
  --out output/analytics/pipeline-videos.csv
```

Generate one script for a specific topic:

```bash
python -m brainrot script \
  --topic "How fake QR code parking tickets work" \
  --niche scams \
  --backend claude \
  --out-dir output/qr-ticket
```

Generate voiceover audio with macOS `say`:

```bash
python -m brainrot voice output/qr-ticket/how-fake-qr-code-parking-tickets-work.json
```

Render a Short using gameplay you recorded yourself:

```bash
python -m brainrot render \
  output/qr-ticket/how-fake-qr-code-parking-tickets-work.json \
  --gameplay assets/gameplay/example.mp4 \
  --audio output/qr-ticket/how-fake-qr-code-parking-tickets-work.aiff \
  --out output/qr-ticket/final.mp4
```

## Recommended Daily Workflow

1. Idea Agent scans Reddit for fast-moving leads.
2. You pick or keep the strongest 3 hooks.
3. Script Agent asks Claude for original 45-60 second scripts.
4. You fact-check claims and add source links in the JSON.
5. Video Agent creates captions, optional voiceover, and optional split-screen renders.
6. Review the final video before uploading.

## Agents

Idea Agent:

- Reads hot, top, rising, or new posts from configured subreddits.
- Can use niche presets with dozens of default communities.
- Scores posts by upvotes and comment activity.
- Converts them into briefs without copying the post text.
- Falls back to the built-in topic bank if Reddit is unavailable.

Script Agent:

- Uses `--backend claude` for Anthropic's Messages API.
- Uses `--backend template` for offline draft scripts.
- Produces JSON, Markdown, and SRT caption files.

Video Agent:

- Uses macOS `say` when `--make-voice` is passed.
- Uses `ffmpeg` to render final split-screen videos when `--gameplay` is passed.
- Skips rendering and leaves warnings if required tools or assets are missing.

Publisher Agent:

- Uses YouTube Data API `videos.insert` for upload.
- Uses YouTube Analytics API `reports.query` for reporting.
- Saves OAuth tokens locally under `.secrets/`.
- Defaults uploads to `private`.

## YouTube API Setup

1. Create or choose a Google Cloud project.
2. Enable the YouTube Data API v3 and YouTube Analytics API.
3. Create an OAuth desktop app credential.
4. Download the credential as `client_secrets.json` in the repo root.
5. Run `python -m brainrot publish ...` or `python -m brainrot analytics ...`.
6. Complete the browser OAuth flow once; the token is saved to `.secrets/youtube-token.json`.

The YouTube upload agent uses these scopes:

- `https://www.googleapis.com/auth/youtube.upload`
- `https://www.googleapis.com/auth/youtube.readonly`
- `https://www.googleapis.com/auth/yt-analytics.readonly`

## Content Notes

Use this as an original-content assistant, not a scraper. YouTube can reject monetization for reused, repetitive, or low-originality videos. The safer version is:

- Original scripts.
- Your own voice or a consistent licensed AI voice.
- Self-recorded or licensed gameplay.
- Factual claims checked against reliable sources.
- A recognizable niche and editorial style.

## Project Layout

```text
brainrot/
  agents.py      Idea, script, and video agent workflow.
  cli.py         Command line interface.
  claude.py      Claude API backend.
  youtube.py     YouTube upload and analytics backend.
  topics.py      Niche/topic bank.
  scriptgen.py   Script and brief generation.
  captions.py    Caption timing and SRT export.
  render.py      ffmpeg renderer.
assets/
  gameplay/      Put your own gameplay clips here.
output/          Generated scripts, captions, audio, and videos.
```

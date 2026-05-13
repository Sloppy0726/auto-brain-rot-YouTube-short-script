# Auto Brain Rot YouTube Short Script

A small local pipeline for making "interesting narration + satisfying gameplay" Shorts without copying other people's videos or scripts.

It can:

- Run a simple three-agent workflow: Idea Agent, Script Agent, Video Agent.
- Run a Publisher Agent for YouTube upload and analytics reporting.
- Generate 3 daily Short briefs across monetizable niches.
- Pull topic leads from many Reddit communities, then mark them for verification.
- Write 45-60 second narration scripts.
- Estimate punchy caption timing and export `.srt`.
- Match your recorded voiceover files to generated scripts.
- Retiming captions to the actual recorded voiceover duration.
- Pick gameplay clips from a local gameplay library folder.
- Apply genre-aware visual templates with timed highlighted captions.
- Overlay an optional per-channel logo.
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

Run a fiction channel by genre:

```bash
python -m brainrot pipeline \
  --count 3 \
  --content-mode fiction \
  --fiction-genre micro-horror \
  --backend claude \
  --out-dir output/micro-horror
```

Run multiple fiction genres in one batch:

```bash
python -m brainrot pipeline \
  --count 4 \
  --content-mode fiction \
  --fiction-genre micro-horror,sci-fi-ai \
  --backend claude \
  --out-dir output/fiction-batch
```

Render with your recorded voiceover and gameplay footage:

```bash
python -m brainrot pipeline \
  --count 3 \
  --backend claude \
  --voiceover-dir assets/voiceovers \
  --gameplay-dir assets/gameplay/clips \
  --channel example-channel \
  --out-dir output/today
```

Put your gameplay/satisfying footage here:

```text
assets/gameplay/clips/
```

The pipeline picks one clip per script. The choice is deterministic by script slug so reruns are stable. Use `--gameplay-seed 42` to rotate selections.

Put channel logos here:

```text
assets/logos/example-channel/logo.png
```

Then use `--channel example-channel`. You can also force a specific logo with `--logo path/to/logo.png`.

When a voiceover is provided, captions are automatically retimed to the actual audio duration with `ffprobe`. This keeps the caption pace aligned with a human read instead of the estimated script speed. Use `--no-sync-captions` only if you want to keep the original generated timing.

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
  --voiceover-dir assets/voiceovers \
  --gameplay-dir assets/gameplay/clips \
  --channel example-channel \
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

Optional fallback: generate scratch voiceover audio with macOS `say`:

```bash
python -m brainrot voice output/qr-ticket/how-fake-qr-code-parking-tickets-work.json
```

Render a Short using gameplay and voiceover you recorded yourself:

```bash
python -m brainrot render \
  output/qr-ticket/how-fake-qr-code-parking-tickets-work.json \
  --gameplay assets/gameplay/example.mp4 \
  --voiceover assets/voiceovers/how-fake-qr-code-parking-tickets-work.wav \
  --channel example-channel \
  --out output/qr-ticket/final.mp4
```

## Recommended Daily Workflow

1. Choose `--content-mode nonfiction` or `--content-mode fiction`.
2. For nonfiction, Idea Agent scans Reddit for fast-moving leads.
3. For fiction, Idea Agent generates original story seeds for the selected `--fiction-genre`.
4. Script Agent asks Claude for original 45-60 second scripts.
5. You fact-check nonfiction claims or review fiction for originality.
6. Record the voiceover from the Markdown script.
7. Save the recording with the same slug as the script JSON.
8. Video Agent retimes captions to the recorded audio duration.
9. Drop reusable gameplay clips into `assets/gameplay/clips/`.
10. Video Agent matches the recorded audio, captions, and a gameplay clip into a split-screen render.
11. Review the final video before uploading.

Example:

```text
output/today/how-fake-qr-code-parking-tickets-work.json
assets/voiceovers/how-fake-qr-code-parking-tickets-work.wav
```

## Agents

Idea Agent:

- Reads hot, top, rising, or new posts from configured subreddits.
- Can use niche presets with dozens of default communities.
- Can skip Reddit and generate fiction seeds with `--content-mode fiction`.
- Scores posts by upvotes and comment activity.
- Converts them into briefs without copying the post text.
- Falls back to the built-in topic bank if Reddit is unavailable.

Fiction genres:

- `micro-horror`
- `sci-fi-ai`
- `moral-dilemma`
- `workplace-drama`
- `relationship-drama`

Two-person example:

```bash
# Person 1, channel A
python -m brainrot pipeline --content-mode fiction --fiction-genre micro-horror --out-dir output/person-1-horror

# Person 1, channel B
python -m brainrot pipeline --content-mode fiction --fiction-genre sci-fi-ai --out-dir output/person-1-sci-fi

# Person 2, channel A
python -m brainrot pipeline --content-mode fiction --fiction-genre moral-dilemma --out-dir output/person-2-dilemmas

# Person 2, channel B
python -m brainrot pipeline --content-mode fiction --fiction-genre workplace-drama --out-dir output/person-2-workplace
```

Script Agent:

- Uses `--backend claude` for Anthropic's Messages API.
- Uses `--backend template` for offline draft scripts.
- Produces JSON, Markdown, and SRT caption files.

Video Agent:

- Uses your recorded audio when `--voiceover` or `--voiceover-dir` is passed.
- Automatically syncs caption timing to the recorded audio duration.
- Matches `--voiceover-dir` files by script slug, with `.wav`, `.mp3`, `.m4a`, `.aac`, `.aiff`, `.aif`, `.flac`, or `.ogg`.
- Uses `--gameplay-dir` to pick from `.mp4`, `.mov`, `.m4v`, `.webm`, or `.mkv` clips.
- Uses `--gameplay` when you want to force one exact clip.
- Uses `--channel` to load `assets/logos/<channel>/logo.png`.
- Uses `--render-template auto` to style captions by fiction genre or nonfiction niche.
- Can still use macOS `say` when `--make-voice` is passed as a scratch fallback.
- Uses `ffmpeg` to render final split-screen videos when `--gameplay` or `--gameplay-dir` is passed.
- Skips rendering and leaves warnings if required tools or assets are missing.

Caption sync note:

- Current sync mode is duration-proportional: caption chunks are spread across the actual voiceover length.
- This handles slow or fast readers much better than script-estimated timing.
- For exact word-level karaoke timing, the next upgrade would add a transcription/alignment backend such as Whisper.

Rendered video look:

```text
1080x1920
+------------------------------+
| blurred gameplay background  |
| dark overlay                  |
| logo in the top-left          |
| timed highlighted captions    |
+------------------------------+
| cropped gameplay clip         |
| satisfying motion             |
+------------------------------+
```

Visual template keys:

- `auto`
- `scams`
- `business`
- `ai`
- `internet`
- `law`
- `money`
- `micro-horror`
- `sci-fi-ai`
- `moral-dilemma`
- `workplace-drama`
- `relationship-drama`

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
- Your own recorded voice.
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
  gameplay/
    clips/       Put reusable gameplay clips here.
  logos/         Put per-channel logos here.
  voiceovers/    Put your recorded narration files here.
output/          Generated scripts, captions, audio, and videos.
```

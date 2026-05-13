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
- Use either the offline template backend or OpenAI through the Responses API.

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

OpenAI examples assume this is set in your shell:

```bash
export OPENAI_API_KEY="your_api_key"
```

Generate three scripts with OpenAI:

```bash
python -m brainrot create --count 3 --out-dir output/today
```

Generate three offline template scripts without an API key:

```bash
python -m brainrot create \
  --count 3 \
  --backend template \
  --out-dir output/today
```

Run the full agent pipeline:

```bash
python -m brainrot pipeline \
  --count 3 \
  --backend openai \
  --model gpt-5-mini \
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
  --backend openai \
  --model gpt-5-mini \
  --out-dir output/micro-horror
```

Run multiple fiction genres in one batch:

```bash
python -m brainrot pipeline \
  --count 4 \
  --content-mode fiction \
  --fiction-genre micro-horror,sci-fi-ai \
  --backend openai \
  --model gpt-5-mini \
  --out-dir output/fiction-batch
```

Render with your recorded voiceover and gameplay footage:

```bash
python -m brainrot pipeline \
  --count 3 \
  --backend openai \
  --model gpt-5-mini \
  --voiceover-dir assets/voiceovers \
  --gameplay-dir assets/gameplay/clips \
  --music-dir assets/music \
  --music-volume 0.10 \
  --channel example-channel \
  --out-dir output/today
```

Put your gameplay/satisfying footage here:

```text
assets/gameplay/clips/
```

The pipeline picks one clip per script, then starts at a random-looking point inside that clip for the background segment. The choice is deterministic by script slug so reruns are stable. Use `--gameplay-seed 42` to rotate clip selections and start points.

Put quiet background music tracks here:

```text
assets/music/
```

Use `--music-dir assets/music --music-volume 0.10` to mix a low-volume music bed under your voiceover. Start low; `0.08` to `0.12` is usually enough.

You can also organize music by genre or niche:

```text
assets/music/micro-horror/
assets/music/sci-fi-ai/
assets/music/business/
assets/music/scams/
```

Then point a run at one folder, such as `--music-dir assets/music/micro-horror`.

Put channel logos here:

```text
assets/logos/example-channel/logo.png
```

Then use `--channel example-channel`. You can also force a specific logo with `--logo path/to/logo.png`.

When a voiceover is provided, captions are automatically retimed to the actual audio duration with `ffprobe`. This keeps the caption pace aligned with a human read instead of the estimated script speed. Use `--caption-sync word` for Whisper word timestamps, or `--no-sync-captions`/`--caption-sync none` if you want to keep the original generated timing.

For tighter sync to the actual spoken words, set `OPENAI_API_KEY` and use word mode:

```bash
export OPENAI_API_KEY="your_api_key"
python -m brainrot render \
  output/qr-ticket/how-fake-qr-code-parking-tickets-work.json \
  --gameplay assets/gameplay/example.mp4 \
  --voiceover assets/voiceovers/how-fake-qr-code-parking-tickets-work.wav \
  --music assets/music/background.mp3 \
  --music-volume 0.10 \
  --caption-sync word \
  --out output/qr-ticket/final.mp4
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
  --backend openai \
  --model gpt-5-mini \
  --voiceover-dir assets/voiceovers \
  --gameplay-dir assets/gameplay/clips \
  --music-dir assets/music \
  --music-volume 0.10 \
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
  --backend openai \
  --model gpt-5-mini \
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
  --gameplay-seed 42 \
  --voiceover assets/voiceovers/how-fake-qr-code-parking-tickets-work.wav \
  --music assets/music/background.mp3 \
  --music-volume 0.10 \
  --channel example-channel \
  --out output/qr-ticket/final.mp4
```

## End-to-End Workflow

Use this when you want to go from scripts to finished rendered Shorts.

### 1. Add API keys

Replace the placeholder values:

```bash
export OPENAI_API_KEY="your_openai_api_key_here"
```

`OPENAI_API_KEY` is used for both script generation with `--backend openai` and word-level caption sync with `--caption-sync word`.

### 2. Choose channel and content settings

Change these values for your channel:

```bash
COUNT=3
MODEL="gpt-5-mini"
CHANNEL="example-channel"
CONTENT_MODE="fiction"
FICTION_GENRE="micro-horror"
NICHES="scams,business,ai,internet,money"
OUT_DIR="output/today"
GAMEPLAY_SEED=42
CAPTION_SYNC="word"
MUSIC_VOLUME=0.10
PRIVACY_STATUS="private"
```

For nonfiction, use `CONTENT_MODE="nonfiction"` and remove the `--fiction-genre` line from the pipeline command.

Common parameters to change:

| Parameter | What it controls | Example values |
| --- | --- | --- |
| `COUNT` | How many scripts/videos to create in the run. | `1`, `3`, `10` |
| `MODEL` | OpenAI model used to write scripts. | `gpt-5-mini`, `gpt-5.2` |
| `CHANNEL` | Which logo folder to use from `assets/logos/<channel>/`. | `example-channel`, `horror-channel` |
| `CONTENT_MODE` | Whether ideas are nonfiction topics or fiction story seeds. | `fiction`, `nonfiction` |
| `FICTION_GENRE` | Fiction genre when `CONTENT_MODE="fiction"`. | `micro-horror`, `sci-fi-ai`, `moral-dilemma`, `workplace-drama`, `relationship-drama` |
| `NICHES` | Nonfiction topic niches when `CONTENT_MODE="nonfiction"`. | `scams,business,ai`, `internet,law,money` |
| `OUT_DIR` | Where generated scripts, captions, transcripts, manifests, and videos are saved. | `output/today`, `output/horror-batch-1` |
| `GAMEPLAY_SEED` | Changes which gameplay clip and start point are selected. Same seed means stable reruns. | `42`, `100`, `999` |
| `CAPTION_SYNC` | Caption timing mode. | `word`, `duration`, `none` |
| `MUSIC_VOLUME` | Background music volume under the voiceover. | `0.08`, `0.10`, `0.12` |
| `PRIVACY_STATUS` | YouTube privacy setting when publishing. | `private`, `unlisted`, `public` |

### 3. Generate scripts first

```bash
python -m brainrot pipeline \
  --count "$COUNT" \
  --backend openai \
  --model "$MODEL" \
  --content-mode "$CONTENT_MODE" \
  --fiction-genre "$FICTION_GENRE" \
  --channel "$CHANNEL" \
  --out-dir "$OUT_DIR"
```

Review the generated `.md` files in `output/today/`, then record the voiceover for each script.

For nonfiction runs, add `--niches "$NICHES"` and remove `--fiction-genre "$FICTION_GENRE"`.

### 4. Add voiceovers, gameplay, and logo

Save each recorded voiceover with the same slug as its script JSON:

```text
output/today/my-story-title.json
assets/voiceovers/my-story-title.wav
```

Put long gameplay source clips here:

```text
assets/gameplay/clips/
```

Put background music tracks here:

```text
assets/music/
```

For tighter control, use a genre/niche folder such as `assets/music/micro-horror/` or `assets/music/business/`.

Put the channel logo here:

```text
assets/logos/example-channel/logo.png
```

Change `example-channel` to match your `CHANNEL` value.

### 5. Render finished Shorts

This matches voiceovers by filename, picks a gameplay clip, chooses a random-looking section inside long gameplay files, syncs captions to spoken words with Whisper, and renders the videos:

```bash
python -m brainrot pipeline \
  --count "$COUNT" \
  --backend openai \
  --model "$MODEL" \
  --content-mode "$CONTENT_MODE" \
  --fiction-genre "$FICTION_GENRE" \
  --voiceover-dir assets/voiceovers \
  --gameplay-dir assets/gameplay/clips \
  --music-dir assets/music \
  --music-volume "$MUSIC_VOLUME" \
  --caption-sync "$CAPTION_SYNC" \
  --gameplay-seed "$GAMEPLAY_SEED" \
  --channel "$CHANNEL" \
  --out-dir "$OUT_DIR"
```

Change `GAMEPLAY_SEED` when you want different gameplay clips or different start points.

### 6. Review outputs

Check these files:

```text
output/today/pipeline-manifest.json
output/today/*.mp4
output/today/*.srt
output/today/*.transcript.json
```

If captions feel too loose but you do not want to use OpenAI transcription, change `--caption-sync word` to `--caption-sync duration`.

### 7. Publish after review

Only add `--publish` once the rendered Shorts look good:

```bash
python -m brainrot pipeline \
  --count "$COUNT" \
  --backend openai \
  --model "$MODEL" \
  --content-mode "$CONTENT_MODE" \
  --fiction-genre "$FICTION_GENRE" \
  --voiceover-dir assets/voiceovers \
  --gameplay-dir assets/gameplay/clips \
  --music-dir assets/music \
  --music-volume "$MUSIC_VOLUME" \
  --caption-sync "$CAPTION_SYNC" \
  --gameplay-seed "$GAMEPLAY_SEED" \
  --channel "$CHANNEL" \
  --publish \
  --privacy-status "$PRIVACY_STATUS" \
  --out-dir "$OUT_DIR"
```

Change `PRIVACY_STATUS` to `unlisted` or `public` only when you are ready.

## Recommended Daily Workflow

1. Choose `--content-mode nonfiction` or `--content-mode fiction`.
2. For nonfiction, Idea Agent scans Reddit for fast-moving leads.
3. For fiction, Idea Agent generates original story seeds for the selected `--fiction-genre`.
4. Script Agent asks OpenAI for original 45-60 second scripts.
5. You fact-check nonfiction claims or review fiction for originality.
6. Record the voiceover from the Markdown script.
7. Save the recording with the same slug as the script JSON.
8. Video Agent retimes captions to the recorded audio duration.
9. Drop reusable gameplay clips into `assets/gameplay/clips/`.
10. Drop quiet background music tracks into `assets/music/`.
11. Video Agent matches the recorded audio, music, captions, and a gameplay clip into a split-screen render.
12. Review the final video before uploading.

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

- Uses `--backend openai` for OpenAI's Responses API.
- Uses `--backend template` for offline draft scripts.
- Produces JSON, Markdown, and SRT caption files.

Video Agent:

- Uses your recorded audio when `--voiceover` or `--voiceover-dir` is passed.
- Uses `--music` or `--music-dir` to add a quiet background music bed.
- Uses `--music-volume` to control music loudness. Default is `0.10`.
- Automatically syncs caption timing to the recorded audio duration by default.
- Uses `--caption-sync word` to transcribe the voiceover with Whisper and time captions from returned word timestamps.
- Matches `--voiceover-dir` files by script slug, with `.wav`, `.mp3`, `.m4a`, `.aac`, `.aiff`, `.aif`, `.flac`, or `.ogg`.
- Uses `--gameplay-dir` to pick from `.mp4`, `.mov`, `.m4v`, `.webm`, or `.mkv` clips.
- Uses a random-looking start point inside long gameplay clips, so one 1-2 hour source file can produce many different Shorts.
- Uses `--gameplay` when you want to force one exact clip, and `--gameplay-start` when you want to force the exact start time in seconds.
- Uses `--channel` to load `assets/logos/<channel>/logo.png`.
- Uses `--render-template auto` to style captions by fiction genre or nonfiction niche.
- Can still use macOS `say` when `--make-voice` is passed as a scratch fallback.
- Uses `ffmpeg` to render final split-screen videos when `--gameplay` or `--gameplay-dir` is passed.
- Skips rendering and leaves warnings if required tools or assets are missing.

Caption sync note:

- `--caption-sync duration` is the default cheap/local mode: caption chunks are spread across the actual voiceover length.
- `--caption-sync word` sends the voiceover to OpenAI Whisper with word timestamp output and rebuilds caption chunks from those timings.
- `--caption-sync none` leaves the original generated captions unchanged. `--no-sync-captions` is kept as a compatibility alias.

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
  openai.py      OpenAI script backend.
  youtube.py     YouTube upload and analytics backend.
  topics.py      Niche/topic bank.
  scriptgen.py   Script and brief generation.
  captions.py    Caption timing and SRT export.
  render.py      ffmpeg renderer.
assets/
  gameplay/
    clips/       Put reusable gameplay clips here.
  logos/         Put per-channel logos here.
  music/         Put background music tracks here.
  voiceovers/    Put your recorded narration files here.
output/          Generated scripts, captions, audio, and videos.
```

# ClipTales 🎬

A fully automated faceless TikTok channel. Claude invents a topic in your
niche, writes a 60–90 second story, picks stock footage scene by scene, the
pipeline stitches + narrates it, and posts it to TikTok. Zero input per video.

```
python run.py auto
   │
   ▼  Claude invents the next video in your NICHE
topic + 75s script + caption + hashtags + scene queries
   │
   ▼  Pexels API (free, licensed for commercial use)
portrait stock clips, one per scene
   │
   ▼  ffmpeg: 1080x1920 @30fps, fast cuts, TTS narration
output/auto_20260610_180000.mp4   (61+ seconds — monetization eligible)
   │
   ▼  TikTok Content Posting API (labeled as AI-generated)
posted ✅  topic logged so it's never repeated
```

There's also a **folder mode** (`python run.py once`) that narrates clips you
drop into `clips/` — your own footage monetizes best of all.

## Why this design makes money (and scrapers don't)

TikTok's **Creator Rewards Program** is the direct payout, and it has hard
rules baked into this pipeline:

| Requirement | How ClipTales handles it |
|---|---|
| Videos must be **over 1 minute** | `TARGET_DURATION_SECONDS=75` default; warns if narration lands under 60s |
| Content must be **original** | The AI story *is* the original work; visuals are licensed stock, not reposts |
| 10k followers + 100k views/30 days to join | Consistency — autopilot posts on a schedule without you |
| AI content must be labeled | Posts are flagged `is_aigc` via the API |

Reposting other people's clips fails every one of those rows — repost accounts
get demonetized/banned, which is why this pipeline doesn't do it. Expect
roughly **$0.40–$1.00 per 1,000 qualified views** from Creator Rewards once
you're in. The bigger money long-term is layering on TikTok Shop affiliate
links and brand deals once the account has an audience in a clear niche.

## Setup

```bash
# system: ffmpeg
brew install ffmpeg          # or: sudo apt install ffmpeg

# python
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env         # then fill in:
```

1. **`ANTHROPIC_API_KEY`** — https://console.anthropic.com
2. **`PEXELS_API_KEY`** — free at https://www.pexels.com/api/ (auto mode only)
3. **TikTok developer app** — create one at https://developers.tiktok.com, add
   the **Content Posting API** product (Direct Post, `video.publish` scope),
   run the OAuth flow once, and put `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`,
   `TIKTOK_REFRESH_TOKEN` in `.env`.

> **Until TikTok audits your app, all API posts are forced private
> (SELF_ONLY).** That's your tuning period: run the pipeline, watch what it
> makes, adjust `NICHE`/`STORY_STYLE`, then apply for the audit and switch
> `TIKTOK_PRIVACY_LEVEL=PUBLIC_TO_EVERYONE`.

## Usage

```bash
python run.py plan      # preview the next topic/script — costs one Claude call, renders nothing
python run.py auto      # generate + render + post one video
python run.py watch     # full autopilot, one video per interval (default hourly)

python run.py story clips/myclip.mp4   # folder mode: preview a story for your clip
python run.py once                     # folder mode: narrate + post pending clips
python run.py watch --folder           # autopilot over your own clips
```

Cron instead of watch mode:

```bash
# two videos a day, 11am and 7pm
0 11,19 * * * cd /path/to/cliptales && .venv/bin/python run.py auto >> cliptales.log 2>&1
```

`ENABLE_UPLOAD=false` dry-runs everything (script, footage, render) without
posting — the rendered video lands in `output/` for you to review.

## Reliability features

- One failing video can't wedge the queue — after 3 attempts an item is
  skipped and logged in `processed.json` with its error.
- Stories are cached to disk before upload, so a failed TikTok post never
  pays for the same Claude call twice.
- `processed.json` writes are atomic; a corrupt file is quarantined, never
  silently reset (which would cause re-posting).
- Credentials are checked at startup, before any money is spent.
- Files mid-copy into `clips/` are detected and skipped until stable.

## Tuning

- `NICHE` — the single biggest lever. Specific beats broad: "abandoned places
  and the stories behind them" outperforms "interesting facts".
- `STORY_STYLE` — narration personality.
- `TTS_VOICE` — any edge-tts voice (`edge-tts --list-voices`).
- `MAX_POSTS_PER_RUN` / `WATCH_INTERVAL_SECONDS` — pacing. 1–3 good videos a
  day beats 10 mediocre ones; the algorithm rewards watch time, not volume.

## Project layout

```
cliptales/
  config.py     # all env-driven settings
  story.py      # Claude: clip stories + auto-mode video plans (structured output)
  sourcing.py   # Pexels stock footage search + download
  compose.py    # scene normalization (1080x1920@30) + concat to narration length
  voiceover.py  # edge-tts narration, ducked mix, never truncates video
  frames.py     # ffmpeg frame extraction + probing
  tiktok.py     # Content Posting API: token refresh, chunked upload, AIGC label
  state.py      # atomic processed.json, failure tracking, topic history
  pipeline.py   # orchestration + preflight checks
run.py          # CLI: auto / watch / once / plan / story
```

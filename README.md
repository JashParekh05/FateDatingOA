# ClipTales 🎬

Drop video clips in a folder → AI writes a playful story about them → a voiceover
gets rendered onto the clip → it posts to TikTok. Fully automated.

```
clips/cat_fail.mp4
   │
   ▼  Claude looks at frames from the clip
"This cat had ONE job..."        ← story + caption + hashtags
   │
   ▼  edge-tts + ffmpeg
output/cat_fail_narrated.mp4     ← voiceover mixed over the clip
   │
   ▼  TikTok Content Posting API
posted ✅  (tracked in processed.json, never posts twice)
```

## Setup

### 1. System dependencies

You need `ffmpeg` (which includes `ffprobe`):

```bash
# macOS
brew install ffmpeg
# Ubuntu/Debian
sudo apt install ffmpeg
```

### 2. Python

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill it in
```

### 3. Anthropic API key

Get one at https://console.anthropic.com and put it in `.env` as
`ANTHROPIC_API_KEY`.

### 4. TikTok developer app (the annoying part)

TikTok only allows automated posting through their official **Content Posting
API**, so you need a developer app:

1. Create an app at https://developers.tiktok.com
2. Add the **Content Posting API** product and request the **Direct Post**
   configuration with the `video.publish` scope.
3. Run through the OAuth flow once with your TikTok account to get a
   **refresh token** (TikTok's [Login Kit docs](https://developers.tiktok.com/doc/login-kit-web)
   walk through it). Put `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`, and
   `TIKTOK_REFRESH_TOKEN` in `.env`. The app refreshes access tokens
   automatically from there.

> **Important:** until TikTok audits and approves your app, the API forces all
> posts to **private (SELF_ONLY)** — only you can see them. That's fine for
> testing the pipeline end-to-end. Apply for the audit in the developer portal
> when you're ready to post publicly, then set
> `TIKTOK_PRIVACY_LEVEL=PUBLIC_TO_EVERYONE`.

## Usage

```bash
# Preview the AI story for a clip without rendering or posting
python run.py story clips/cat_fail.mp4

# Process the next pending clip (story -> voiceover -> post) and exit
python run.py once

# Full autopilot: check the clips folder every hour
python run.py watch
```

Or schedule it with cron instead of watch mode:

```bash
# post one clip every day at 6pm
0 18 * * * cd /path/to/cliptales && .venv/bin/python run.py once >> cliptales.log 2>&1
```

Set `ENABLE_UPLOAD=false` in `.env` to dry-run the whole pipeline (story +
voiceover render) without posting anything.

## Tuning the vibe

- `STORY_STYLE` — the personality of the narration. This is the biggest lever
  for making content feel like *yours* instead of generic AI output.
- `TTS_VOICE` — any [edge-tts voice](https://github.com/rany2/edge-tts#voice-list),
  e.g. `en-US-AriaNeural`, `en-GB-RyanNeural`. List them with
  `edge-tts --list-voices`.
- `FRAMES_PER_CLIP` — more frames = Claude sees more of the clip (and costs a
  bit more per story).
- `MAX_POSTS_PER_RUN` — keep this at 1–2. Spamming posts tanks reach and can
  get an account flagged.

## Things to know before chasing the bag 💰

- **TikTok's rules:** you must own the rights to the clips you post, and
  TikTok requires AI-generated content to be labeled (there's an AI-generated
  content toggle on posts; spammy unlabeled AI content is exactly what their
  moderation targets). Monetization programs (Creator Rewards) also have
  originality requirements — AI narration over *your own* clips qualifies a
  lot better than reposted content.
- **Quality beats volume:** the pipeline can post as fast as you feed it, but
  the algorithm rewards watch time, not upload count. One good clip a day
  outperforms ten mediocre ones.
- **Review before going public:** while your app is in SELF_ONLY mode, watch
  what it produces. Tune `STORY_STYLE` until the voice is right, *then* apply
  for the audit.

## Project layout

```
cliptales/
  config.py     # all env-driven settings
  frames.py     # ffmpeg frame extraction
  story.py      # Claude vision -> story/caption/hashtags (structured output)
  voiceover.py  # edge-tts narration mixed over the clip
  tiktok.py     # Content Posting API: token refresh, chunked upload, status poll
  state.py      # processed.json bookkeeping
  pipeline.py   # glue
run.py          # CLI: once / watch / story
```

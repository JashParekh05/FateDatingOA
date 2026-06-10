"""Configuration loaded from environment variables (and .env if present)."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent

# --- Folders ---
CLIPS_DIR = Path(os.environ.get("CLIPS_DIR", ROOT / "clips"))
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", ROOT / "output"))
STATE_FILE = Path(os.environ.get("STATE_FILE", ROOT / "processed.json"))

VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm", ".mkv", ".avi"}

# --- Anthropic ---
# ANTHROPIC_API_KEY is read by the SDK directly from the environment.
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-8")
FRAMES_PER_CLIP = int(os.environ.get("FRAMES_PER_CLIP", "6"))

# Persona/vibe for the generated stories. Tweak freely.
STORY_STYLE = os.environ.get(
    "STORY_STYLE",
    "playful, witty, slightly absurd internet humor — like a friend narrating "
    "the clip with way too much enthusiasm",
)

# --- Voiceover ---
ENABLE_VOICEOVER = os.environ.get("ENABLE_VOICEOVER", "true").lower() == "true"
TTS_VOICE = os.environ.get("TTS_VOICE", "en-US-GuyNeural")
TTS_RATE = os.environ.get("TTS_RATE", "+10%")
ORIGINAL_AUDIO_VOLUME = float(os.environ.get("ORIGINAL_AUDIO_VOLUME", "0.25"))

# --- Auto mode (self-sourced content from licensed stock footage) ---
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "")
# The niche the channel covers. Specific niches monetize better than random.
NICHE = os.environ.get(
    "NICHE",
    "mind-blowing true facts about history, nature, and science",
)
# Creator Rewards only pays on videos over 60 seconds — default safely above.
TARGET_DURATION_SECONDS = int(os.environ.get("TARGET_DURATION_SECONDS", "75"))
# Approximate spoken pace used to size scripts (words per second).
WORDS_PER_SECOND = 2.3

# --- TikTok ---
TIKTOK_CLIENT_KEY = os.environ.get("TIKTOK_CLIENT_KEY", "")
TIKTOK_CLIENT_SECRET = os.environ.get("TIKTOK_CLIENT_SECRET", "")
TIKTOK_REFRESH_TOKEN = os.environ.get("TIKTOK_REFRESH_TOKEN", "")
# SELF_ONLY until your TikTok app passes audit; then PUBLIC_TO_EVERYONE,
# MUTUAL_FOLLOW_FRIENDS, or FOLLOWER_OF_CREATOR.
TIKTOK_PRIVACY_LEVEL = os.environ.get("TIKTOK_PRIVACY_LEVEL", "SELF_ONLY")

# Set false to run the pipeline end-to-end without actually posting (dry run).
ENABLE_UPLOAD = os.environ.get("ENABLE_UPLOAD", "true").lower() == "true"

# --- Pacing ---
# How many clips to post per run. Keep this low — flooding TikTok with posts
# hurts reach and risks the account.
MAX_POSTS_PER_RUN = int(os.environ.get("MAX_POSTS_PER_RUN", "1"))
WATCH_INTERVAL_SECONDS = int(os.environ.get("WATCH_INTERVAL_SECONDS", "3600"))

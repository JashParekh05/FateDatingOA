"""Orchestration for both modes:

- auto:   Claude invents a topic -> Pexels stock footage -> narrated video -> post
- folder: clips you drop in clips/ -> Claude story -> narration -> post
"""

import json
import logging
import re
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from . import compose, config, sourcing, state, story, tiktok, voiceover

log = logging.getLogger("cliptales")


# --------------------------------------------------------------------------
# Auto mode — fully self-sourced content
# --------------------------------------------------------------------------

def create_auto_post() -> None:
    """Generate one complete video from scratch and post it."""
    plan = story.generate_plan(avoid_topics=state.recent_titles())
    key = "auto:" + re.sub(r"[^a-z0-9]+", "-", plan.title.lower()).strip("-")
    log.info("Topic: %s", plan.title)

    caption = story.full_caption(plan)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    final_video = config.OUTPUT_DIR / f"auto_{stamp}.mp4"

    try:
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            narration_mp3, narration_len = voiceover.narration_seconds(
                plan.story, workdir
            )
            log.info("Narration: %.0fs (%d words)", narration_len, len(plan.story.split()))
            if narration_len < 61:
                log.warning(
                    "Narration is under 60s — this video won't qualify for "
                    "Creator Rewards. Posting anyway; consider raising "
                    "TARGET_DURATION_SECONDS."
                )

            scene_clips = sourcing.fetch_scene_clips(plan.scene_queries, workdir / "scenes")
            silent_video = compose.build_video(
                scene_clips, narration_len, workdir / "assembled.mp4"
            )
            voiceover.mix(silent_video, narration_mp3, final_video)
            log.info("Rendered %s", final_video.name)

        _post(final_video, caption, key, plan)
    except Exception as e:
        failures = state.record_failure(key, str(e))
        log.exception("Auto post failed (attempt %d)", failures)
        raise


# --------------------------------------------------------------------------
# Folder mode — clips you supply
# --------------------------------------------------------------------------

def _is_stable(clip: Path, wait: float = 2.0) -> bool:
    """Skip files that are still being copied into the folder."""
    size = clip.stat().st_size
    time.sleep(wait)
    return clip.stat().st_size == size and size > 0


def _story_cache(clip: Path) -> Path:
    return config.OUTPUT_DIR / f"{clip.stem}.story.json"


def _get_story(clip: Path) -> story.StoryPackage:
    """Generate the story, or reuse a cached one from a previous failed run
    so retries don't pay for the same Claude call twice."""
    cache = _story_cache(clip)
    if cache.exists():
        log.info("Reusing cached story for %s", clip.name)
        return story.StoryPackage(**json.loads(cache.read_text()))
    pkg = story.generate_story(clip)
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(pkg.model_dump_json(indent=2))
    return pkg


def pending_clips() -> list[Path]:
    if not config.CLIPS_DIR.exists():
        return []
    return [
        p for p in sorted(config.CLIPS_DIR.iterdir())
        if p.suffix.lower() in config.VIDEO_EXTENSIONS and not state.is_done(p.name)
    ]


def process_clip(clip: Path) -> None:
    log.info("Processing %s", clip.name)
    pkg = _get_story(clip)
    caption = story.full_caption(pkg)
    log.info("Story: %s", pkg.title)

    if config.ENABLE_VOICEOVER:
        final_video = config.OUTPUT_DIR / f"{clip.stem}_narrated.mp4"
        if not final_video.exists():
            voiceover.add_voiceover(clip, pkg.story, final_video)
            log.info("Rendered voiceover -> %s", final_video.name)
    else:
        final_video = clip

    _post(final_video, caption, clip.name, pkg)
    _story_cache(clip).unlink(missing_ok=True)


# --------------------------------------------------------------------------
# Shared
# --------------------------------------------------------------------------

def _post(video: Path, caption: str, key: str, pkg: story.StoryPackage) -> None:
    if config.ENABLE_UPLOAD:
        publish_id = tiktok.upload_video(video, caption)
        log.info("Posted to TikTok (publish_id=%s)", publish_id)
    else:
        publish_id = None
        log.info("ENABLE_UPLOAD=false — skipping TikTok post (dry run)")

    state.mark_posted(
        key,
        title=pkg.title,
        caption=caption,
        story=pkg.story,
        rendered=str(video),
        publish_id=publish_id,
    )


def preflight() -> None:
    """Fail fast on missing credentials before spending money on generation."""
    import os
    problems = []
    if config.LLM_PROVIDER == "openai":
        if not os.environ.get("OPENAI_API_KEY"):
            problems.append("OPENAI_API_KEY is not set")
    elif config.LLM_PROVIDER == "groq":
        if not config.GROQ_API_KEY:
            problems.append("GROQ_API_KEY is not set (free key: console.groq.com)")
    elif not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        problems.append("ANTHROPIC_API_KEY is not set")
    if config.ENABLE_UPLOAD and not (
        config.TIKTOK_CLIENT_KEY and config.TIKTOK_CLIENT_SECRET and config.TIKTOK_REFRESH_TOKEN
    ):
        problems.append(
            "TikTok credentials missing (or set ENABLE_UPLOAD=false to dry-run)"
        )
    if problems:
        raise SystemExit("Cannot start:\n  - " + "\n  - ".join(problems))


def run_once(auto: bool) -> int:
    """Produce up to MAX_POSTS_PER_RUN posts. Returns count posted."""
    posted = 0

    if auto:
        for _ in range(config.MAX_POSTS_PER_RUN):
            try:
                create_auto_post()
                posted += 1
            except Exception:
                break  # already logged; don't burn more generations this run
        return posted

    # Folder mode: walk past failing clips so one bad file never blocks the rest.
    for clip in pending_clips():
        if posted >= config.MAX_POSTS_PER_RUN:
            break
        if not _is_stable(clip):
            log.info("%s is still being copied — skipping this run", clip.name)
            continue
        try:
            process_clip(clip)
            posted += 1
        except Exception as e:
            failures = state.record_failure(clip.name, str(e))
            gave_up = " — giving up on this clip" if failures >= state.MAX_FAILURES else ""
            log.exception("Failed on %s (attempt %d)%s", clip.name, failures, gave_up)

    if posted == 0 and not pending_clips():
        log.info("No new clips in %s", config.CLIPS_DIR)
    return posted

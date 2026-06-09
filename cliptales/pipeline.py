"""Orchestrate the full clip -> story -> voiceover -> TikTok pipeline."""

import logging
from pathlib import Path

from . import config, state, story, tiktok, voiceover

log = logging.getLogger("cliptales")


def pending_clips() -> list[Path]:
    if not config.CLIPS_DIR.exists():
        return []
    clips = [
        p for p in sorted(config.CLIPS_DIR.iterdir())
        if p.suffix.lower() in config.VIDEO_EXTENSIONS
        and not state.is_processed(p.name)
    ]
    return clips


def process_clip(clip: Path) -> None:
    log.info("Processing %s", clip.name)

    pkg = story.generate_story(clip)
    caption = story.full_caption(pkg)
    log.info("Story: %s", pkg.title)
    log.info("Caption: %s", caption)

    if config.ENABLE_VOICEOVER:
        final_video = config.OUTPUT_DIR / f"{clip.stem}_narrated.mp4"
        voiceover.add_voiceover(clip, pkg.story, final_video)
        log.info("Rendered voiceover -> %s", final_video.name)
    else:
        final_video = clip

    if config.ENABLE_UPLOAD:
        publish_id = tiktok.upload_video(final_video, caption)
        log.info("Posted to TikTok (publish_id=%s)", publish_id)
    else:
        publish_id = None
        log.info("ENABLE_UPLOAD=false — skipping TikTok post (dry run)")

    state.mark_processed(
        clip.name,
        title=pkg.title,
        caption=caption,
        story=pkg.story,
        rendered=str(final_video),
        publish_id=publish_id,
    )


def run_once() -> int:
    """Process up to MAX_POSTS_PER_RUN pending clips. Returns count posted."""
    clips = pending_clips()
    if not clips:
        log.info("No new clips in %s", config.CLIPS_DIR)
        return 0

    posted = 0
    for clip in clips[: config.MAX_POSTS_PER_RUN]:
        try:
            process_clip(clip)
            posted += 1
        except Exception:
            log.exception("Failed on %s — leaving it unmarked for retry", clip.name)
    return posted

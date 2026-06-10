"""Content generation: stories for existing clips, and full video plans for
auto mode (topic + script + stock-footage queries). Provider-agnostic — see
llm.py for the Anthropic/Groq switch."""

from pathlib import Path

from pydantic import BaseModel, Field

from . import config, frames, llm


class StoryPackage(BaseModel):
    title: str = Field(description="Short punchy internal title for the post")
    story: str = Field(
        description=(
            "The playful story narrating the clip, written to be read aloud as "
            "a voiceover. Hooks the viewer in the first sentence."
        )
    )
    caption: str = Field(
        description="TikTok caption, under 150 characters, no hashtags in it"
    )
    hashtags: list[str] = Field(
        description="4-6 relevant hashtags without the # symbol"
    )


class VideoPlan(StoryPackage):
    scene_queries: list[str] = Field(
        description=(
            "5-8 stock-footage search queries, one per scene of the story in "
            "order. Each is 2-4 concrete visual words (e.g. 'ocean storm "
            "waves', 'ancient rome colosseum'), no abstract concepts."
        )
    )


def _word_budget(seconds: float) -> int:
    return max(20, int(seconds * config.WORDS_PER_SECOND))


CLIP_SYSTEM_PROMPT = f"""You are a viral short-form video writer. You are shown \
frames sampled from a video clip in chronological order. Write a story about \
what's happening as if you watched the whole clip.

Style: {config.STORY_STYLE}

Rules:
- The story must work as a spoken voiceover laid over the clip.
- First sentence is the hook — make scrolling past feel impossible.
- Reference concrete things visible in the frames so it feels specific.
- Keep it clean enough for TikTok's content rules.
- The caption teases the story without spoiling it."""


def generate_story(video: Path) -> StoryPackage:
    """Look at frames from the clip and return a ready-to-post story package."""
    duration = frames.duration_seconds(video)
    images = frames.frames_as_base64(video, config.FRAMES_PER_CLIP)
    prompt = (
        f"The clip is {duration:.0f} seconds long. The story will be read "
        f"aloud over it, so it must be at most {_word_budget(duration)} "
        "words — it gets cut off otherwise. Write the story package."
    )
    return llm.generate(CLIP_SYSTEM_PROMPT, prompt, StoryPackage, images_b64=images)


AUTO_SYSTEM_PROMPT = f"""You are a viral short-form video writer running a \
faceless TikTok channel about: {config.NICHE}

You invent the topic, write the narration script, and choose stock footage.

Style: {config.STORY_STYLE}

Rules:
- The story must be TRUE and verifiable — fabricated facts kill channels.
- First sentence is the hook; end with a detail that rewards watching fully.
- scene_queries must be concrete and visual; stock sites have no footage of
  abstract ideas.
- Keep it clean enough for TikTok's content rules.
- The caption teases the story without spoiling it."""


def generate_plan(avoid_topics: list[str]) -> VideoPlan:
    """Invent a topic and full video plan for auto mode."""
    words = _word_budget(config.TARGET_DURATION_SECONDS)
    avoid = "\n".join(f"- {t}" for t in avoid_topics) or "- (none yet)"
    prompt = (
        f"Create the next video. The narration must be about {words} words "
        f"(roughly {config.TARGET_DURATION_SECONDS}s spoken — it MUST end up "
        "over 60 seconds for monetization, so do not write short).\n\n"
        f"Topics already covered, pick something different:\n{avoid}"
    )
    return llm.generate(AUTO_SYSTEM_PROMPT, prompt, VideoPlan)


def full_caption(pkg: StoryPackage) -> str:
    """Caption + hashtags as posted to TikTok (capped at TikTok's 2200 chars)."""
    tags = " ".join(f"#{t.lstrip('#')}" for t in pkg.hashtags)
    return f"{pkg.caption} {tags}"[:2200]

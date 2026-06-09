"""Generate a playful story, caption, and hashtags for a clip with Claude."""

from pathlib import Path

import anthropic
from pydantic import BaseModel, Field

from . import config, frames


class StoryPackage(BaseModel):
    title: str = Field(description="Short punchy internal title for the post")
    story: str = Field(
        description=(
            "The playful story narrating the clip, written to be read aloud as a "
            "voiceover. 3-6 sentences, hooks the viewer in the first sentence."
        )
    )
    caption: str = Field(
        description="TikTok caption, under 150 characters, no hashtags in it"
    )
    hashtags: list[str] = Field(
        description="4-6 relevant hashtags without the # symbol"
    )


SYSTEM_PROMPT = f"""You are a viral short-form video writer. You are shown frames \
sampled from a video clip in chronological order. Write a story about what's \
happening as if you watched the whole clip.

Style: {config.STORY_STYLE}

Rules:
- The story must work as a spoken voiceover laid over the clip.
- First sentence is the hook — make scrolling past feel impossible.
- Reference concrete things visible in the frames so it feels specific, not generic.
- Keep it clean enough for TikTok's content rules.
- The caption teases the story without spoiling it."""

_client = anthropic.Anthropic()


def generate_story(video: Path) -> StoryPackage:
    """Look at frames from the clip and return a ready-to-post story package."""
    images = frames.frames_as_base64(video, config.FRAMES_PER_CLIP)

    content = []
    for i, data in enumerate(images):
        content.append({"type": "text", "text": f"Frame {i + 1}:"})
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/jpeg", "data": data},
        })
    content.append({
        "type": "text",
        "text": "Write the story package for this clip.",
    })

    response = _client.messages.parse(
        model=config.ANTHROPIC_MODEL,
        max_tokens=16000,
        thinking={"type": "adaptive"},
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": content}],
        output_format=StoryPackage,
    )
    return response.parsed_output


def full_caption(pkg: StoryPackage) -> str:
    """Caption + hashtags as posted to TikTok (capped at TikTok's 2200 chars)."""
    tags = " ".join(f"#{t.lstrip('#')}" for t in pkg.hashtags)
    return f"{pkg.caption} {tags}"[:2200]

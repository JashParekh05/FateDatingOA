"""Render the story as a TTS voiceover and mix it over the original clip."""

import asyncio
import subprocess
import tempfile
from pathlib import Path

import edge_tts

from . import config, frames


def _synthesize(text: str, out_mp3: Path) -> None:
    async def run():
        tts = edge_tts.Communicate(text, voice=config.TTS_VOICE, rate=config.TTS_RATE)
        await tts.save(str(out_mp3))

    asyncio.run(run())


def add_voiceover(video: Path, story_text: str, out_video: Path) -> Path:
    """Mix a narrated voiceover over the clip; original audio is ducked.

    The output keeps the full video length. If the narration runs longer than
    the clip, the tail of the narration is cut with the video — keep stories
    short relative to clip length.
    """
    out_video.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        voice = Path(tmp) / "voice.mp3"
        _synthesize(story_text, voice)

        if frames.has_audio_stream(video):
            filter_complex = (
                f"[0:a]volume={config.ORIGINAL_AUDIO_VOLUME}[bg];"
                f"[bg][1:a]amix=inputs=2:duration=first[a]"
            )
            cmd = [
                "ffmpeg", "-y", "-v", "error",
                "-i", str(video), "-i", str(voice),
                "-filter_complex", filter_complex,
                "-map", "0:v", "-map", "[a]",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                str(out_video),
            ]
        else:
            cmd = [
                "ffmpeg", "-y", "-v", "error",
                "-i", str(video), "-i", str(voice),
                "-map", "0:v", "-map", "1:a", "-shortest",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                str(out_video),
            ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg mix failed: {result.stderr.strip()[:500]}")

    return out_video

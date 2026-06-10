"""Render the story as a TTS voiceover and mix it over the video."""

import asyncio
import subprocess
import tempfile
from pathlib import Path

import edge_tts

from . import config, frames


def synthesize(text: str, out_mp3: Path) -> None:
    async def run():
        tts = edge_tts.Communicate(text, voice=config.TTS_VOICE, rate=config.TTS_RATE)
        await tts.save(str(out_mp3))

    asyncio.run(run())


def narration_seconds(text: str, workdir: Path) -> tuple[Path, float]:
    """Synthesize narration and return (mp3 path, duration in seconds)."""
    mp3 = workdir / "narration.mp3"
    synthesize(text, mp3)
    return mp3, frames.duration_seconds(mp3)


def mix(video: Path, narration_mp3: Path, out_video: Path) -> Path:
    """Mix narration over the video. Output always keeps the full video length.

    If the video has original audio it is ducked underneath; either way the
    narration is padded with silence so the video is never truncated.
    """
    out_video.parent.mkdir(parents=True, exist_ok=True)

    if frames.has_audio_stream(video):
        # duration=first pins the mix to the original audio (= video) length.
        filter_complex = (
            f"[0:a]volume={config.ORIGINAL_AUDIO_VOLUME}[bg];"
            f"[1:a]apad[vo];"
            f"[bg][vo]amix=inputs=2:duration=first[a]"
        )
    else:
        # apad makes the narration infinite; -shortest then ends the output at
        # the (finite) video stream, so silence fills any gap after narration.
        filter_complex = "[1:a]apad[a]"

    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-i", str(video), "-i", str(narration_mp3),
        "-filter_complex", filter_complex,
        "-map", "0:v", "-map", "[a]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        str(out_video),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg mix failed: {result.stderr.strip()[-500:]}")
    return out_video


def add_voiceover(video: Path, story_text: str, out_video: Path) -> Path:
    """Convenience: synthesize + mix in one call (used by folder mode)."""
    with tempfile.TemporaryDirectory() as tmp:
        mp3, _ = narration_seconds(story_text, Path(tmp))
        return mix(video, mp3, out_video)

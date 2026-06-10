"""Assemble scene clips into one 9:16 video timed to the narration."""

import subprocess
import tempfile
from pathlib import Path

from . import frames

# Cap how long any single scene stays on screen — fast cuts retain viewers.
MAX_SCENE_SECONDS = 7.0


def _run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr.strip()[-500:]}")


def _normalize(src: Path, out: Path, seconds: float) -> None:
    """Scale/crop to 1080x1920@30fps and trim to the segment length."""
    _run([
        "ffmpeg", "-y", "-v", "error", "-i", str(src),
        "-t", f"{seconds:.2f}",
        "-vf",
        "scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,fps=30,setsar=1",
        "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        str(out),
    ])


def build_video(scene_clips: list[Path], narration_seconds: float, out: Path) -> Path:
    """Stitch scenes (looping through them if needed) to cover the narration."""
    out.parent.mkdir(parents=True, exist_ok=True)
    target = narration_seconds + 0.7  # small tail so audio never outruns video

    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        segments: list[Path] = []
        remaining = target
        i = 0
        while remaining > 0.05:
            src = scene_clips[i % len(scene_clips)]
            available = frames.duration_seconds(src)
            seg_len = min(remaining, available, MAX_SCENE_SECONDS)
            seg = tmpdir / f"seg_{i:03d}.mp4"
            _normalize(src, seg, seg_len)
            segments.append(seg)
            remaining -= seg_len
            i += 1

        concat_list = tmpdir / "concat.txt"
        concat_list.write_text(
            "".join(f"file '{s}'\n" for s in segments)
        )
        _run([
            "ffmpeg", "-y", "-v", "error",
            "-f", "concat", "-safe", "0", "-i", str(concat_list),
            "-c", "copy", str(out),
        ])
    return out

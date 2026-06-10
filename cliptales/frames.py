"""Extract representative frames from a video clip using ffmpeg/ffprobe."""

import base64
import json
import subprocess
import tempfile
from pathlib import Path


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"{cmd[0]} failed: {result.stderr.strip()[:500]}")
    return result


def probe(video: Path) -> dict:
    """Return ffprobe metadata (duration, streams) for a video file."""
    result = _run([
        "ffprobe", "-v", "error", "-print_format", "json",
        "-show_format", "-show_streams", str(video),
    ])
    return json.loads(result.stdout)


def duration_seconds(video: Path) -> float:
    return float(probe(video)["format"]["duration"])


def has_audio_stream(video: Path) -> bool:
    return any(s.get("codec_type") == "audio" for s in probe(video)["streams"])


def extract_frames(video: Path, count: int) -> list[bytes]:
    """Grab `count` JPEG frames evenly spaced through the clip."""
    total = duration_seconds(video)
    # Sample away from the very start/end, which are often black or mid-cut.
    timestamps = [total * (i + 0.5) / count for i in range(count)]

    frames = []
    with tempfile.TemporaryDirectory() as tmp:
        for i, ts in enumerate(timestamps):
            out = Path(tmp) / f"frame_{i}.jpg"
            _run([
                "ffmpeg", "-y", "-v", "error",
                "-ss", f"{ts:.2f}", "-i", str(video),
                "-frames:v", "1", "-q:v", "3",
                "-vf", "scale='min(1024,iw)':-2",
                str(out),
            ])
            frames.append(out.read_bytes())
    return frames


def frames_as_base64(video: Path, count: int) -> list[str]:
    return [
        base64.standard_b64encode(f).decode("utf-8")
        for f in extract_frames(video, count)
    ]

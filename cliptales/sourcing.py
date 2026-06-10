"""Fetch licensed stock footage from Pexels for auto-generated video plans.

Pexels videos are free for commercial use without attribution
(https://www.pexels.com/license/). A free API key is required:
https://www.pexels.com/api/
"""

import logging
from pathlib import Path

import requests

from . import config

log = logging.getLogger("cliptales")

SEARCH_URL = "https://api.pexels.com/videos/search"


class SourcingError(RuntimeError):
    pass


def _search(query: str) -> list[dict]:
    if not config.PEXELS_API_KEY:
        raise SourcingError("PEXELS_API_KEY is not set — get a free key at pexels.com/api")
    resp = requests.get(
        SEARCH_URL,
        headers={"Authorization": config.PEXELS_API_KEY},
        params={"query": query, "orientation": "portrait", "per_page": 5},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json().get("videos", [])


def _best_file(video: dict) -> str | None:
    """Pick the smallest video file that's still tall enough for 1080x1920."""
    candidates = [
        f for f in video.get("video_files", [])
        if f.get("height") and f["height"] >= 1280 and f.get("link")
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda f: f["height"])["link"]


def fetch_scene_clips(queries: list[str], workdir: Path) -> list[Path]:
    """Download one stock clip per scene query. Skips queries with no results."""
    workdir.mkdir(parents=True, exist_ok=True)
    clips: list[Path] = []
    seen_ids: set[int] = set()

    for i, query in enumerate(queries):
        chosen = None
        for video in _search(query):
            if video["id"] not in seen_ids and _best_file(video):
                chosen = video
                break
        if not chosen:
            log.warning("No stock footage found for query %r — skipping scene", query)
            continue

        seen_ids.add(chosen["id"])
        url = _best_file(chosen)
        out = workdir / f"scene_{i:02d}.mp4"
        with requests.get(url, stream=True, timeout=120) as r:
            r.raise_for_status()
            with open(out, "wb") as f:
                for chunk in r.iter_content(chunk_size=1 << 20):
                    f.write(chunk)
        clips.append(out)
        log.info("Scene %d: %r -> pexels video %s", i + 1, query, chosen["id"])

    if len(clips) < 2:
        raise SourcingError(
            f"Only found footage for {len(clips)} of {len(queries)} scenes — "
            "not enough to build a video. Try more concrete scene queries."
        )
    return clips

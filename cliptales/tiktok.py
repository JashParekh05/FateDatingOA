"""Upload videos via TikTok's official Content Posting API (direct post).

Flow: refresh access token -> init publish -> PUT video bytes -> poll status.
Requires a TikTok developer app with the Content Posting API product and the
`video.publish` scope. Until the app passes TikTok's audit, posts are forced
to SELF_ONLY (private) by TikTok regardless of the requested privacy level.

API docs: https://developers.tiktok.com/doc/content-posting-api-get-started/
"""

import time
from pathlib import Path

import requests

from . import config

OAUTH_TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
INIT_URL = "https://open.tiktokapis.com/v2/post/publish/video/init/"
STATUS_URL = "https://open.tiktokapis.com/v2/post/publish/status/fetch/"

# TikTok chunk rules: 5MB <= chunk <= 64MB; final chunk may absorb remainder.
MIN_CHUNK = 5 * 1024 * 1024
MAX_CHUNK = 64 * 1024 * 1024
DEFAULT_CHUNK = 10 * 1024 * 1024


class TikTokError(RuntimeError):
    pass


def get_access_token() -> str:
    """Exchange the long-lived refresh token for a fresh access token."""
    resp = requests.post(
        OAUTH_TOKEN_URL,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "client_key": config.TIKTOK_CLIENT_KEY,
            "client_secret": config.TIKTOK_CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": config.TIKTOK_REFRESH_TOKEN,
        },
        timeout=30,
    )
    data = resp.json()
    if "access_token" not in data:
        raise TikTokError(f"Token refresh failed: {data}")
    return data["access_token"]


def _chunk_plan(size: int) -> tuple[int, int]:
    """Return (chunk_size, total_chunk_count) per TikTok's upload rules."""
    if size <= MAX_CHUNK:
        return size, 1
    chunk = DEFAULT_CHUNK
    count = size // chunk  # remainder rides along with the final chunk
    return chunk, count


def upload_video(video: Path, caption: str) -> str:
    """Direct-post a video to TikTok. Returns the publish_id."""
    token = get_access_token()
    size = video.stat().st_size
    chunk_size, chunk_count = _chunk_plan(size)

    init_resp = requests.post(
        INIT_URL,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=UTF-8",
        },
        json={
            "post_info": {
                "title": caption,
                "privacy_level": config.TIKTOK_PRIVACY_LEVEL,
                "disable_comment": False,
                "disable_duet": False,
                "disable_stitch": False,
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": size,
                "chunk_size": chunk_size,
                "total_chunk_count": chunk_count,
            },
        },
        timeout=30,
    )
    init_data = init_resp.json()
    if init_data.get("error", {}).get("code") not in (None, "ok"):
        raise TikTokError(f"Init failed: {init_data['error']}")

    publish_id = init_data["data"]["publish_id"]
    upload_url = init_data["data"]["upload_url"]

    with open(video, "rb") as f:
        data = f.read()

    for i in range(chunk_count):
        start = i * chunk_size
        # Final chunk takes everything that's left.
        end = size - 1 if i == chunk_count - 1 else start + chunk_size - 1
        resp = requests.put(
            upload_url,
            headers={
                "Content-Type": "video/mp4",
                "Content-Range": f"bytes {start}-{end}/{size}",
            },
            data=data[start : end + 1],
            timeout=300,
        )
        if resp.status_code not in (200, 201, 206):
            raise TikTokError(
                f"Chunk {i + 1}/{chunk_count} upload failed "
                f"({resp.status_code}): {resp.text[:300]}"
            )

    _wait_for_publish(token, publish_id)
    return publish_id


def _wait_for_publish(token: str, publish_id: str, timeout_s: int = 300) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        resp = requests.post(
            STATUS_URL,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=UTF-8",
            },
            json={"publish_id": publish_id},
            timeout=30,
        )
        status = resp.json().get("data", {}).get("status", "")
        if status == "PUBLISH_COMPLETE":
            return
        if status == "FAILED":
            reason = resp.json()["data"].get("fail_reason", "unknown")
            raise TikTokError(f"Publish failed: {reason}")
        time.sleep(10)
    raise TikTokError(f"Publish timed out (publish_id={publish_id})")

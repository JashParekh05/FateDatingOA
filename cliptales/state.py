"""Track processed items so nothing posts twice and failures don't loop forever."""

import json
import os
import tempfile
from datetime import datetime, timezone

from . import config

MAX_FAILURES = 3


def load() -> dict:
    if not config.STATE_FILE.exists():
        return {}
    try:
        return json.loads(config.STATE_FILE.read_text())
    except json.JSONDecodeError:
        # Corrupt state (e.g. killed mid-write). Quarantine it instead of
        # crashing or silently forgetting what we already posted.
        backup = config.STATE_FILE.with_suffix(".corrupt")
        config.STATE_FILE.rename(backup)
        raise RuntimeError(
            f"State file was corrupt and moved to {backup}. Recover what you "
            "can from it into processed.json before running again, or the "
            "pipeline may re-post old clips."
        )


def _save(state: dict) -> None:
    # Atomic write: temp file + rename, so a crash can't corrupt the state.
    fd, tmp = tempfile.mkstemp(dir=config.STATE_FILE.parent, suffix=".tmp")
    with os.fdopen(fd, "w") as f:
        json.dump(state, f, indent=2, sort_keys=True)
    os.replace(tmp, config.STATE_FILE)


def is_done(key: str) -> bool:
    """Posted successfully, or failed enough times that we've given up."""
    entry = load().get(key)
    if not entry:
        return False
    return entry.get("status") == "posted" or entry.get("failures", 0) >= MAX_FAILURES


def mark_posted(key: str, **details) -> None:
    state = load()
    state[key] = {
        "status": "posted",
        "posted_at": datetime.now(timezone.utc).isoformat(),
        **details,
    }
    _save(state)


def record_failure(key: str, error: str) -> int:
    """Increment the failure count for an item. Returns the new count."""
    state = load()
    entry = state.get(key, {"status": "failing", "failures": 0})
    entry["failures"] = entry.get("failures", 0) + 1
    entry["last_error"] = error[:500]
    entry["last_failed_at"] = datetime.now(timezone.utc).isoformat()
    if entry["failures"] >= MAX_FAILURES:
        entry["status"] = "gave_up"
    state[key] = entry
    _save(state)
    return entry["failures"]


def recent_titles(limit: int = 25) -> list[str]:
    """Titles of recent posts, used to keep auto-generated topics fresh."""
    entries = sorted(
        load().values(), key=lambda e: e.get("posted_at", ""), reverse=True
    )
    return [e["title"] for e in entries if e.get("title")][:limit]

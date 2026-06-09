"""Track which clips have already been processed so nothing posts twice."""

import json
from datetime import datetime, timezone

from . import config


def load() -> dict:
    if config.STATE_FILE.exists():
        return json.loads(config.STATE_FILE.read_text())
    return {}


def is_processed(clip_name: str) -> bool:
    return clip_name in load()


def mark_processed(clip_name: str, **details) -> None:
    state = load()
    state[clip_name] = {
        "processed_at": datetime.now(timezone.utc).isoformat(),
        **details,
    }
    config.STATE_FILE.write_text(json.dumps(state, indent=2, sort_keys=True))

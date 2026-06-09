#!/usr/bin/env python3
"""ClipTales CLI.

  python run.py once    # process the next pending clip(s) and exit
  python run.py watch   # keep running, checking for new clips on an interval
  python run.py story <clip>  # generate + print a story only (no render/post)
"""

import argparse
import logging
import sys
import time
from pathlib import Path

from cliptales import config, pipeline, story

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("cliptales")


def main() -> int:
    parser = argparse.ArgumentParser(description="Clip -> AI story -> TikTok")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("once", help="process pending clips once and exit")
    watch = sub.add_parser("watch", help="run forever, polling for new clips")
    watch.add_argument(
        "--interval", type=int, default=config.WATCH_INTERVAL_SECONDS,
        help="seconds between checks (default from WATCH_INTERVAL_SECONDS)",
    )
    story_cmd = sub.add_parser("story", help="preview the AI story for one clip")
    story_cmd.add_argument("clip", type=Path)

    args = parser.parse_args()
    command = args.command or "once"

    config.CLIPS_DIR.mkdir(parents=True, exist_ok=True)
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if command == "story":
        pkg = story.generate_story(args.clip)
        print(f"\nTitle:   {pkg.title}")
        print(f"Story:   {pkg.story}")
        print(f"Caption: {story.full_caption(pkg)}\n")
        return 0

    if command == "once":
        pipeline.run_once()
        return 0

    log.info("Watching %s every %ss — Ctrl-C to stop", config.CLIPS_DIR, args.interval)
    while True:
        pipeline.run_once()
        time.sleep(args.interval)


if __name__ == "__main__":
    sys.exit(main())

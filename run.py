#!/usr/bin/env python3
"""ClipTales CLI.

  python run.py auto          # invent + render + post one video from scratch
  python run.py watch         # full autopilot: auto-post on an interval
  python run.py once          # process your own pending clips from clips/
  python run.py watch --folder      # autopilot over your own clips folder
  python run.py story <clip>        # preview the AI story for one clip
  python run.py plan                # preview an auto-mode topic/script (no render)
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
    parser = argparse.ArgumentParser(description="AI content -> TikTok, on autopilot")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("auto", help="generate and post one self-sourced video")
    sub.add_parser("once", help="process pending clips from clips/ once")
    watch = sub.add_parser("watch", help="run forever on an interval")
    watch.add_argument("--folder", action="store_true",
                       help="watch clips/ instead of auto-generating")
    watch.add_argument("--interval", type=int, default=config.WATCH_INTERVAL_SECONDS)
    sub.add_parser("plan", help="preview an auto-mode video plan (no render/post)")
    story_cmd = sub.add_parser("story", help="preview the AI story for one clip")
    story_cmd.add_argument("clip", type=Path)

    args = parser.parse_args()
    command = args.command or "auto"

    config.CLIPS_DIR.mkdir(parents=True, exist_ok=True)
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if command == "plan":
        from cliptales import state
        plan = story.generate_plan(avoid_topics=state.recent_titles())
        print(f"\nTopic:   {plan.title}")
        print(f"Script:  {plan.story}")
        print(f"Scenes:  {plan.scene_queries}")
        print(f"Caption: {story.full_caption(plan)}\n")
        return 0

    if command == "story":
        if not args.clip.exists():
            print(f"No such file: {args.clip}", file=sys.stderr)
            return 1
        pkg = story.generate_story(args.clip)
        print(f"\nTitle:   {pkg.title}")
        print(f"Story:   {pkg.story}")
        print(f"Caption: {story.full_caption(pkg)}\n")
        return 0

    pipeline.preflight()

    if command == "auto":
        pipeline.run_once(auto=True)
        return 0

    if command == "once":
        pipeline.run_once(auto=False)
        return 0

    auto = not args.folder
    mode = "auto-generating" if auto else f"watching {config.CLIPS_DIR}"
    log.info("Autopilot: %s every %ss — Ctrl-C to stop", mode, args.interval)
    while True:
        try:
            pipeline.run_once(auto=auto)
        except Exception:
            log.exception("Run failed; retrying next interval")
        time.sleep(args.interval)


if __name__ == "__main__":
    sys.exit(main())

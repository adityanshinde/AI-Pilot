from __future__ import annotations

import argparse
import logging

from db.init_db import init_db
from pipelines.autopilot_pipeline import AutopilotContentPipeline
from utils import get_settings, setup_logging


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Autopilot Content Engine")
    parser.add_argument(
        "command",
        choices=["init_db", "run_once"],
        nargs="?",
        default="run_once",
        help="Command to execute",
    )
    parser.add_argument("--no-init-db", action="store_true", help="Skip DB init on run_once")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    settings = get_settings()
    setup_logging(settings.log_level)

    if args.command == "init_db":
        init_db()
        logging.getLogger(__name__).info("Database initialized")
        return

    pipeline = AutopilotContentPipeline(settings=settings)
    pipeline.run_once(ensure_db=not args.no_init_db)


if __name__ == "__main__":
    main()

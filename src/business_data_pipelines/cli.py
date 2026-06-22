from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path
from typing import Tuple


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bdp")
    parser.add_argument("--env", default=".env", help="Path to environment file")
    subparsers = parser.add_subparsers(dest="platform", required=True)

    qnh = subparsers.add_parser("qnh")
    qnh_subparsers = qnh.add_subparsers(dest="pipeline", required=True)

    activity = qnh_subparsers.add_parser("activity-detail")
    activity.add_argument("--dimension", choices=["activity", "store"], required=True)
    activity.add_argument("--date", help="Single business date. Defaults to yesterday when omitted.")
    activity.add_argument("--start", help="Start business date for backfill.")
    activity.add_argument("--end", help="End business date for backfill.")
    activity.add_argument("--config", required=True)

    review = qnh_subparsers.add_parser("review-detail")
    review.add_argument("--start", help="Start review date. Defaults to the platform default window.")
    review.add_argument("--end", help="End review date. Defaults to the platform default window.")
    review.add_argument("--config", required=True)

    return parser


def resolve_date_range(args: argparse.Namespace, parser: argparse.ArgumentParser) -> Tuple[str, str]:
    if args.date and (args.start or args.end):
        parser.error("Use either --date or --start/--end, not both.")
    if args.date:
        return args.date, args.date
    if args.start or args.end:
        if not args.start or not args.end:
            parser.error("--start and --end must be used together.")
        return args.start, args.end
    yesterday = date.today() - timedelta(days=1)
    value = yesterday.isoformat()
    return value, value


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.platform == "qnh" and args.pipeline == "activity-detail":
        from business_data_pipelines.core.config import RuntimeSettings
        from business_data_pipelines.pipelines.qnh.activity_detail.pipeline import run_activity_detail

        settings = RuntimeSettings.load(Path(args.config), env_path=Path(args.env))
        start, end = resolve_date_range(args, parser)
        run_activity_detail(settings, args.dimension, start, end)
        return
    if args.platform == "qnh" and args.pipeline == "review-detail":
        from business_data_pipelines.core.config import RuntimeSettings
        from business_data_pipelines.pipelines.qnh.review_detail.pipeline import run_review_detail

        if bool(args.start) != bool(args.end):
            parser.error("--start and --end must be used together.")
        settings = RuntimeSettings.load(Path(args.config), env_path=Path(args.env))
        run_review_detail(settings, start=args.start, end=args.end)
        return
    parser.error("Unsupported command")


if __name__ == "__main__":
    main()

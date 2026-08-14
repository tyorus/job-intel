"""CLI entrypoint for Job Intelligence."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from jobintel import __version__
from jobintel.career.profile import CareerProfileError, validate_career_profile
from jobintel.collectors.run import ALL_SOURCES, collect_jobs, scrape_to_store
from jobintel.config import get_settings
from jobintel.db import get_store


def _cmd_career_validate(args: argparse.Namespace) -> int:
    career_dir = Path(args.career_dir) if args.career_dir else get_settings().career_data_dir
    try:
        profile = validate_career_profile(career_dir)
    except CareerProfileError as exc:
        print(f"Career validation failed: {exc}", file=sys.stderr)
        return 1

    print(f"OK: career profile valid ({career_dir})")
    print(f"  name:         {profile.profile.full_name}")
    print(f"  skills:       {len(profile.skills)}")
    print(f"  experiences:  {len(profile.experiences)}")
    print(f"  projects:     {len(profile.projects)}")
    print(f"  education:    {len(profile.education)}")
    print(f"  achievements: {len(profile.achievements)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="jobintel",
        description="Personal Job Intelligence & Resume Tailoring CLI",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command")

    career = sub.add_parser("career", help="Career profile commands")
    career_sub = career.add_subparsers(dest="career_command")

    validate = career_sub.add_parser("validate", help="Validate career_data YAML files")
    validate.add_argument(
        "--career-dir",
        type=str,
        default=None,
        help="Path to career_data directory (default: CAREER_DATA_DIR / career_data)",
    )
    validate.set_defaults(func=_cmd_career_validate)

    scrape = sub.add_parser(
        "scrape",
        help="Fetch public job boards and insert new remote-matching jobs",
    )
    scrape.add_argument(
        "--source",
        action="append",
        dest="sources",
        choices=list(ALL_SOURCES),
        help="Collector to run (repeatable). Default: all public sources.",
    )
    scrape.add_argument(
        "--dry-run",
        action="store_true",
        help="Print matched jobs without writing to Supabase",
    )
    scrape.set_defaults(func=_cmd_scrape)

    return parser


def _cmd_scrape(args: argparse.Namespace) -> int:
    sources = args.sources or list(ALL_SOURCES)
    if args.dry_run:
        jobs = collect_jobs(sources=sources)
        print(json.dumps({"matched": len(jobs), "sources": sources}, indent=2))
        for job in jobs[:20]:
            print(f"  [{job.source}] {job.company_name} — {job.title}")
        if len(jobs) > 20:
            print(f"  … {len(jobs) - 20} more")
        return 0
    result = scrape_to_store(get_store(), sources=sources)
    print(json.dumps(result, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return 0
    if args.command == "career" and not getattr(args, "career_command", None):
        parser.parse_args(["career", "--help"])
        return 0
    func = getattr(args, "func", None)
    if func is None:
        parser.print_help()
        return 0
    return int(func(args))


if __name__ == "__main__":
    raise SystemExit(main())

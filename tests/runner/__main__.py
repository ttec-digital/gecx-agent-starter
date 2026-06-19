"""CLI entry point: `python -m runner ...`

Examples:
  python -m runner --cases tests/cases --transport mock
  python -m runner --transport unary --case smoke-greeting
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .cases import load_cases
from .config import REPO_ROOT, load_config
from .report import print_report
from .session import run_case
from .transports import get_transport


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="GECX agent RPC test harness")
    parser.add_argument(
        "--cases",
        default=str(REPO_ROOT / "tests" / "cases"),
        help="Directory of *.yaml test cases (default: tests/cases).",
    )
    parser.add_argument("--case", help="Run only the case with this name.")
    parser.add_argument(
        "--transport",
        choices=["mock", "unary", "stream"],
        help="Override transport for all cases (default: per-case, else config).",
    )
    parser.add_argument("--config", help="Path to config json (default: config/config.json).")
    args = parser.parse_args(argv)

    config = load_config(Path(args.config) if args.config else None)
    cases = load_cases(Path(args.cases), only=args.case)
    if not cases:
        print("No cases found.")
        return 1

    default_transport = config.testing.transport
    reports = []
    for case in cases:
        transport_name = args.transport or case.transport or default_transport
        reports.append(
            run_case(
                case,
                lambda name=transport_name: get_transport(name, config),
                transport_name,
                config.app_path,
            )
        )

    return print_report(reports)


if __name__ == "__main__":
    sys.exit(main())

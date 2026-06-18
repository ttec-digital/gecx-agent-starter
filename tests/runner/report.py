"""Console reporting + process exit code for the harness."""
from __future__ import annotations

from .session import CaseReport

GREEN, RED, DIM, RESET = "\033[32m", "\033[31m", "\033[2m", "\033[0m"


def print_report(reports: list[CaseReport]) -> int:
    """Print a per-case summary; return a process exit code (0 = all passed)."""
    passed = 0
    for cr in reports:
        mark = f"{GREEN}PASS{RESET}" if cr.passed else f"{RED}FAIL{RESET}"
        print(f"\n[{mark}] {cr.name}  ({cr.transport})")
        if cr.error:
            print(f"  {RED}error:{RESET} {cr.error}")
        for i, turn in enumerate(cr.turns, 1):
            print(f"  {DIM}turn {i}{RESET}  user: {turn.user!r}")
            print(f"          reply: {turn.reply!r}  {DIM}({turn.latency_ms:.0f}ms){RESET}")
            for o in turn.outcomes:
                omark = f"{GREEN}ok{RESET}" if o.passed else f"{RED}xx{RESET}"
                print(f"            [{omark}] {o.key}: {o.detail}")
        if cr.passed:
            passed += 1

    total = len(reports)
    summary_color = GREEN if passed == total else RED
    print(f"\n{summary_color}{passed}/{total} cases passed{RESET}")
    return 0 if passed == total else 1

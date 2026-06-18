"""Per-case orchestration: open a session, play turns, evaluate assertions.

Transport-agnostic — works identically over mock/unary/bidi.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from . import assertions
from .cases import Case
from .transports import Transport
from .transports.base import TurnResult


@dataclass
class TurnReport:
    user: str
    reply: str
    latency_ms: float
    outcomes: list[assertions.AssertionOutcome] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(o.passed for o in self.outcomes)


@dataclass
class CaseReport:
    name: str
    transport: str
    turns: list[TurnReport] = field(default_factory=list)
    error: str | None = None

    @property
    def passed(self) -> bool:
        return self.error is None and all(t.passed for t in self.turns)


def run_case(
    case: Case,
    transport_factory: Callable[[], Transport],
    transport_name: str,
    app_path: str,
) -> CaseReport:
    report = CaseReport(name=case.name, transport=transport_name)
    transport: Transport | None = None
    try:
        # Construct inside the try so a not-yet-wired transport (NotImplementedError) is
        # reported as a clean failed case rather than crashing the whole run.
        transport = transport_factory()
        transport.open_session(app_path, case.variables)
        for turn in case.turns:
            result: TurnResult = transport.send_turn(turn.user)
            outcomes = assertions.evaluate(turn.expect, result)
            report.turns.append(
                TurnReport(
                    user=turn.user,
                    reply=result.reply_text,
                    latency_ms=result.latency_ms,
                    outcomes=outcomes,
                )
            )

        # End-of-conversation assertions evaluate against the last turn's result.
        if case.final_expect and report.turns:
            last = report.turns[-1]
            final_result = TurnResult(reply_text=last.reply, latency_ms=last.latency_ms)
            last.outcomes.extend(assertions.evaluate(case.final_expect, final_result))
    except Exception as exc:  # surface transport/setup failures as a failed case
        report.error = f"{type(exc).__name__}: {exc}"
    finally:
        if transport is not None:
            try:
                transport.close()
            except Exception:
                pass
    return report

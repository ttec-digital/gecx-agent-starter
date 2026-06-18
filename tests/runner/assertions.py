"""Assertion evaluators.

Each assertion in a case's `expect:` list is a single-key dict, e.g. {"contains": "shipped"}.
Evaluators are registered by key, so adding a new assertion type is a one-function change
(modularity per ADR-001). Each returns (passed: bool, detail: str).
"""
from __future__ import annotations

import re
from typing import Any, Callable

from .transports.base import TurnResult

Evaluator = Callable[[Any, TurnResult], "AssertionOutcome"]
_REGISTRY: dict[str, Evaluator] = {}


class AssertionOutcome:
    def __init__(self, key: str, passed: bool, detail: str) -> None:
        self.key = key
        self.passed = passed
        self.detail = detail


def register(key: str):
    def deco(fn: Evaluator) -> Evaluator:
        _REGISTRY[key] = fn
        return fn

    return deco


def evaluate(expect: list[dict[str, Any]], result: TurnResult) -> list[AssertionOutcome]:
    outcomes: list[AssertionOutcome] = []
    for clause in expect:
        for key, expected in clause.items():
            evaluator = _REGISTRY.get(key)
            if evaluator is None:
                outcomes.append(
                    AssertionOutcome(key, False, f"unknown assertion type {key!r}")
                )
                continue
            outcomes.append(evaluator(expected, result))
    return outcomes


# --- text assertions -------------------------------------------------------- #
@register("contains")
def _contains(expected: str, r: TurnResult) -> AssertionOutcome:
    ok = str(expected).lower() in r.reply_text.lower()
    return AssertionOutcome("contains", ok, f"expected substring {expected!r} in reply")


@register("not_contains")
def _not_contains(expected: str, r: TurnResult) -> AssertionOutcome:
    ok = str(expected).lower() not in r.reply_text.lower()
    return AssertionOutcome("not_contains", ok, f"reply must not contain {expected!r}")


@register("regex")
def _regex(pattern: str, r: TurnResult) -> AssertionOutcome:
    ok = re.search(pattern, r.reply_text, re.IGNORECASE) is not None
    return AssertionOutcome("regex", ok, f"reply must match /{pattern}/i")


@register("equals")
def _equals(expected: str, r: TurnResult) -> AssertionOutcome:
    ok = r.reply_text.strip() == str(expected).strip()
    return AssertionOutcome("equals", ok, f"reply must equal {expected!r}")


# --- performance ------------------------------------------------------------ #
@register("latency_ms_max")
def _latency(budget: int, r: TurnResult) -> AssertionOutcome:
    ok = r.latency_ms <= float(budget)
    return AssertionOutcome(
        "latency_ms_max", ok, f"latency {r.latency_ms:.0f}ms <= {budget}ms"
    )


# --- behavior signals (active once SessionOutput parsing is confirmed) ------ #
@register("tool_called")
def _tool_called(name: str, r: TurnResult) -> AssertionOutcome:
    ok = name in r.tools_called
    return AssertionOutcome("tool_called", ok, f"tool {name!r} should have been called")


@register("transferred_to")
def _transferred_to(name: str, r: TurnResult) -> AssertionOutcome:
    ok = r.transferred_to == name
    return AssertionOutcome("transferred_to", ok, f"should transfer to {name!r}")


@register("escalated")
def _escalated(expected: bool, r: TurnResult) -> AssertionOutcome:
    actual = r.transferred_to is not None
    ok = actual == bool(expected)
    return AssertionOutcome("escalated", ok, f"escalated should be {expected}")


@register("no_validation_errors")
def _no_validation_errors(expected: bool, r: TurnResult) -> AssertionOutcome:
    ok = (len(r.validation_errors) == 0) == bool(expected)
    return AssertionOutcome(
        "no_validation_errors", ok, f"validation errors: {r.validation_errors or 'none'}"
    )

"""CES conversations — pull the server-side trace for one call and render a per-call report.

CES keeps a full per-conversation trace under the app — the source of truth for what the live
agent actually did (tool calls/responses, guardrail decisions, spans) for a past call. This module
lists conversations and renders one into a readable report: overview, transcript interleaved with
tool calls/responses, guardrail decisions, and outcome. Target project/location/app/auth come from
`config/config.json` via `runner.config`; auth via `runner.auth`. Stdlib only (urllib) — no extra deps.

CLI (run from the `tests/` dir, like the harness):
    python -m runner.conversations list [--limit N] [--json]
    python -m runner.conversations get <id>              # raw JSON
    python -m runner.conversations report <id> [--out FILE]

`<id>` is the conversation id — the last path segment of the resource name, e.g. a `test-…`
session id the harness mints, a `bidi-…`/`simulator-…` id, or a bare UUID.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Iterator

from .auth import get_access_token
from .config import Config, load_config


class ConversationsClient:
    """Thin CES conversations reader driven by config/config.json."""

    def __init__(self, config: Config | None = None) -> None:
        self.config = config or load_config()
        self._token: str | None = None

    def _headers(self) -> dict[str, str]:
        if self._token is None:
            self._token = get_access_token(self.config.auth_account or None)
        return {
            "Authorization": f"Bearer {self._token}",
            "x-goog-user-project": self.config.project_id,
        }

    def _base(self) -> str:
        c = self.config
        return f"{c.endpoint}/{c.api_version}/{c.app_path}/conversations"

    def _get(self, url: str) -> dict[str, Any]:
        req = urllib.request.Request(url, method="GET", headers=self._headers())
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")
            raise RuntimeError(f"conversations HTTP {exc.code}: {detail}") from exc

    def list(self, limit: int | None = None) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        token: str | None = None
        while True:
            url = self._base()
            if token:
                url += f"?pageToken={urllib.parse.quote(token)}"
            resp = self._get(url)
            items.extend(resp.get("conversations", []) or [])
            token = resp.get("nextPageToken")
            if not token or (limit and len(items) >= limit):
                break
        return items[:limit] if limit else items

    def get(self, conv_id: str) -> dict[str, Any]:
        cid = conv_id.strip().split("/")[-1]
        return self._get(f"{self._base()}/{urllib.parse.quote(cid)}")


# --------------------------------------------------------------------------- #
# report rendering
# --------------------------------------------------------------------------- #
def _short(name: str | None) -> str:
    return (name or "").split("/")[-1]


def _compact(obj: Any, maxlen: int = 200) -> str:
    s = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    return s if len(s) <= maxlen else s[: maxlen - 1] + "…"


def _iter_spans(span: dict[str, Any]) -> Iterator[dict[str, Any]]:
    for child in span.get("childSpans", []) or []:
        yield child
        yield from _iter_spans(child)


def format_report(conv: dict[str, Any]) -> str:
    turns = conv.get("turns", []) or []
    out: list[str] = []
    out.append(f"# Call report: {_short(conv.get('name'))}")
    out.append("")

    # ---- overview -------------------------------------------------------- #
    latencies: list[Any] = []
    served: set[str] = set()
    seed_vars: dict[str, Any] = {}
    all_vars: dict[str, Any] = {}
    for t in turns:
        rs = t.get("rootSpan") or {}
        attrs = rs.get("attributes") or {}
        if attrs.get("perceived latency (ms)") is not None:
            latencies.append(attrs["perceived latency (ms)"])
        for s in _iter_spans(rs):
            a = s.get("attributes") or {}
            for k in ("version id", "deployment id"):
                if a.get(k):
                    served.add(f"{k}={_short(str(a[k]))}")
        for m in t.get("messages", []):
            for ch in m.get("chunks", []):
                if "defaultVariables" in ch and not seed_vars:
                    seed_vars = ch.get("defaultVariables") or {}
                if ch.get("updatedVariables"):
                    all_vars.update(ch["updatedVariables"])

    out.append("## Overview")
    out.append(f"- Started: {conv.get('startTime', '?')} | Ended: {conv.get('endTime', '?')}")
    out.append(
        f"- Channel: {conv.get('channelType', '?')} | Source: {conv.get('source', '?')} | "
        f"Language: {conv.get('languageCode', '?')}"
    )
    out.append(
        f"- Entry agent: `{_short(conv.get('entryAgent'))}` | "
        f"Turns: {conv.get('turnCount', len(turns))}"
    )
    if latencies:
        out.append(f"- Perceived latency: {', '.join(str(x) for x in latencies)} ms")
    out.append(f"- Served: {', '.join(sorted(served)) if served else 'no deployment (Preview/runSession)'}")
    if seed_vars:
        out.append(f"- Seed variables: {_compact(seed_vars, 240)}")
    out.append("")

    # ---- transcript & actions ------------------------------------------- #
    out.append("## Transcript & actions")
    for t in turns:
        for m in t.get("messages", []):
            role = m.get("role", "?")
            is_user = role == "user"
            for ch in m.get("chunks", []):
                if ch.get("text"):
                    who = "USER" if is_user else f"AGENT [{role}]"
                    out.append(f"- **{who}:** {ch['text']}")
                elif ch.get("transcript"):
                    out.append(f"- **USER (speech):** {ch['transcript']}")
                elif "toolCall" in ch:
                    tc = ch["toolCall"] or {}
                    out.append(f"    - call `{tc.get('displayName', '?')}`({_compact(tc.get('args', {}), 140)})")
                elif "toolResponse" in ch:
                    tr = ch["toolResponse"] or {}
                    out.append(f"    - -> `{tr.get('displayName', '?')}` => {_compact(tr.get('response', {}), 180)}")
                elif "agentTransfer" in ch:
                    out.append("    - => *agent transfer*")
                elif ch.get("updatedVariables"):
                    out.append(f"    - vars: {_compact(ch['updatedVariables'], 140)}")
    out.append("")

    # ---- guardrails (dedup by name, prefer the triggered evaluation) ----- #
    gr: dict[str, tuple[bool, str]] = {}
    for t in turns:
        for s in _iter_spans(t.get("rootSpan") or {}):
            if s.get("name") == "Guardrail":
                a = s.get("attributes") or {}
                nm = a.get("name", "?")
                trig = bool(a.get("triggered"))
                cur = gr.get(nm)
                if cur is None or (trig and not cur[0]):
                    gr[nm] = (trig, a.get("reason", "") or "")
    if gr:
        out.append("## Guardrails")
        for nm in sorted(gr, key=lambda k: (not gr[k][0], k)):
            trig, reason = gr[nm]
            mark = "**TRIGGERED**" if trig else "ok"
            tail = f" - {reason}" if (trig and reason) else ""
            out.append(f"- {mark}: `{nm}`{tail}")
        out.append("")

    # ---- outcome --------------------------------------------------------- #
    final_line = ""
    for t in turns:
        for m in t.get("messages", []):
            if m.get("role") != "user":
                for ch in m.get("chunks", []):
                    if ch.get("text"):
                        final_line = ch["text"]
    out.append("## Outcome")
    if final_line:
        out.append(f"- Final agent line: {final_line}")
    if all_vars:
        out.append(f"- Final session variables: {_compact(all_vars, 400)}")
    out.append("")
    return "\n".join(out)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _cli(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="CES conversation logs — list / get / per-call report")
    sub = p.add_subparsers(dest="cmd", required=True)

    pl = sub.add_parser("list", help="recent conversations, newest first")
    pl.add_argument("--limit", type=int, help="max rows")
    pl.add_argument("--json", action="store_true", help="raw JSON instead of a table")

    pg = sub.add_parser("get", help="raw conversation JSON for one id")
    pg.add_argument("id")

    pr = sub.add_parser("report", help="rendered per-call report for one id")
    pr.add_argument("id")
    pr.add_argument("--out", help="write the markdown report to this file")

    args = p.parse_args(argv)
    # Windows console defaults to cp1252; force UTF-8 so call content (£, curly quotes, etc.)
    # never crashes on print. File output (--out) is already written as UTF-8.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    client = ConversationsClient()

    if args.cmd == "list":
        items = client.list(limit=args.limit)
        if args.json:
            print(json.dumps(items, indent=2))
        else:
            for c in items:
                print(
                    f"{_short(c.get('name')):40}  {c.get('startTime', '?'):27}  "
                    f"turns={str(c.get('turnCount', '?')):<3}  {_short(c.get('entryAgent'))}"
                )
            print(f"\n{len(items)} conversation(s)")
        return 0

    if args.cmd == "get":
        print(json.dumps(client.get(args.id), indent=2))
        return 0

    if args.cmd == "report":
        md = format_report(client.get(args.id))
        if args.out:
            Path(args.out).write_text(md, encoding="utf-8")
            print(f"wrote {args.out}")
        else:
            print(md)
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(_cli())

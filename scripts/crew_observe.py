#!/usr/bin/env python3
"""Post-delivery regression observer: re-run a delivered crew card's owner-confirmed proof and say whether it
still holds (OpenSpec stewardship-core-adoption, CREW-INV-7).

One seam, no second database:

    observe_delivered(db_path=None, state_path=None, card_id=None, window_days=14, timeout_s=60,
                      dry_run=False, clock=None) -> {"eligible", "results", "skipped", ...}

Eligible: a `done` crew card with a terminal `completed` run in task_runs, an owner-confirmed proof snapshot
(crew_card.proof_snapshot - never the editable `proof command:` body line), no `Observe: off` line, and either
completed within `window_days` of `clock()`, an `Observe: always` line, or named by `card_id`.

Each proof runs through crew_proc.run_bounded (empty stdin, 64 KiB head+tail streams, monotonic timeout,
CREW_RUN_MARKER sweep) after Hermes's safety floors (crew_safety). exit 0 -> `improved`; non-zero or timeout ->
`regressed`; a proof the floors refuse -> `unknown` (nothing ran). The outcome is written to
<HERMES_HOME>/crew/observations.json and as a `crew_observation` task event on the card. A card that turns
`regressed` gets one alert through crew_notify (key `regressed:<card>:<event id>`); the card is never reopened.

  python crew_observe.py [<card id>] [--window-days N] [--timeout S] [--dry-run] [--db PATH] [--state PATH]
"""
import argparse
import json
import os
import sqlite3
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import crew_card  # noqa: E402
import crew_notify  # noqa: E402
import crew_proc  # noqa: E402

EVENT_KIND = "crew_observation"
IMPROVED, REGRESSED, UNKNOWN = "improved", "regressed", "unknown"
OUTPUT_KEEP = 2000          # characters of proof output kept in the state/event (the tail: where failures print)


class Blocked:
    """A runner's answer for a proof the safety floors refused: nothing ran."""

    def __init__(self, reason=""):
        self.reason = str(reason or "refused by the safety floor")


BLOCKED = Blocked()


def state_file():
    return os.path.join(crew_card.base_home(), "crew", "observations.json")


def _load_state(path):
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict) and isinstance(data.get("cards"), dict):
            return data
    except (OSError, ValueError):
        pass
    return {"version": 1, "cards": {}}


def _save_state(path, state):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=1, sort_keys=True)
    os.replace(tmp, path)


def _observe_mode(body):
    return (crew_card.field(body or "", "Observe") or "").strip().lower()


def _default_runner(cmd, *, cwd=None, timeout_s=60.0, card_id=None, db=None):
    """The proof through Hermes's floors and the card's script binding, then crew_proc.run_bounded in the shell a
    crew proof runs in (Git Bash on Windows, or PowerShell for a bare cmdlet; /bin/sh on POSIX)."""
    import crew_safety
    mode = crew_safety.proof_mode(card_id, cmd) if card_id else "safe"
    ok, why = crew_safety._floors(cmd, mode)
    if ok and card_id:
        why = crew_safety.script_change(card_id, cmd, record=False)
        ok = not why
    if not ok:
        return Blocked(why)
    if crew_safety.IS_WINDOWS and crew_safety.detect_bare_powershell(cmd):
        argv = [crew_safety._powershell(), "-NoProfile", "-NonInteractive", "-Command", crew_safety._PS_WRAPPER % cmd]
    elif crew_safety.IS_WINDOWS:
        bash = crew_safety.git_bash()
        if not bash:
            return Blocked("Git Bash was not found: crew proofs run in Git Bash on Windows")
        argv = [bash, "-c", cmd]
    else:
        argv = ["/bin/sh", "-c", cmd]
    with crew_safety.proof_cmd_scope(cmd):
        return crew_proc.run_bounded(argv, timeout_s=timeout_s, cwd=cwd, env=crew_safety.proof_env())


def _eligible(conn, db, now, window_days, card_id):
    """([task rows to observe], {card: why skipped})."""
    cutoff = now - window_days * 86400
    sql = ("select t.* from tasks t where t.status='done' and exists (select 1 from task_runs r "
           "where r.task_id=t.id and r.outcome='completed')")
    args = ()
    if card_id:
        sql += " and t.id=?"
        args = (card_id,)
    rows, skipped = [], {}
    for task in conn.execute(sql + " order by t.completed_at", args):
        mode = _observe_mode(task["body"])
        if not card_id and mode != "always" and (task["completed_at"] or 0) < cutoff:
            continue                    # outside the window: silent, or a nightly pass lists every old card
        if mode == "off":
            skipped[task["id"]] = "Observe: off"
            continue
        if not crew_card.proof_snapshot(task["id"], db):
            skipped[task["id"]] = "no owner-confirmed proof command"
            continue
        rows.append(task)
    if card_id and not rows and card_id not in skipped:
        skipped[card_id] = "not a done card with a completed run"
    return rows, skipped


def _tail(text, n=OUTPUT_KEEP):
    text = str(text or "")
    return text if len(text) <= n else "..." + text[-n:]


def _classify(result):
    if isinstance(result, Blocked):
        return UNKNOWN
    if getattr(result, "timed_out", False) or getattr(result, "exit_code", 1) != 0:
        return REGRESSED
    return IMPROVED


def _append_event(db, card_id, payload):
    """crew_card's one audit writer, then the new row's id (the dedupe key of a regression alert)."""
    if not crew_card._append_card_event(card_id, EVENT_KIND, payload, db=db):
        return 0
    conn = sqlite3.connect(db, timeout=10)
    try:
        row = conn.execute("select max(id) from task_events where task_id=? and kind=?", (card_id, EVENT_KIND)).fetchone()
    finally:
        conn.close()
    return int(row[0] or 0)


def observe_delivered(*, db_path=None, state_path=None, card_id=None, window_days=14, timeout_s=60.0,
                      dry_run=False, clock=None, runner=None, send=None, notify_state_path=None):
    """One observation pass. `runner(cmd, cwd=, timeout_s=, card_id=, db=)` and `send(target, text)` replace the real
    proof run and the real `hermes send` (tests); `clock` replaces time.time."""
    now = float((clock or time.time)())
    db = db_path or crew_card.kanban_db()
    out = {"eligible": [], "results": {}, "skipped": {}, "alerts": [], "dry_run": bool(dry_run), "at": now}
    if not db or not os.path.exists(db):
        out["error"] = "no board"
        return out
    runner = runner or _default_runner
    state_path = state_path or state_file()
    conn = sqlite3.connect("file:%s?mode=ro" % db, uri=True, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        rows, out["skipped"] = _eligible(conn, db, now, int(window_days), card_id)
        tasks = [dict(r) for r in rows]
    finally:
        conn.close()
    out["eligible"] = [t["id"] for t in tasks]
    if dry_run:
        return out
    state = _load_state(state_path)
    cards = state["cards"]
    for task in tasks:
        tid = task["id"]
        cmd = crew_card.proof_snapshot(tid, db)
        result = runner(cmd, cwd=crew_card.proof_cwd(task["body"]), timeout_s=timeout_s, card_id=tid, db=db)
        status = _classify(result)
        prev = cards.get(tid) or {}
        obs = {
            "status": status,
            "previous": prev.get("status") or "",
            "observed_at": now,
            "proof_cmd": cmd,
            "exit_code": getattr(result, "exit_code", None),
            "timed_out": bool(getattr(result, "timed_out", False)),
            "duration_s": round(float(getattr(result, "duration_s", 0.0) or 0.0), 3),
        }
        if isinstance(result, Blocked):
            obs["blocked"] = result.reason
        else:
            obs["output"] = _tail((result.stdout or "") + (("\n" + result.stderr) if result.stderr else ""))
        event_id = _append_event(db, tid, {k: v for k, v in obs.items() if k != "output"}
                                 | {"output_tail": _tail(obs.get("output", ""), 600), "by": "crew_observe"})
        obs["event_id"] = event_id
        if status == REGRESSED:
            # The alert belongs to the transition into `regressed`; a card that stays regressed keeps that key.
            key = prev.get("regression_key") if prev.get("status") in (REGRESSED, UNKNOWN) else ""
            obs["regression_key"] = key or "regressed:%s:%d" % (tid, event_id)
            sent = crew_notify.notify_regression(db, task, obs, obs["regression_key"], state_path=notify_state_path,
                                                 send=send)
            if sent.get("sent"):
                out["alerts"].append(obs["regression_key"])
            obs["alert"] = sent
        elif status == UNKNOWN and prev.get("status") == REGRESSED:
            # nothing ran: keep the open regression's key so a later failing run does not alert twice
            obs["regression_key"] = prev.get("regression_key") or ""
        cards[tid] = obs
        out["results"][tid] = {k: obs[k] for k in ("status", "previous", "exit_code", "timed_out", "event_id")}
    state["updated_at"] = now
    _save_state(state_path, state)
    return out


def summary_lines(res):
    lines = []
    for tid, r in res.get("results", {}).items():
        lines.append("%s %s (exit %s%s)" % (r["status"].upper(), tid, r.get("exit_code"),
                                            ", timed out" if r.get("timed_out") else ""))
    for tid, why in res.get("skipped", {}).items():
        lines.append("SKIP %s: %s" % (tid, why))
    counts = {s: sum(1 for r in res.get("results", {}).values() if r["status"] == s) for s in (IMPROVED, REGRESSED, UNKNOWN)}
    lines.append("[RESULT] observed=%d improved=%d regressed=%d unknown=%d alerts=%d%s"
                 % (len(res.get("results", {})), counts[IMPROVED], counts[REGRESSED], counts[UNKNOWN],
                    len(res.get("alerts", [])), " dry_run eligible=%d" % len(res.get("eligible", [])) if res.get("dry_run") else ""))
    return lines


def main(argv=None):
    ap = argparse.ArgumentParser(description="re-run delivered crew cards' proofs and alert on regressions")
    ap.add_argument("card", nargs="?", default=None, help="one card id (default: every eligible done card)")
    ap.add_argument("--window-days", type=int, default=14)
    ap.add_argument("--timeout", type=float, default=60.0, help="seconds per proof")
    ap.add_argument("--dry-run", action="store_true", help="list eligible cards; run, record and send nothing")
    ap.add_argument("--db", default=None)
    ap.add_argument("--state", default=None)
    a = ap.parse_args(argv)
    if a.card and not crew_card.contracts.is_valid_card_id(a.card):
        print("error: not a card id: %s" % a.card)
        return 2
    res = observe_delivered(db_path=a.db, state_path=a.state, card_id=a.card, window_days=a.window_days,
                            timeout_s=a.timeout, dry_run=a.dry_run)
    if res.get("error"):
        print("error: %s" % res["error"])
        return 2
    print("\n".join(summary_lines(res)))
    return 0


if __name__ == "__main__":
    crew_proc.utf8_stdio()
    sys.exit(main())

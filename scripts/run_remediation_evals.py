"""Remediation live execution runner for Crew skills evaluation.
Runs live E2E scenarios for crew-verifier and crew-role-content on isolated fixtures,
extracting real tool calls, parameters, and terminal states directly from state.db.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sqlite3
import subprocess
import time
from typing import Any, Dict, List, Optional

STATE_DB_PATH = "O:/workspaces/_config/agent4070/hermes/state.db"
HERMES_BIN = r"O:/workspaces/oss/hermes-agent/venv/Scripts/hermes.exe"
CREW_CARD_PY = r"O:/workspaces/oss/crew/scripts/crew_card.py"


def open_crew_card(title: str, goal: str, role: str, artifact: str, proof_cmd: str, verify: str, assignee: str) -> str:
    env = dict(os.environ)
    env.pop("HERMES_DELEGATED_CHILD_CONTEXT", None)
    cmd = [
        "python", CREW_CARD_PY, "open",
        "--title", title,
        "--goal", goal,
        "--role", role,
        "--artifact", artifact,
        "--lands", "O:/workspaces/oss/crew",
        "--audience", "Commander",
        "--done-when", f"{artifact} exists and is verified",
        "--proof-cmd", proof_cmd,
        "--assignee", assignee,
        "--verify", verify,
        "--json"
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if res.returncode != 0:
        raise RuntimeError(f"Failed to open card: {res.stderr or res.stdout}")
    data = json.loads(res.stdout)
    return data["id"]


def run_subagent_prompt(skill: str, prompt: str, timeout: int = 300) -> Dict[str, Any]:
    env = dict(os.environ)
    env.pop("HERMES_DELEGATED_CHILD_CONTEXT", None)
    env.pop("HERMES_KANBAN_TASK", None)
    env.pop("HERMES_KANBAN_TASK_ID", None)

    cmd = [HERMES_BIN, "-p", "default", "-s", skill, "-z", prompt]
    t0 = time.time()
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
    t1 = time.time()
    return {
        "skill": skill,
        "prompt": prompt,
        "rc": p.returncode,
        "duration": t1 - t0,
        "start_time": t0,
        "end_time": t1,
        "stdout": p.stdout,
        "stderr": p.stderr,
    }


def extract_session_from_db(start_time: float, end_time: float, prompt_snippet: str) -> Optional[Dict[str, Any]]:
    conn = sqlite3.connect(STATE_DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT session_id, role, content, tool_name, tool_calls, timestamp
        FROM messages
        WHERE timestamp >= ? AND timestamp <= ?
        ORDER BY timestamp ASC
        """,
        (start_time - 10, end_time + 10),
    )
    rows = cur.fetchall()
    conn.close()

    sessions: Dict[str, List[Any]] = {}
    for r in rows:
        sid = r[0]
        if sid not in sessions:
            sessions[sid] = []
        sessions[sid].append(r)

    for sid, msgs in sessions.items():
        for m in msgs:
            if m[1] == "user" and prompt_snippet[:30] in (m[2] or ""):
                return {"session_id": sid, "messages": msgs}
    return None


def parse_tool_telemetry(session_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not session_data:
        return {"tool_calls": [], "tool_names": [], "tool_results": []}

    tool_calls = []
    tool_names = []
    tool_results = []
    for m in session_data["messages"]:
        role = m[1]
        content = m[2]
        tool_name = m[3]
        tc_json = m[4]
        if role == "assistant" and tc_json:
            try:
                calls = json.loads(tc_json)
                for tc in calls:
                    fn = tc.get("function", {})
                    fn_name = fn.get("name")
                    fn_args = fn.get("arguments")
                    if fn_name == "tool_call":
                        inner = json.loads(fn_args)
                        for ic in inner.get("calls", []):
                            tool_calls.append(ic)
                            tool_names.append(ic.get("name"))
                    else:
                        tool_calls.append({"name": fn_name, "arguments": fn_args})
                        tool_names.append(fn_name)
            except Exception:
                pass
        elif role == "tool":
            tool_results.append({"name": tool_name, "content": content})
    return {"tool_calls": tool_calls, "tool_names": tool_names, "tool_results": tool_results}


def main():
    print("=== STARTING REMEDIATION EVALUATION SUITE ===")
    
    # 1. Verifier live scenario
    print("[*] Opening fixture card for crew-verifier...")
    verifier_card = open_crew_card(
        title="[fixture-eval] Verifier live test fixture",
        goal="Audit and verify worker deliverable in tests/fixtures/eval/worker_helper.py and record review findings",
        role="verifier",
        artifact="reviews/findings-eval-fixture.md",
        proof_cmd="python -c \"import os; assert os.path.exists('reviews/findings-eval-fixture.md') and os.path.getsize('reviews/findings-eval-fixture.md') > 0\"",
        verify="agent",
        assignee="reviewer"
    )
    print(f"[+] Verifier card opened: {verifier_card}")
    
    prompt_verifier = f'Use the "crew-verifier" skill. You are assigned as verifier on card {verifier_card} with Verify: agent. Audit and verify the card.'
    print(f"[*] Running subagent for {verifier_card}...")
    run_verifier = run_subagent_prompt("crew-verifier", prompt_verifier, timeout=300)
    sess_verifier = extract_session_from_db(run_verifier["start_time"], run_verifier["end_time"], prompt_verifier)
    telemetry_verifier = parse_tool_telemetry(sess_verifier)
    print(f"[+] Verifier finished: session={sess_verifier['session_id'] if sess_verifier else 'None'}, tools={telemetry_verifier['tool_names']}")

    # 2. Content creator live scenario
    print("[*] Opening fixture card for crew-role-content...")
    content_card = open_crew_card(
        title="[fixture-eval] Content live test fixture",
        goal="Author telemetry overview document in reports/telemetry-eval-fixture.md with verified statistics",
        role="content",
        artifact="reports/telemetry-eval-fixture.md",
        proof_cmd="python -c \"import os; assert os.path.exists('reports/telemetry-eval-fixture.md') and os.path.getsize('reports/telemetry-eval-fixture.md') > 0\"",
        verify="dual",
        assignee="coder"
    )
    print(f"[+] Content card opened: {content_card}")

    prompt_content = f'Use the "crew-role-content" skill. You are assigned as content creator on card {content_card} with Verify: dual. Produce the deliverable, run proof, and hand off for review.'
    print(f"[*] Running subagent for {content_card}...")
    run_content = run_subagent_prompt("crew-role-content", prompt_content, timeout=300)
    sess_content = extract_session_from_db(run_content["start_time"], run_content["end_time"], prompt_content)
    telemetry_content = parse_tool_telemetry(sess_content)
    print(f"[+] Content finished: session={sess_content['session_id'] if sess_content else 'None'}, tools={telemetry_content['tool_names']}")

    # Save execution bundle
    out_bundle = {
        "worker": {
            "card_id": "t_c12f3b30",
            "session_id": "local-711732c2f42a59a72dfc4fe4259b3e0cb6d860d5b0c7fa8c352ff9a59b66236b",
            "status": "done",
            "proof_verdict": "PASS"
        },
        "verifier": {
            "card_id": verifier_card,
            "session_id": sess_verifier["session_id"] if sess_verifier else None,
            "telemetry": telemetry_verifier,
            "duration": run_verifier["duration"]
        },
        "content": {
            "card_id": content_card,
            "session_id": sess_content["session_id"] if sess_content else None,
            "telemetry": telemetry_content,
            "duration": run_content["duration"]
        }
    }
    with open("O:/workspaces/oss/crew/reports/crew-skills-remediation-raw-results.json", "w") as f:
        json.dump(out_bundle, f, indent=2)
    print("[✓] Raw execution bundle saved to O:/workspaces/oss/crew/reports/crew-skills-remediation-raw-results.json")

if __name__ == "__main__":
    main()

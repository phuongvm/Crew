import json
import os
import subprocess
import time

CREW_CARD_PY = r"O:/workspaces/oss/crew/scripts/crew_card.py"
HERMES_BIN = r"O:/workspaces/oss/hermes-agent/venv/Scripts/hermes.exe"

env = dict(os.environ)
env.pop("HERMES_DELEGATED_CHILD_CONTEXT", None)
env.pop("HERMES_KANBAN_TASK", None)
env.pop("HERMES_KANBAN_TASK_ID", None)

# Open content fixture card
open_cmd = [
    "python", CREW_CARD_PY, "open",
    "--title", "[fixture-eval] Content live test fixture",
    "--goal", "Author telemetry overview document in reports/telemetry-eval-fixture.md with verified statistics",
    "--role", "content",
    "--artifact", "reports/telemetry-eval-fixture.md",
    "--lands", "O:/workspaces/oss/crew",
    "--audience", "Commander",
    "--done-when", "reports/telemetry-eval-fixture.md exists and contains verified metrics",
    "--proof-cmd", "python -c \"import os; assert os.path.exists('reports/telemetry-eval-fixture.md') and os.path.getsize('reports/telemetry-eval-fixture.md') > 0\"",
    "--verify", "dual",
    "--assignee", "coder",
    "--json"
]
p = subprocess.run(open_cmd, capture_output=True, text=True, env=env)
card_data = json.loads(p.stdout)
card_id = card_data["id"]
print(f"[+] Content fixture card opened: {card_id}")

prompt = f'Use the "crew-role-content" skill. You are assigned as content creator on card {card_id} with Verify: dual. Produce the deliverable, run proof, and hand off for review.'
cmd = [HERMES_BIN, "-p", "default", "-s", "crew-role-content", "-z", prompt]

print(f"[*] Running subagent for content on {card_id}...")
t0 = time.time()
res = subprocess.run(cmd, capture_output=True, text=True, timeout=360, env=env)
print(f"[+] Content finished in {time.time() - t0:.1f}s (rc={res.returncode})")
print("STDOUT len:", len(res.stdout))
print("STDOUT:\n", res.stdout[:1000])

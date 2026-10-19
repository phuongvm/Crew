import os
import subprocess
import time

env = dict(os.environ)
env.pop("HERMES_DELEGATED_CHILD_CONTEXT", None)
env.pop("HERMES_KANBAN_TASK", None)
env.pop("HERMES_KANBAN_TASK_ID", None)

hermes_bin = r"O:/workspaces/oss/hermes-agent/venv/Scripts/hermes.exe"
card_id = "t_c12f3b30"
prompt = f'Use the "crew-role-worker" skill. You are assigned as worker on card {card_id}. Work the card to completion.'
cmd = [hermes_bin, "-p", "default", "-s", "crew-role-worker", "-z", prompt]

print(f"[*] Launching subagent for worker on {card_id}...")
t0 = time.time()
res = subprocess.run(cmd, capture_output=True, text=True, timeout=240, env=env)
print(f"[+] Subagent finished in {time.time() - t0:.1f}s (rc={res.returncode})")
print("STDOUT:\n", res.stdout[:1500])
print("STDERR:\n", res.stderr[:500])

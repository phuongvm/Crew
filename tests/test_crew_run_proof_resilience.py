#!/usr/bin/env python3
"""Regression tests for crew_safety.run_proof() and _exe_py_version() resilience (OpenSpec P0-1).

Seams under test:
  1. Non-interactive stdin isolation: when the parent process holds an open `stdin=PIPE` with a reader
     thread blocked in `sys.stdin.readline()` (as `agent.managed_worker` does on Windows), `run_proof()`
     completes via Git Bash without blocking (`< 2.0s`, `rc == 0`).
  2. Full process-tree termination on timeout: when a proof spawns a child Python sleeper and exceeds
     `timeout=1`, `run_proof()` returns `Result(124, "proof command timed out after 1s", "")` promptly
     and leaves zero surviving descendant processes (`crew_proc.alive(child_pid) is False`).
  3. Bounded stream capture: noisy stdout/stderr (`> 256 KiB`) is capped via `crew_proc.HeadTail` without
     halting the proof or buffering unbounded output in memory.
  4. Auxiliary interpreter version probe (`_exe_py_version`) attaches `stdin=subprocess.DEVNULL` and
     `crew_safety.py` imports cleanly even when `scripts/` is not pre-populated on `sys.path`.
"""
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = str(REPO / "scripts")
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)
os.environ.setdefault("HERMES_BIN", "/bin/false")

import crew_proc  # noqa: E402
import crew_safety  # noqa: E402

PY_POSIX = sys.executable.replace("\\", "/")


class RunProofResilienceTests(unittest.TestCase):
    def setUp(self):
        self._env = dict(os.environ)
        self.home = tempfile.mkdtemp(prefix="crew-run-proof-resilience-").replace(os.sep, "/")
        self.db = os.path.join(self.home, "kanban.db")
        os.environ.update(HERMES_HOME=self.home, HERMES_KANBAN_DB=self.db)
        for k in ("CREW_PROFILE_PREFIX", "HERMES_KANBAN_TASK", "CREW_COORDINATOR_TURN"):
            os.environ.pop(k, None)
        crew_safety._hermes()
        try:
            patch = mock.patch("tools.tirith_security.check_command_security", return_value={"action": "allow"})
            patch.start()
            self.addCleanup(patch.stop)
        except (ImportError, AttributeError):
            pass
        conn = sqlite3.connect(self.db)
        conn.executescript(
            "create table tasks (id text primary key, title text, status text, assignee text, body text);"
            "create table task_events (id integer primary key autoincrement, task_id text, run_id integer,"
            " kind text, payload text, created_at integer);"
        )
        conn.commit()
        conn.close()

    def tearDown(self):
        for key in [k for k in os.environ if k not in self._env]:
            del os.environ[key]
        os.environ.update(self._env)
        shutil.rmtree(self.home, ignore_errors=True)

    def test_run_proof_does_not_deadlock_when_parent_holds_blocked_stdin_pipe(self):
        sample = os.path.join(self.home, "sample.txt").replace("\\", "/")
        Path(sample).write_text("non-empty\n", encoding="utf-8")

        worker_script = textwrap.dedent("""
            import json, os, sys, threading, time

            scripts_dir, home_dir, db_path, sample_path = sys.argv[1:5]
            sys.path.insert(0, scripts_dir)
            os.environ["HERMES_HOME"] = home_dir
            os.environ["HERMES_KANBAN_DB"] = db_path
            os.environ["HERMES_BIN"] = "/bin/false"

            import crew_safety
            crew_safety._hermes()
            try:
                import tools.tirith_security as ts
                ts.check_command_security = lambda *_a, **_k: {"action": "allow"}
            except Exception:
                pass

            # Simulate agent.managed_worker holding synchronous ReadFile on inherited stdin pipe.
            reader = threading.Thread(target=sys.stdin.readline, daemon=True)
            reader.start()
            time.sleep(0.15)

            t0 = time.monotonic()
            res = crew_safety.run_proof("test -s '%s'" % sample_path, cwd=home_dir, timeout=2, mode="safe")
            dt = time.monotonic() - t0
            sys.stdout.write(json.dumps({"rc": res.rc, "dt": dt, "out": res.out, "blocked": res.blocked}) + "\\n")
            sys.stdout.flush()
            os._exit(0)
        """)

        proc = subprocess.Popen(
            [sys.executable, "-B", "-E", "-c", worker_script, SCRIPTS, self.home, self.db, sample],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        try:
            proc.wait(timeout=5.0)
            stdout = proc.stdout.read() if proc.stdout else ""
            stderr = proc.stderr.read() if proc.stderr else ""
        except subprocess.TimeoutExpired:
            stdout, stderr = "", "worker_script hung past 5.0s on inherited stdin pipe"
        finally:
            if proc.stdin:
                try:
                    proc.stdin.close()
                except OSError:
                    pass
            for stream in (proc.stdout, proc.stderr):
                if stream:
                    try:
                        stream.close()
                    except OSError:
                        pass
            if proc.poll() is None:
                crew_proc.terminate_tree(proc.pid, 0.2)
                proc.wait(timeout=5)

        self.assertEqual(0, proc.returncode, stderr)
        payload = json.loads(stdout.strip().splitlines()[-1])
        self.assertEqual("", payload["blocked"], payload)
        self.assertEqual(0, payload["rc"], payload)
        self.assertLess(payload["dt"], 2.0, payload)

    def test_timeout_terminates_descendant_process_tree_and_preserves_message(self):
        pid_file = os.path.join(self.home, "descendant.pid").replace("\\", "/")
        # Spawn a child Python sleeper from the proof process so killing only root bash leaves child_pid
        # orphaned unless run_proof terminates the full process tree / sweeps CREW_RUN_MARKER.
        cmd = (
            '"%s" -B -E -c "import subprocess, sys, time; '
            'p = subprocess.Popen([sys.executable, \'-B\', \'-E\', \'-c\', \'import time; time.sleep(60)\']); '
            'open(%r, \'w\', encoding=\'utf-8\').write(str(p.pid)); '
            'time.sleep(60)"'
        ) % (PY_POSIX, pid_file)

        child_pid = None
        try:
            t0 = time.monotonic()
            res = crew_safety.run_proof(cmd, cwd=self.home, timeout=1, mode="brave")
            elapsed = time.monotonic() - t0
            self.assertEqual(124, res.rc)
            self.assertEqual("proof command timed out after 1s", res.out)
            self.assertEqual("", res.blocked)
            self.assertLess(elapsed, 15.0)

            self.assertTrue(os.path.isfile(pid_file), "child sleeper never wrote pid file before timeout")
            child_pid = int(Path(pid_file).read_text(encoding="utf-8").strip())
            self.assertFalse(crew_proc.alive(child_pid), "descendant pid %d survived proof timeout" % child_pid)
        finally:
            if child_pid and crew_proc.alive(child_pid):
                crew_proc.terminate_tree(child_pid, 0.2)

    def test_noisy_stdout_and_stderr_are_bounded_via_head_tail(self):
        # > 256 KiB on both stdout and stderr (~600 KiB combined) must be bounded by 64 KiB HeadTail per stream.
        cmd = (
            '"%s" -B -E -c "import sys; '
            'sys.stdout.write(\'HEAD-OUT-\' + (\'x\' * 300000) + \'-TAIL-OUT\'); sys.stdout.flush(); '
            'sys.stderr.write(\'HEAD-ERR-\' + (\'y\' * 300000) + \'-TAIL-ERR\'); sys.stderr.flush()"'
        ) % PY_POSIX
        res = crew_safety.run_proof(cmd, cwd=self.home, timeout=30, mode="brave")
        self.assertEqual((0, ""), (res.rc, res.blocked))
        self.assertTrue("HEAD-OUT-" in res.out, "missing HEAD-OUT")
        self.assertTrue("-TAIL-OUT" in res.out, "missing TAIL-OUT")
        self.assertTrue("HEAD-ERR-" in res.out, "missing HEAD-ERR")
        self.assertTrue("-TAIL-ERR" in res.out, "missing TAIL-ERR")
        self.assertTrue("...[truncated " in res.out, "output not truncated (len=%d)" % len(res.out))
        self.assertLessEqual(len(res.out.encode("utf-8")), 2 * crew_proc.DEFAULT_STREAM_BYTES + 1024)

    def test_exe_py_version_passes_devnull_stdin(self):
        fake_exe = os.path.join(self.home, "custom_bin", "python.exe")
        os.makedirs(os.path.dirname(fake_exe), exist_ok=True)
        Path(fake_exe).write_bytes(b"")
        seen = []

        def fake_run(argv, **kw):
            seen.append((argv, kw))
            return subprocess.CompletedProcess(argv, 0, "3.12\n", "")

        with mock.patch.object(crew_safety.os.path, "realpath", return_value=fake_exe), \
                mock.patch.object(crew_safety.subprocess, "run", side_effect=fake_run):
            ver = crew_safety._exe_py_version(fake_exe)

        self.assertEqual((3, 12), ver)
        self.assertEqual(1, len(seen))
        self.assertEqual(subprocess.DEVNULL, seen[0][1].get("stdin"))

    def test_crew_safety_imports_cleanly_without_scripts_dir_preloaded_on_sys_path(self):
        code = textwrap.dedent("""
            import importlib.util, sys
            spec = importlib.util.spec_from_file_location("crew_safety_isolated", %r)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            assert hasattr(mod, "crew_proc"), "crew_proc not bound on crew_safety"
            print("OK")
        """) % str(REPO / "scripts" / "crew_safety.py")
        done = subprocess.run(
            [sys.executable, "-B", "-E", "-c", code],
            cwd=self.home,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=15,
            encoding="utf-8",
            errors="replace",
        )
        self.assertEqual(0, done.returncode, done.stderr)
        self.assertEqual("OK", done.stdout.strip())


if __name__ == "__main__":
    unittest.main()

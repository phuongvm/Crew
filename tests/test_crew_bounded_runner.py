"""crew_proc.run_bounded / crew_proc.terminate_tree (OpenSpec stewardship-core-adoption, Ticket 02, CREW-INV-7).

Seam: the hardened bounded runner. Head+tail capped streams (no early kill on output volume), empty stdin,
a monotonic deadline, an absolute System32\\taskkill.exe with a minimal environment on Windows, and a
per-run CREW_RUN_MARKER sweep that ends detached helpers a process-tree kill cannot reach.
"""
import os
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import crew_proc  # noqa: E402

PY = sys.executable


def py(code):
    return [PY, "-c", textwrap.dedent(code)]


class HeadTailBufferTests(unittest.TestCase):
    def test_small_input_is_kept_whole(self):
        buf = crew_proc.HeadTail(16)
        buf.feed(b"hello ")
        buf.feed(b"world")
        self.assertEqual(buf.text(), "hello world")
        self.assertEqual(buf.total, 11)
        self.assertFalse(buf.truncated)

    def test_overflow_keeps_head_and_tail_with_marker(self):
        buf = crew_proc.HeadTail(10)                 # 5 head + 5 tail
        for chunk in (b"ABCDE", b"-middle-", b"-more-", b"VWXYZ"):
            buf.feed(chunk)
        out = buf.text()
        self.assertTrue(out.startswith("ABCDE"), out)
        self.assertTrue(out.endswith("VWXYZ"), out)
        self.assertIn("truncated", out)
        self.assertTrue(buf.truncated)
        self.assertEqual(buf.total, 5 + 8 + 6 + 5)
        self.assertLessEqual(len(buf.head) + len(buf.tail), 10)


class RunBoundedTests(unittest.TestCase):
    def test_success_returns_streams_exit_code_and_marker(self):
        res = crew_proc.run_bounded(py("""
            import os, sys
            print("out:" + os.environ["CREW_RUN_MARKER"])
            print("err-line", file=sys.stderr)
            sys.exit(3)
        """), timeout_s=30)
        self.assertIsInstance(res, crew_proc.BoundedResult)
        self.assertEqual(res.exit_code, 3)
        self.assertFalse(res.timed_out)
        self.assertTrue(res.run_marker)
        self.assertIn("out:" + res.run_marker, res.stdout)
        self.assertIn("err-line", res.stderr)
        self.assertGreaterEqual(res.duration_s, 0.0)

    def test_stdin_is_empty_never_waits_for_input(self):
        res = crew_proc.run_bounded(py("""
            import sys
            data = sys.stdin.read()
            print("stdin=%d" % len(data))
        """), timeout_s=20)
        self.assertFalse(res.timed_out)
        self.assertIn("stdin=0", res.stdout)

    def test_flooded_stdout_and_stderr_are_capped_to_head_and_tail_without_early_kill(self):
        res = crew_proc.run_bounded(py("""
            import sys
            sys.stdout.write("HEAD-OUT" + "x" * (1024 * 1024) + "TAIL-OUT")
            sys.stdout.flush()
            sys.stderr.write("HEAD-ERR" + "y" * (1024 * 1024) + "TAIL-ERR")
            sys.stderr.flush()
            sys.exit(0)
        """), timeout_s=60)
        self.assertEqual(res.exit_code, 0)
        self.assertFalse(res.timed_out)
        for text, head, tail in ((res.stdout, "HEAD-OUT", "TAIL-OUT"), (res.stderr, "HEAD-ERR", "TAIL-ERR")):
            self.assertTrue(text.startswith(head), text[:40])
            self.assertTrue(text.endswith(tail), text[-40:])
            self.assertIn("truncated", text)
            self.assertLessEqual(len(text.encode("utf-8")), 65536 + 200)

    def test_custom_cap(self):
        res = crew_proc.run_bounded(py("print('A' * 50 + 'B' * 5000 + 'C' * 50)"), timeout_s=30, max_stream_bytes=100)
        self.assertTrue(res.stdout.startswith("A" * 50))
        self.assertTrue(res.stdout.rstrip().endswith("C" * 40))
        self.assertLessEqual(len(res.stdout.encode()), 100 + 200)

    def test_timeout_is_reported_and_the_process_ends(self):
        t0 = time.monotonic()
        res = crew_proc.run_bounded(py("import time; print('started', flush=True); time.sleep(60)"), timeout_s=1.5)
        self.assertTrue(res.timed_out)
        self.assertEqual(res.exit_code, 124)
        self.assertIn("started", res.stdout)
        self.assertLess(time.monotonic() - t0, 20)

    def test_env_and_cwd_are_passed(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, CREW_TEST_VALUE="v-42")
            res = crew_proc.run_bounded(py("import os; print(os.getcwd()); print(os.environ['CREW_TEST_VALUE'])"),
                                        timeout_s=30, cwd=tmp, env=env)
            self.assertIn("v-42", res.stdout)
            self.assertEqual(os.path.normcase(os.path.realpath(res.stdout.splitlines()[0])),
                             os.path.normcase(os.path.realpath(tmp)))
            self.assertNotIn("CREW_RUN_MARKER", env, "the caller's env dict is not mutated")

    def test_missing_executable_reports_127(self):
        res = crew_proc.run_bounded([os.path.join(tempfile.gettempdir(), "no-such-binary-crew-xyz")], timeout_s=5)
        self.assertEqual(res.exit_code, 127)
        self.assertFalse(res.timed_out)

    def test_detached_marker_child_is_swept_on_timeout(self):
        with tempfile.TemporaryDirectory() as tmp:
            pid_file = os.path.join(tmp, "grandchild.pid")
            # top-level child -> intermediate (exits at once) -> detached grandchild in its own session/group.
            # Neither the POSIX process group nor taskkill /T reaches the orphan; only the marker sweep does.
            grandchild = "import time; time.sleep(120)"
            intermediate = textwrap.dedent("""
                import subprocess, sys
                kw = {}
                if sys.platform == "win32":
                    kw["creationflags"] = 0x00000008 | 0x00000200   # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
                else:
                    kw["start_new_session"] = True
                p = subprocess.Popen([sys.executable, "-c", %r], stdin=subprocess.DEVNULL,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kw)
                open(%r, "w").write(str(p.pid))
            """) % (grandchild, pid_file)
            top = textwrap.dedent("""
                import subprocess, sys, time
                subprocess.run([sys.executable, "-c", %r])
                print("spawned", flush=True)
                time.sleep(120)
            """) % (intermediate,)
            res = crew_proc.run_bounded([PY, "-c", top], timeout_s=4)
            self.assertTrue(res.timed_out, res)
            gpid = int(Path(pid_file).read_text())
            try:
                deadline = time.monotonic() + 10
                while crew_proc.alive(gpid) and time.monotonic() < deadline:
                    time.sleep(0.1)
                self.assertFalse(crew_proc.alive(gpid), "detached CREW_RUN_MARKER grandchild survived")
            finally:
                if crew_proc.alive(gpid):
                    crew_proc.terminate_tree(gpid, 0.2)


class SweepMarkerTests(unittest.TestCase):
    def test_sweep_ends_only_processes_carrying_the_marker(self):
        marker = "crew-test-" + os.urandom(6).hex()
        kw = {"start_new_session": True} if os.name != "nt" else {"creationflags": 0x00000200}
        tagged = subprocess.Popen([PY, "-c", "import time; time.sleep(60)"], env=dict(os.environ, CREW_RUN_MARKER=marker),
                                  stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kw)
        other = subprocess.Popen([PY, "-c", "import time; time.sleep(60)"], env=dict(os.environ, CREW_RUN_MARKER="other"),
                                 stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kw)
        try:
            time.sleep(0.5)
            swept = crew_proc.sweep_marker(marker)
            self.assertIn(tagged.pid, swept)
            self.assertNotIn(other.pid, swept)
            tagged.wait(timeout=10)
            self.assertIsNone(other.poll())
        finally:
            for p in (tagged, other):
                if p.poll() is None:
                    p.kill()
                p.wait()

    def test_empty_marker_sweeps_nothing(self):
        self.assertEqual(crew_proc.sweep_marker(""), [])
        self.assertEqual(crew_proc.sweep_marker(None), [])


class TaskkillResolutionTests(unittest.TestCase):
    def test_taskkill_is_absolute_under_system32(self):
        exe = crew_proc.taskkill_exe(system_root=r"C:\Windows")
        self.assertEqual(exe.replace("/", "\\").lower(), r"c:\windows\system32\taskkill.exe")
        self.assertTrue(os.path.isabs(exe) or exe[1:3] == ":\\")

    def test_terminate_tree_on_windows_never_uses_a_bare_taskkill(self):
        calls = []

        def fake_run(argv, **kw):
            calls.append((argv, kw))
            return subprocess.CompletedProcess(argv, 0, b"", b"")

        with mock.patch.object(crew_proc, "IS_WINDOWS", True), \
                mock.patch.object(crew_proc, "_system_root", return_value=r"C:\Windows"), \
                mock.patch.object(crew_proc.subprocess, "run", side_effect=fake_run), \
                mock.patch.object(crew_proc, "alive", return_value=False), \
                mock.patch.object(crew_proc, "sweep_marker", return_value=[]) as sweep:
            self.assertTrue(crew_proc.terminate_tree(4242, 0.1, run_marker="m-1"))
        argv, kw = calls[0]
        self.assertNotEqual(argv[0].lower(), "taskkill")
        self.assertEqual(argv[0].replace("/", "\\").lower(), r"c:\windows\system32\taskkill.exe")
        self.assertEqual(argv[1:], ["/PID", "4242", "/T", "/F"])
        env = kw.get("env")
        self.assertIsNotNone(env, "taskkill runs with an explicit minimal environment")
        self.assertEqual(set(env), {"SystemRoot", "PATH"})
        self.assertEqual(env["PATH"].replace("/", "\\").lower(), r"c:\windows\system32")
        self.assertFalse(kw.get("shell"))
        sweep.assert_called_once_with("m-1")

    def test_terminate_tree_without_marker_does_not_sweep(self):
        with mock.patch.object(crew_proc, "IS_WINDOWS", True), \
                mock.patch.object(crew_proc, "_system_root", return_value=r"C:\Windows"), \
                mock.patch.object(crew_proc.subprocess, "run",
                                  return_value=subprocess.CompletedProcess([], 0, b"", b"")), \
                mock.patch.object(crew_proc, "alive", return_value=False), \
                mock.patch.object(crew_proc, "sweep_marker") as sweep:
            crew_proc.terminate_tree(4242, 0.1)
        sweep.assert_not_called()

    def test_real_terminate_tree_still_ends_a_child(self):
        kw = {"start_new_session": True} if os.name != "nt" else {}
        proc = subprocess.Popen([PY, "-c", "import time; time.sleep(60)"], **kw)
        try:
            time.sleep(0.3)
            self.assertTrue(crew_proc.terminate_tree(proc.pid, 0.2))
            self.assertFalse(crew_proc.alive(proc.pid))
        finally:
            if proc.poll() is None:
                proc.kill()
            proc.wait()


if __name__ == "__main__":
    unittest.main()

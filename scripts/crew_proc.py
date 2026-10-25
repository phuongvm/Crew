#!/usr/bin/env python3
"""Process facts the crew needs on every OS: is a pid running, what is its command line, end its tree.

One module, because `os.kill(pid, 0)` is a liveness probe only on POSIX: on Windows signal 0 is not a signal and
raises WinError 87 for any pid. Windows uses OpenProcess + GetExitCodeProcess (stdlib ctypes only); POSIX keeps
signal 0, and a zombie (a killed child nobody reaped) counts as gone on Linux.
"""
import ntpath
import os
import secrets
import signal
import subprocess
import threading
import time
from dataclasses import dataclass

IS_WINDOWS = os.name == "nt"
STILL_ACTIVE = 259                       # GetExitCodeProcess for a process that has not exited
_QUERY_LIMITED = 0x1000                  # PROCESS_QUERY_LIMITED_INFORMATION
_SYNCHRONIZE = 0x00100000


def _win_alive(pid):
    import ctypes
    from ctypes import wintypes
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.OpenProcess.restype = wintypes.HANDLE
    k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    k32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    k32.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = k32.OpenProcess(_QUERY_LIMITED, False, pid)
    if not handle:
        # ERROR_ACCESS_DENIED (5): it exists but is not ours to query. Anything else (87 bad pid, ...): gone.
        return ctypes.get_last_error() == 5
    try:
        code = wintypes.DWORD()
        if not k32.GetExitCodeProcess(handle, ctypes.byref(code)):
            return False
        return code.value == STILL_ACTIVE
    finally:
        k32.CloseHandle(handle)


def alive(pid):
    """True while `pid` is a running process. A zombie reads dead. Garbage (None, text, <= 0) reads dead."""
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    if pid <= 0:
        return False
    if IS_WINDOWS:
        return _win_alive(pid)
    try:
        with open("/proc/%d/stat" % pid, encoding="utf-8") as fh:
            if fh.read().rsplit(") ", 1)[-1][:1] == "Z":
                return False
    except OSError:
        pass
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except (PermissionError, ValueError, OverflowError):
        return True


def cmdline_of(pid):
    """The process's command line as one string, '' when unreadable."""
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return ""
    if IS_WINDOWS:
        ps = ("(Get-CimInstance Win32_Process -Filter 'ProcessId=%d').CommandLine" % pid)
        try:
            done = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                                   "[Console]::OutputEncoding=[Text.Encoding]::UTF8; " + ps],
                                  capture_output=True, encoding="utf-8", errors="replace", timeout=30)
        except (OSError, subprocess.SubprocessError):
            return ""
        return (done.stdout or "").strip()
    try:
        with open("/proc/%d/cmdline" % pid, encoding="utf-8") as fh:
            return fh.read().replace("\0", " ")
    except OSError:
        return ""


def _system_root():
    """%SystemRoot% as an absolute drive path (C:\\Windows when unset or not absolute): the only directory the
    crew resolves Windows system binaries from, never the working directory or PATH."""
    for key in ("SystemRoot", "SYSTEMROOT", "windir", "WINDIR"):
        val = (os.environ.get(key) or "").strip()
        if ntpath.isabs(val) and ntpath.splitdrive(val)[0]:
            return val
    return r"C:\Windows"


def taskkill_exe(system_root=None):
    """The absolute %SystemRoot%\\System32\\taskkill.exe. A bare `taskkill` is looked up in the working directory
    first on Windows, so a planted taskkill.exe in a proof's cwd would run instead (binary planting)."""
    return ntpath.join(system_root or _system_root(), "System32", "taskkill.exe")


def _process_marker(proc):
    try:
        return (proc.environ() or {}).get(MARKER_ENV)
    except Exception:  # noqa: BLE001 - access denied, gone, zombie: not ours to judge
        return None


def _marked_pids(marker):
    """Pids (never this process) whose environment carries CREW_RUN_MARKER=<marker>. psutil where installed (Hermes
    ships it), else /proc/<pid>/environ on Linux; [] where neither can read another process's environment."""
    me = os.getpid()
    found = []
    try:
        import psutil
    except ImportError:
        psutil = None
    if psutil is not None:
        for proc in psutil.process_iter(["pid"]):
            if proc.pid != me and _process_marker(proc) == marker:
                found.append(proc.pid)
        return found
    if IS_WINDOWS or not os.path.isdir("/proc"):
        return found
    needle = ("%s=%s" % (MARKER_ENV, marker)).encode()
    for name in os.listdir("/proc"):
        if not name.isdigit() or int(name) == me:
            continue
        try:
            with open("/proc/%s/environ" % name, "rb") as fh:
                if needle in fh.read().split(b"\0"):
                    found.append(int(name))
        except OSError:
            continue
    return found


def sweep_marker(marker, wait_s=0.5):
    """End every process still carrying CREW_RUN_MARKER=<marker> (detached helpers a tree kill cannot reach,
    because their parent already exited). Returns the pids it ended. An empty marker sweeps nothing."""
    marker = str(marker or "").strip()
    if not marker:
        return []
    swept = []
    for pid in _marked_pids(marker):
        _kill_tree_once(pid, wait_s)
        swept.append(pid)
    return swept


def _kill_tree_once(pid, wait_s):
    if IS_WINDOWS:
        root = _system_root()
        try:
            subprocess.run([taskkill_exe(root), "/PID", str(pid), "/T", "/F"], capture_output=True, timeout=60,
                           env={"SystemRoot": root, "PATH": ntpath.join(root, "System32")}, shell=False,
                           stdin=subprocess.DEVNULL)
        except (OSError, subprocess.SubprocessError):
            pass
        deadline = time.monotonic() + max(wait_s, 5.0)
        while alive(pid) and time.monotonic() < deadline:
            time.sleep(0.1)
        return not alive(pid)
    try:
        pgid = os.getpgid(pid)
    except ProcessLookupError:
        return not alive(pid)
    if pgid == os.getpgid(0):          # never signal our own group (a child not started in its own session)
        pgid = None
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            if pgid is not None:
                os.killpg(pgid, sig)
            else:
                os.kill(pid, sig)
        except ProcessLookupError:
            break
        time.sleep(wait_s)
        if not alive(pid):
            break
    if alive(pid):
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass
    return not alive(pid)


def terminate_tree(pid, wait_s=1.0, run_marker=None):
    """End `pid` and everything it started. POSIX: SIGTERM then SIGKILL to the process group, then the pid itself.
    Windows: the absolute %SystemRoot%\\System32\\taskkill.exe /T /F under a minimal environment (SystemRoot, PATH =
    System32 only). With `run_marker`, any surviving process that still carries CREW_RUN_MARKER=<run_marker> is
    swept as well. Returns True when the pid is gone afterwards."""
    pid = int(pid)
    gone = _kill_tree_once(pid, wait_s)
    if run_marker:
        sweep_marker(run_marker)
    return gone and not alive(pid)


# ------------------------------------------------------------------ bounded runner
MARKER_ENV = "CREW_RUN_MARKER"
DEFAULT_STREAM_BYTES = 65536
_READ_CHUNK = 65536


class HeadTail:
    """At most `cap` bytes of a stream: the first cap//2 and the last cap - cap//2. Memory stays bounded whatever
    the child writes, and the child is never stopped for writing too much."""

    def __init__(self, cap=DEFAULT_STREAM_BYTES):
        cap = max(int(cap), 2)
        self.head_cap = cap // 2
        self.tail_cap = cap - self.head_cap
        self.head = bytearray()
        self.tail = bytearray()
        self.total = 0

    def feed(self, chunk):
        if not chunk:
            return
        self.total += len(chunk)
        room = self.head_cap - len(self.head)
        if room > 0:
            self.head += chunk[:room]
            chunk = chunk[room:]
        if chunk:
            self.tail += chunk
            if len(self.tail) > self.tail_cap:
                del self.tail[:len(self.tail) - self.tail_cap]

    @property
    def truncated(self):
        return self.total > len(self.head) + len(self.tail)

    def text(self):
        head = bytes(self.head).decode("utf-8", errors="replace")
        tail = bytes(self.tail).decode("utf-8", errors="replace")
        if not self.truncated:
            return head + tail
        dropped = self.total - len(self.head) - len(self.tail)
        return "%s\n...[truncated %d bytes]...\n%s" % (head, dropped, tail)


@dataclass(frozen=True)
class BoundedResult:
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool
    duration_s: float
    run_marker: str


def _pump(stream, buf):
    try:
        while True:
            chunk = stream.read(_READ_CHUNK)
            if not chunk:
                break
            buf.feed(chunk)
    except (OSError, ValueError):
        pass


def run_bounded(cmd, *, timeout_s=60.0, max_stream_bytes=DEFAULT_STREAM_BYTES, cwd=None, env=None):
    """Run `cmd` unattended: empty stdin, a monotonic deadline, stdout and stderr read concurrently into head+tail
    buffers of `max_stream_bytes` each, and CREW_RUN_MARKER=<random token> in the child's environment. On timeout
    the tree is ended (terminate_tree) and every process still carrying the marker is swept; exit_code is 124.
    A command that cannot start answers 127. `cmd` is an argv list, or a string run by the platform shell."""
    marker = "crew-%s" % secrets.token_hex(12)
    child_env = dict(os.environ if env is None else env)
    child_env[MARKER_ENV] = marker
    kw = {}
    if IS_WINDOWS:
        kw["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)
    else:
        kw["start_new_session"] = True
    started = time.monotonic()
    try:
        proc = subprocess.Popen(cmd, shell=isinstance(cmd, str), cwd=cwd, env=child_env, stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0, **kw)
    except OSError as exc:
        return BoundedResult(127, "", "%s: %s" % (type(exc).__name__, exc), False,
                             time.monotonic() - started, marker)
    out_buf, err_buf = HeadTail(max_stream_bytes), HeadTail(max_stream_bytes)
    readers = [threading.Thread(target=_pump, args=(proc.stdout, out_buf), daemon=True),
               threading.Thread(target=_pump, args=(proc.stderr, err_buf), daemon=True)]
    for t in readers:
        t.start()
    timed_out = False
    try:
        proc.wait(timeout=max(float(timeout_s), 0.0))
    except subprocess.TimeoutExpired:
        timed_out = True
    except BaseException:                      # KeyboardInterrupt: never leave the tree behind
        terminate_tree(proc.pid, 0.5, run_marker=marker)
        raise
    if timed_out:
        terminate_tree(proc.pid, 0.5, run_marker=marker)
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
    for t in readers:
        t.join(timeout=5)
    for stream in (proc.stdout, proc.stderr):
        try:
            stream.close()
        except OSError:
            pass
    duration = time.monotonic() - started
    code = 124 if timed_out else (proc.returncode if proc.returncode is not None else 1)
    return BoundedResult(code, out_buf.text(), err_buf.text(), timed_out, duration, marker)


def utf8_stdio():
    """Print UTF-8 whatever the console code page is (a piped Windows child defaults to cp1252, which turns the
    '·' and the status emoji the crew prints into errors or mojibake for whoever reads the pipe)."""
    import sys
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass

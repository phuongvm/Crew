#!/usr/bin/env python3
"""Whether, and how, an unattended proof command may run.

A card's proof command is shell the crew runs with nobody watching: `crew_card.py verdict` (the writer's and
the verifier's run), the coordinator's verify/audit runs, and the stale-block heal all end up in `run_proof`
below, and nowhere else. A proof is not a tool call, so Hermes's approvals never see it; this module puts the
same floors in front of it:

  always   Hermes's hardline list (wiping the root, formatting a disk, fork bombs) and the owner's `approvals.deny` globs
  safe     also anything Hermes flags as dangerous (detect_dangerous_command, unless permanently approved)
           or tirith flags - the default
  brave    nothing else; chosen per card (`Proof mode: brave` in the intake, stored on the card's snapshot)
           or for good (`/crew-safety brave` sets approvals.mode off on the crew profiles)

Any failure to load Hermes's detectors blocks the run: a floor that could not be checked is not a pass.
A blocked proof is not a FAIL: the result says so and the caller asks the owner.

The environment is scrubbed the same way Hermes scrubs a terminal child (provider keys, bot tokens and the
gateway's secrets stay out), so a proof cannot read or leak them.

A proof that runs a script (`python3 /x/site/.crew/verify.py`) is only as good as the file: the first run of each
script on a card records its sha256 on the card, and a later run of a changed script is blocked like any other
refusal (`SCRIPT_CHANGED`) and the coordinator decides (crew_coordinator `revise_script`: it may accept the script or
have the verifier rewrite it, with a reason on record); the writer never writes or changes a proof script.
"""
import hashlib
import os
import re
import shutil
import subprocess
import sys
from collections import namedtuple

IS_WINDOWS = os.name == "nt"     # a name of its own so a test can pin the Windows branch on Linux
PROOF_MODES = ("safe", "brave")
APPROVED = "approved"            # a mode only proof_mode() returns: safe, but this exact command has the owner's yes
BLOCKED_RC = 126                 # what a shell says for "found but refused"; Result.blocked carries the reason
ENV_KEEP = ("PATH", "HOME", "LANG", "HERMES_HOME", "HERMES_KANBAN_DB", "HERMES_KANBAN_BOARD", "TMPDIR")


def _hermes_home():
    return os.environ.get("HERMES_HOME") or os.path.expanduser("~/.hermes")


def _base_home():
    h = os.path.abspath(_hermes_home())
    if os.path.basename(os.path.dirname(h)) == "profiles":
        return os.path.dirname(os.path.dirname(h))
    return h


def _find_hermes_sources():
    sources = []
    seen = set()

    def _add(path):
        # Only a real Hermes checkout counts: a bare dir (e.g. ~/.hermes/hermes-agent left by a failed install)
        # would land on the proof PYTHONPATH and trip the hermes-agent tests' real-home I/O guard.
        if not path:
            return
        norm = os.path.abspath(os.path.normpath(path))
        if norm not in seen and os.path.isfile(os.path.join(norm, "hermes_cli", "__init__.py")):
            seen.add(norm)
            sources.append(norm)

    for env_var in ("HERMES_AGENT_SRC", "HERMES_AGENT_DIR", "HERMES_SRC"):
        val = os.environ.get(env_var)
        if val:
            _add(val)

    cur = os.path.abspath(__file__)
    while True:
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
        for sub in ("hermes-agent", os.path.join("oss", "hermes-agent")):
            _add(os.path.join(cur, sub))

    _add(os.path.join(_base_home(), "hermes-agent"))
    _add(os.path.expanduser("~/.hermes/hermes-agent"))
    return tuple(sources)


HERMES_SRC = _find_hermes_sources()

class Result(namedtuple("Result", "rc out blocked")):
    """rc, out (stdout + stderr) and blocked (the refusal reason, '' when it ran); `output` names the same text."""
    __slots__ = ()

    @property
    def output(self):
        return self.out


SCRIPT_CHANGED = "proof script changed since it first ran: "     # the prefix crew_coordinator.proof_blocked_ask keys on
# An absolute script path in a proof command. Relative paths (and ones with spaces) are not bound: they depend on
# the cwd, and the intake writes absolute paths (`<folder>/.crew/verify.py`).
# A script path a proof names: POSIX absolute (/x/site/.crew/verify.py, also Git Bash's /c/Users/...) or a Windows
# drive path (C:/x/verify.py, C:\\x\\verify.py).
SCRIPT_RX = re.compile(r"(?<![\w./~-])((?:[A-Za-z]:[/\\]|/)[^\s'\"`;|&<>()$]+\.(?:py|sh|js))(?![\w/.-])")
_GIT_BASH_DRIVE_RX = re.compile(r"^/([A-Za-z])(?=/)")


def _script_file(path):
    """Where a script path named in a proof is on disk. Git Bash writes C:\\x as /c/x, which Windows Python cannot
    open: without this mapping a script named that way would silently escape the hash binding."""
    if IS_WINDOWS:
        return _GIT_BASH_DRIVE_RX.sub(lambda m: m.group(1).upper() + ":", path)
    return path


def git_bash():
    """The bash a proof runs under on Windows: the one Hermes itself runs commands in. HERMES_GIT_BASH_PATH, then the
    PortableGit Hermes's installer puts under <Hermes home>\\git (bin\\bash.exe, MinGit's usr\\bin\\bash.exe),
    then Git for Windows' own, found from git.exe. Never a bare `bash` on PATH (C:\\Windows\\System32\\bash.exe is
    WSL's, a different machine with different paths), never cmd.exe. '' when no Git Bash is installed."""
    import crew_card
    custom = os.environ.get("HERMES_GIT_BASH_PATH") or ""
    if custom and os.path.isfile(custom):
        return custom
    for root in (crew_card.base_home(), crew_card.default_home()):
        for rel in (("git", "bin", "bash.exe"), ("git", "usr", "bin", "bash.exe")):
            cand = os.path.join(root, *rel)
            if os.path.isfile(cand):
                return cand
    git = shutil.which("git")
    if not git:
        return ""
    here = os.path.dirname(git)
    for root in (os.path.dirname(here), os.path.dirname(os.path.dirname(here)), here):
        for rel in (("bin", "bash.exe"), ("usr", "bin", "bash.exe")):
            cand = os.path.join(root, *rel)
            if os.path.isfile(cand):
                return cand
    return ""


def _hermes():
    """Make Hermes's own modules importable (the crew scripts run under any python): its source root goes on
    the path whole, because an editable install exposes the packages but not top-level modules like hermes_yaml.
    The root is HERMES_AGENT_SRC, else crew_card.hermes_root() (this Hermes home's hermes-agent, which on a native
    Windows install is <%LOCALAPPDATA%\\hermes>\\hermes-agent). Raises ImportError when there is no Hermes."""
    import glob
    import crew_card
    sources = list(_find_hermes_sources())
    root = crew_card.hermes_root()
    if root and root not in sources:
        sources.append(root)
    for src in sources:
        if src and os.path.isdir(src) and src not in sys.path:
            sys.path.append(src)
    _venv_deps()
    try:
        import tools.approval_detection  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            f"Hermes safety checks could not be loaded ({exc}). "
            "Please run under the Hermes venv interpreter."
        ) from exc


def _venv_deps():
    """Put Hermes's dependency venv on the path when this interpreter cannot import them itself: under the
    package-manager layout a bare interpreter (cron, the gateway) runs the crew scripts while ruamel and the rest
    live in the venv Hermes commits. Appended last, so anything the bare interpreter has wins."""
    try:
        import ruamel.yaml  # noqa: F401
        return
    except ImportError:
        pass
    import crew_card
    py = crew_card.hermes_python()
    candidates = []
    if py:
        vdir = os.path.dirname(os.path.dirname(py))
        candidates.extend([
            os.path.join(vdir, "Lib", "site-packages"),
            os.path.join(vdir, "lib", "site-packages"),
            *glob.glob(os.path.join(vdir, "lib", "python*", "site-packages")),
        ])
        if hasattr(crew_card, "venv_site_packages"):
            candidates.extend(crew_card.venv_site_packages(vdir))
    base = _base_home()
    candidates.extend(glob.glob(os.path.join(base, "installs", "*", "environments", "*", "venv", "Lib", "site-packages")))
    candidates.extend(glob.glob(os.path.join(base, "installs", "*", "environments", "*", "venv", "lib", "python*", "site-packages")))
    for src in _find_hermes_sources():
        for venv_name in ("venv", ".venv"):
            vdir = os.path.join(src, venv_name)
            candidates.append(os.path.join(vdir, "Lib", "site-packages"))
            candidates.extend(glob.glob(os.path.join(vdir, "lib", "python*", "site-packages")))
    for sp in sorted(set(candidates)):
        if os.path.isdir(sp) and sp not in sys.path:
            sys.path.append(sp)


def _home_vars(env):
    """Keep a home the child's `Path.home()` can read. The scrub carries HOME (a native Windows process
    never sets it) and drops USERPROFILE/SYSTEMROOT (a native Windows process always has them), and a child
    with neither dies in expanduser before it can load its profile."""
    for key in ("USERPROFILE", "HOMEDRIVE", "HOMEPATH", "SYSTEMROOT", "HOME"):
        if not env.get(key) and os.environ.get(key):
            env[key] = os.environ[key]
    if sys.platform == "win32":
        # Windows expanduser/Path.home reads USERPROFILE (HOME too, for POSIX-style callers), and a native
        # Windows process starts with neither in the scrub. Cross-fill them only here: on POSIX a HOME->
        # USERPROFILE copy would hand every child a bogus Windows username.
        if not env.get("HOME") and env.get("USERPROFILE"):
            env["HOME"] = env["USERPROFILE"]
        if not env.get("USERPROFILE") and env.get("HOME"):
            env["USERPROFILE"] = env["HOME"]
    return env


def proof_env(extra=None):
    """The environment a proof (and the coordinator's own subprocesses) runs with: Hermes's scrubbed child env,
    plus the few variables the crew scripts need to find the board. Never os.environ as it is."""
    try:
        _hermes()
        from tools.environments.local import build_subprocess_env
        env = build_subprocess_env()
    except Exception:  # noqa: BLE001 - no Hermes: the smallest env that still runs a shell command
        env = {k: v for k, v in os.environ.items() if k in ENV_KEEP or k.startswith("CREW_")}
    env.update({k: os.environ[k] for k in ENV_KEEP if k in os.environ})
    _home_vars(env)
    import glob
    base = _base_home()
    extra_py_paths = []
    for sp in glob.glob(os.path.join(base, "installs", "*", "environments", "*", "venv", "Lib", "site-packages")):
        if sp not in extra_py_paths:
            extra_py_paths.append(sp)
    for sp in glob.glob(os.path.join(base, "installs", "*", "environments", "*", "venv", "lib", "python*", "site-packages")):
        if sp not in extra_py_paths:
            extra_py_paths.append(sp)
    for src in _find_hermes_sources():
        if src and os.path.isdir(src) and src not in extra_py_paths:
            extra_py_paths.append(src)
        for venv_name in ("venv", ".venv"):
            vdir = os.path.join(src, venv_name)
            for sp in (
                os.path.join(vdir, "Lib", "site-packages"),
                *glob.glob(os.path.join(vdir, "lib", "python*", "site-packages")),
            ):
                if os.path.isdir(sp) and sp not in extra_py_paths:
                    extra_py_paths.append(sp)
    if extra_py_paths:
        existing_pp = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = os.pathsep.join(extra_py_paths + ([existing_pp] if existing_pp else []))
    env.update(extra or {})
    return env


def _permanently_approved(key, cmd):
    """Hermes's own 'always allow this' answer for a flagged pattern; unknown -> not approved."""
    try:
        from tools.approval import _is_permanently_approved
        from tools.approval_floors import _command_matches_permanent_allowlist
        return bool(_is_permanently_approved(key) or _command_matches_permanent_allowlist(cmd))
    except Exception:  # noqa: BLE001
        return False


def _tirith_block(cmd):
    """Why tirith stops this command, '' when it does not. A Hermes without the scanner (it was removed from core)
    has nothing to stop it. An unusable scanner follows security.tirith_fail_open exactly as tools/approval.py
    did: open (default) lets it through, closed blocks."""
    try:
        from tools.approval_context import _tirith_fail_open
        fail_open = _tirith_fail_open()
    except Exception:
        fail_open = True
    try:
        from tools.tirith_security import check_command_security
    except ModuleNotFoundError:
        return ""
    except Exception:  # noqa: BLE001
        check_command_security = None
    if not check_command_security:
        return ""
    try:
        verdict = check_command_security(cmd)
    except Exception:  # noqa: BLE001
        return "" if fail_open else "the tirith scanner is unavailable and security.tirith_fail_open is false"
    if verdict.get("action") in ("block", "warn"):
        return "tirith: %s" % (verdict.get("summary") or verdict.get("action"))
    return ""


def cmd_hash(cmd):
    return hashlib.sha256(str(cmd or "").strip().encode()).hexdigest()


# A proof is bash text, but a card written on Windows often carries PowerShell (`Test-Path x`), which Git Bash
# answers with exit 127: a false FAIL. Only a cmdlet in command position counts (the first word of a command, outside
# quotes), so `pwsh -Command "Test-Path x"`, `echo Test-Path` and `python -c "...'Test-Path'..."` stay bash.
POWERSHELL_BARE_CMDLET_RX = re.compile(
    r"^(?:(?i:Test-Path|Get-ChildItem|Get-Content|Set-Content|Add-Content|Select-String|Set-Location|New-Item"
    r"|Remove-Item|Get-Process|Start-Process|Stop-Process|Get-Item|Copy-Item|Move-Item|Write-Output|Write-Host"
    r"|Get-FileHash|Invoke-WebRequest|Invoke-RestMethod|Resolve-Path|Join-Path)"
    # any other cmdlet in its canonical case: an approved verb, a capitalised noun. Case matters here, so POSIX
    # tools that happen to look alike (start-stop-daemon, update-alternatives, add-apt-repository) never match.
    r"|(?:Get|Set|Test|New|Remove|Add|Clear|Copy|Move|Rename|Select|Start|Stop|Invoke|Write|Read|Out|Join"
    r"|Resolve|Split|Measure|Compare|Import|Export|ConvertTo|ConvertFrom|Format|Wait|Push|Pop|Expand|Compress"
    r"|Update|Enable|Disable|Install|Uninstall|Register|Unregister|Find|Show|Restart)-[A-Z][A-Za-z0-9]*)$")
POWERSHELL_WRAPPER_RX = re.compile(r"^(?:.*[/\\])?(?:powershell|pwsh)(?:\.exe)?$", re.IGNORECASE)
POWERSHELL_LINT = ("bare PowerShell cmdlet '%s' without pwsh wrapper (Git Bash on Windows will fail with command "
                   "not found). Use POSIX (e.g. 'test -f') or wrap as 'pwsh.exe -NoProfile -Command \"...\"'")
_SHELL_LEAD_WORDS = {"!", "if", "then", "else", "elif", "do", "while", "until", "time", "exec", "{", "("}


def _command_words(cmd):
    """First words of bash commands, ignoring literal quotes and comments. `$()` has its own quote context,
    even inside double quotes; closing it restores the surrounding word rather than starting a command."""
    words, cur, quote, at_start = [], [], "", True
    contexts = []
    in_word = False
    text = str(cmd or "")
    i = 0
    while i < len(text):
        ch = text[i]
        if quote == "'":
            if ch == quote:
                quote = ""
        elif ch == "\\" and i + 1 < len(text):
            # In double quotes bash only escapes these characters; an escaped newline is not a word.
            if not quote or text[i + 1] in '$`"\\\n':
                if text[i + 1] != "\n":
                    cur.append(text[i + 1])
                    in_word = True
                i += 1
        elif text[i:i + 2] == "$(":
            contexts.append((cur, quote, at_start, True))
            cur, quote, at_start, in_word = [], "", True, False
            i += 1
        elif quote:
            if ch == quote:
                quote = ""
        elif ch in "'\"":
            quote, at_start, in_word = ch, False, True
            cur = []
        elif ch == "#" and not in_word:
            # Only an unquoted # at the start of a word opens a comment; word# and ""# are literal.
            end = text.find("\n", i)
            i = len(text) if end == -1 else end
            continue
        elif ch == "(":
            if cur and at_start:
                words.append("".join(cur))
            contexts.append(([], "", False, False))
            cur, at_start, in_word = [], True, False
        elif ch == ")" and contexts:
            if cur and at_start:
                words.append("".join(cur))
            cur, quote, at_start, in_word = contexts.pop()
        elif ch in ";&|\n)`":
            if cur and at_start:
                words.append("".join(cur))
            cur, at_start, in_word = [], True, False
        elif ch.isspace():
            if cur and at_start:
                word = "".join(cur)
                if word in _SHELL_LEAD_WORDS or re.match(r"^[A-Za-z_]\w*=", word):
                    cur = []                         # a keyword or VAR=value: the command word is the next one
                else:
                    words.append(word)
                    cur, at_start = [], False
            else:
                cur = []
            in_word = False
        else:
            cur.append(ch)
            in_word = True
        i += 1
    if cur and at_start:
        words.append("".join(cur))
    return words


def detect_bare_powershell(cmd):
    """The first PowerShell cmdlet a proof runs as a command of its own (not through pwsh/powershell), '' when none."""
    for word in _command_words(cmd):
        if POWERSHELL_WRAPPER_RX.match(word):
            continue
        if POWERSHELL_BARE_CMDLET_RX.match(word):
            return word
    return ""


def _powershell():
    """The PowerShell a routed proof runs under: PowerShell 7, then Windows PowerShell 5.1, then pwsh.exe."""
    return shutil.which("pwsh") or shutil.which("powershell") or "pwsh.exe"


# What runs under -Command: the proof verbatim in a dot-sourced block, with bash's exit status rules. PowerShell
# alone exits 0 for `Test-Path missing` (the cmdlet succeeded, it printed False), so a proof that checks a file
# would pass without the file. Here the last statement decides, like bash: an explicit `exit N` is kept, a failed
# last statement exits with the native exit code (or 1), and a last output of $false exits 1. Out-String -Stream
# renders objects as the console would (Get-Location, Get-Item), since a redirected pwsh prints nothing for them.
_PS_WRAPPER = (
    "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8\n"
    "if ($PSStyle) { $PSStyle.OutputRendering = 'PlainText' }\n"
    "$global:LASTEXITCODE = 0; $global:__crewOk = $true; $global:__crewLast = $null\n"
    ". {\n%s\n$global:__crewOk = $?\n} | ForEach-Object { $global:__crewLast = $_; $_ } | Out-String -Stream\n"
    "if (-not $global:__crewOk) { if ($global:LASTEXITCODE) { exit $global:LASTEXITCODE }; exit 1 }\n"
    "if ($global:__crewLast -is [bool] -and -not $global:__crewLast) { exit 1 }\n"
    "exit 0")


def _floors(cmd, mode):
    """Hermes's floors for `mode`: hardline and approvals.deny always, flagged and tirith in safe mode."""
    try:
        _hermes()
        from tools.approval_detection import detect_dangerous_command, detect_hardline_command
        from tools.approval_floors import _match_user_deny_rule
    except Exception as exc:  # noqa: BLE001
        return False, "Hermes's safety checks could not be loaded (%s: %s), so the proof does not run" % (
            type(exc).__name__, exc)
    try:
        hard, why = detect_hardline_command(cmd)
        if hard:
            return False, "hardline (never runs, even in brave mode): %s" % why
        rule = _match_user_deny_rule(cmd)
        if rule:
            return False, "matches your approvals.deny rule '%s' (never runs, even in brave mode)" % rule
        if mode in ("brave", APPROVED):
            return True, ""
        flagged, key, desc = detect_dangerous_command(cmd)
        if flagged and not _permanently_approved(key, cmd):
            return False, "flagged by Hermes as dangerous: %s" % desc
        tirith = _tirith_block(cmd)
        if tirith:
            return False, tirith
    except Exception as exc:  # noqa: BLE001 - a detector that crashes has not cleared the command
        return False, "Hermes's safety check failed (%s: %s), so the proof does not run" % (type(exc).__name__, exc)
    return True, ""


def check_proof(cmd, mode="safe"):
    """(ok, reason): may this proof command run unattended in `mode`? `reason` is Hermes's own words when not.
    Mode "approved" (the owner said yes to this exact command) skips the flagged/tirith checks like brave,
    never the hardline and deny floors. Safe mode also lints a bare PowerShell cmdlet (the intake's proof-check
    shows it as `flagged:`, so the card is opened with POSIX or a pwsh wrapper); run_proof itself does not refuse
    one, it routes it to PowerShell on Windows."""
    ok, why = _floors(cmd, mode)
    if ok and mode == "safe":
        cmdlet = detect_bare_powershell(cmd)
        if cmdlet:
            return False, POWERSHELL_LINT % cmdlet
    return ok, why


def proof_check(cmd):
    """The intake's pre-ask check, one line: `ok`, `flagged: <Hermes's reason>` (safe mode would stop it) or
    `hardline: <reason>` (never runs, in any mode). Same logic as check_proof, read-only."""
    floor_ok, floor_why = check_proof(cmd, "brave")
    if not floor_ok:
        return "hardline: %s" % floor_why.replace("hardline (never runs, even in brave mode): ", "")
    ok, why = check_proof(cmd, "safe")
    return "ok" if ok else "flagged: %s" % why.replace("flagged by Hermes as dangerous: ", "")


def permanent_mode():
    """"brave" when the crew-coordinator profile's Hermes approvals.mode is off (set for good by
    `/crew-safety brave`), else "safe". The coordinator profile is the one that runs proofs unattended."""
    import crew_card
    mode = crew_card.config_value("mode", section="approvals",
                                  home=crew_card.profile_home(crew_card.role_profile("coordinator")))
    return "brave" if (mode or "").strip().lower() in ("off", "false") else "safe"


def proof_mode(card_id, cmd=None):
    """The mode a card's proof runs in: "brave" when its snapshot records the owner's per-card choice or the
    permanent mode is brave; "approved" when `cmd` is exactly a command the owner approved while Hermes flagged
    it (a hash in the snapshot: any other command, e.g. after a rescope, is not); else "safe"."""
    import crew_card
    if crew_card.proof_snapshot_mode(card_id) == "brave" or permanent_mode() == "brave":
        return "brave"
    if cmd and cmd_hash(cmd) in crew_card.proof_snapshot_approved(card_id):
        return APPROVED
    return "safe"


def script_hashes(cmd):
    """{path: sha256 of its bytes} for every script file the proof command names that exists right now."""
    out = {}
    for path in SCRIPT_RX.findall(str(cmd or "")):
        try:
            with open(_script_file(path), "rb") as fh:
                out[path] = hashlib.sha256(fh.read()).hexdigest()
        except OSError:
            continue
    return out


def script_change(card_id, cmd, record=False):
    """Why this card's proof scripts may not run, '' when they may: a script whose hash differs from the recorded
    one, unless the coordinator authorized a revision (then the new hash is recorded with that reason). With
    `record`, a script not seen before gets its hash recorded now (the first run binds it)."""
    import crew_card
    known = crew_card.proof_script_hashes(card_id)
    now = script_hashes(cmd)
    changed = sorted(p for p, h in now.items() if p in known and known[p] != h)
    why = crew_card.pending_script_authorization(card_id) if changed else ""
    if changed and not why:
        return SCRIPT_CHANGED + ", ".join(changed)
    if record:
        crew_card.record_script_hashes(card_id, {p: h for p, h in now.items() if p not in known or p in changed},
                                       by="verifier" if why else "crew", why=why,
                                       authorized_by=crew_card.decision_id(card_id, "revise_script") if why else None)
    return ""


def is_script_block(reason):
    return str(reason or "").startswith(SCRIPT_CHANGED)


def _resolve_openspec_cwd(change_name):
    import glob

    def _has_change(root):
        if not root or not os.path.isdir(root):
            return False
        if os.path.isdir(os.path.join(root, "openspec", "changes", change_name)):
            return True
        return bool(glob.glob(os.path.join(root, "openspec", "changes", "archive", "*%s*" % change_name)))

    cur_cwd = os.getcwd()
    if _has_change(cur_cwd):
        return cur_cwd

    for src in _find_hermes_sources():
        if _has_change(src):
            return src

    roots = []
    for k in ("HERMES_WORKSPACE_ROOT", "WORKSPACE"):
        v = os.environ.get(k)
        if v and os.path.isdir(v) and v not in roots:
            roots.append(v)

    cur = os.path.abspath(__file__)
    while True:
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
        if cur not in roots:
            roots.append(cur)

    for r in roots:
        if _has_change(r):
            return r
        for path in glob.glob(os.path.join(r, "*", "openspec", "changes", change_name)):
            return os.path.dirname(os.path.dirname(os.path.dirname(path)))
        for path in glob.glob(os.path.join(r, "*", "openspec", "changes", "archive", "*%s*" % change_name)):
            return os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(path))))
        for path in glob.glob(os.path.join(r, "oss", "*", "openspec", "changes", change_name)):
            return os.path.dirname(os.path.dirname(os.path.dirname(path)))
        for path in glob.glob(os.path.join(r, "oss", "*", "openspec", "changes", "archive", "*%s*" % change_name)):
            return os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(path))))

    return None


def run_proof(cmd, cwd=None, timeout=300, mode="safe", card=None):
    """The one runner of a proof command. Result(rc, output, blocked): `blocked` is the reason the safety floor
    (or, with `card`, the card's recorded script hashes) refused it (nothing ran, rc is BLOCKED_RC); rc 124 is a
    timeout, 127 a command that could not start. Every unattended proof comes through here, so the script binding
    lives here and not in one caller. On Windows a proof that runs a bare PowerShell cmdlet (detect_bare_powershell)
    goes to PowerShell instead of Git Bash, which would only answer 127; every other proof runs in bash as before.
    The PowerShell lint in check_proof is the intake's preflight, not a floor: here only Hermes's floors refuse."""
    ok, why = _floors(cmd, mode)
    if ok and card:
        why = script_change(card, cmd, record=True)
        ok = not why
    if not ok:
        return Result(BLOCKED_RC, why, why)
    if cwd is None:
        m = re.search(r"openspec(?:\.cmd)?\s+(?:validate|show|status)\s+([\w-]+)", str(cmd or ""))
        if m:
            change_name = m.group(1)
            resolved = _resolve_openspec_cwd(change_name)
            if resolved:
                cwd = resolved
        else:
            cur_cwd = os.getcwd()
            words = []
            for part in re.split(r"[\s|&;]+", str(cmd or "")):
                part = part.strip("\"'()[]{}<>,")
                if ("/" in part or "\\" in part) and not part.startswith("-"):
                    words.append(part)
            for m in re.finditer(r"([a-zA-Z0-9_.-]+(?:[/\\\\][a-zA-Z0-9_.-]+)+)", str(cmd or "")):
                part = m.group(1).strip()
                if part and not part.startswith("-"):
                    words.append(part)
            if words and not any(os.path.exists(os.path.join(cur_cwd, w)) for w in words):
                roots = []
                for k in ("HERMES_WORKSPACE_ROOT", "WORKSPACE"):
                    v = os.environ.get(k)
                    if v and os.path.isdir(v) and v not in roots:
                        roots.append(v)
                cur = os.path.abspath(__file__)
                while True:
                    parent = os.path.dirname(cur)
                    if parent == cur:
                        break
                    cur = parent
                    if cur not in roots:
                        roots.append(cur)
                for r in roots:
                    if any(os.path.exists(os.path.join(r, w)) for w in words):
                        cwd = r
                        break
    argv = cmd
    stdin = None
    if IS_WINDOWS and detect_bare_powershell(cmd):
        argv = [_powershell(), "-NoProfile", "-NonInteractive", "-Command", _PS_WRAPPER % cmd]
        stdin = subprocess.DEVNULL                   # -NonInteractive: a prompt fails instead of waiting for nobody
    elif IS_WINDOWS:
        # A proof is bash. cmd.exe reads `echo hi; exit 3`, `sleep` and `rm` differently, and a safety check that
        # judged the bash text would then guard something other than what runs.
        bash = git_bash()
        if not bash:
            return Result(127, "Git Bash was not found next to git.exe: crew proofs run in Git Bash on Windows "
                               "(install Git for Windows); the proof was not run", "")
        argv = [bash, "-c", cmd]
    try:
        done = subprocess.run(argv, shell=not IS_WINDOWS, capture_output=True, text=True, timeout=timeout, cwd=cwd,
                              env=proof_env(), encoding="utf-8", errors="replace", stdin=stdin)
        return Result(done.returncode, (done.stdout or "") + (done.stderr or ""), "")
    except subprocess.TimeoutExpired:
        return Result(124, "proof command timed out after %ss" % timeout, "")
    except OSError as exc:
        return Result(127, str(exc), "")

"""OpenSpec governance gates for crew cards: one module the plugin hooks (__init__.py) and the native tools
(native_tools.py) share.

  load_openspec_evaluator()  the authoritative `evaluate_change_gate` from the OpenSpec plugin (never a copy)
  parent_fence()             no Apply (writer) card pre-chained under an unapproved review (verifier) card
  ownership_fence()          an `openspec/changes/<change>` input must live under the target repo's openspec/ root
  verify_close_gate()        a `Verify: dual` card linked to a change closes only when the change passes `verify_close`
  block_rejected_children()  a verifier card completed with a REJECTED verdict blocks its todo/ready children

Every gate takes the loaded scripts/crew_card.py module (`tool`) for board access, so this module opens no board of
its own choosing. A gate that cannot decide fails closed with the exact reason.
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import sqlite3
import time
from pathlib import Path
from typing import Any, Callable, Optional

REJECTED_VERDICT_RX = re.compile(r"\bverdict\b[\s:*`'\"=\-]*(?:is\s+)?REJECTED\b", re.I)
APPROVED_VERDICT_RX = re.compile(r"\bverdict\b[\s:*`'\"=\-]*(?:is\s+)?APPROVED\b", re.I)
_ABS_CHANGE_RX = re.compile(r"((?:[A-Za-z]:)?/[^\s`'\"<>|]*?)/openspec/changes/(?:archive/)?([A-Za-z0-9._-]+)")
_REL_CHANGE_RX = re.compile(r"(?<![\w/.:-])openspec/changes/(?:archive/)?([A-Za-z0-9._-]+)")
_CROSS_REPO_RX = re.compile(r"^\s*x-crossRepo\s*:\s*true\s*$", re.I | re.M)
_ABS_PATH_RX = re.compile(r"(?:[A-Za-z]:)?/[^\s`'\"<>|]+")
WRITER_ROLES = ("worker", "content")
_ARTIFACT_MAX = 512 * 1024


# ---------------------------------------------------------------- evaluator


def load_openspec_evaluator(home: Optional[str] = None) -> Optional[Callable[..., dict]]:
    """`evaluate_change_gate` from the OpenSpec plugin's own artifacts_index.py, or None (callers fail closed).

    Search order: HERMES_OPENSPEC_PLUGIN_DIR, $HERMES_HOME/plugins/openspec, then the openspec plugin next to
    this one (<plugins>/crew -> <plugins>/openspec)."""
    candidates = []
    env_dir = (os.environ.get("HERMES_OPENSPEC_PLUGIN_DIR") or "").strip()
    if env_dir:
        candidates.append(Path(env_dir) / "artifacts_index.py")
    home = home or os.environ.get("HERMES_HOME") or ""
    if home:
        candidates.append(Path(home) / "plugins" / "openspec" / "artifacts_index.py")
    candidates.append(Path(__file__).resolve().parent.parent / "openspec" / "artifacts_index.py")
    for path in candidates:
        if not path.is_file():
            continue
        try:
            spec = importlib.util.spec_from_file_location("crew_openspec_artifacts_index", str(path))
            if spec is None or spec.loader is None:
                continue
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
        except Exception:  # noqa: BLE001 - a broken candidate is skipped; none left means fail closed
            continue
        fn = getattr(mod, "evaluate_change_gate", None)
        if callable(fn):
            return fn
    return None


# ---------------------------------------------------------------- paths


def _norm(text: Any) -> str:
    return str(text or "").replace("\\", "/")


def _same_path(a: str, b: str) -> bool:
    return os.path.normcase(os.path.normpath(a)) == os.path.normcase(os.path.normpath(b))


def owning_repo(repo_path: str) -> str:
    """Canonical repository root owning `repo_path` (resolves a git worktree's `.git` file via `gitdir`/`commondir`)."""
    if not repo_path:
        return ""
    p = Path(repo_path)
    dot_git = p / ".git"
    try:
        if dot_git.is_file():
            raw = dot_git.read_text(encoding="utf-8", errors="replace").splitlines()
            gitdir_line = next((ln for ln in raw if ln.lower().startswith("gitdir:")), "")
            if gitdir_line:
                gitdir = Path(gitdir_line.split(":", 1)[1].strip())
                if not gitdir.is_absolute():
                    gitdir = (p / gitdir).resolve()
                commondir_file = gitdir / "commondir"
                if commondir_file.is_file():
                    common = Path(commondir_file.read_text(encoding="utf-8", errors="replace").strip())
                    common_dir = common if common.is_absolute() else (gitdir / common).resolve()
                    if common_dir.name == ".git":
                        return str(common_dir.parent)
                if gitdir.parent.name == "worktrees" and gitdir.parent.parent.name == ".git":
                    return str(gitdir.parent.parent.parent)
    except OSError:
        pass
    return str(p)


def target_repo(path_text: Any) -> str:
    """The git checkout (repository or worktree) that contains the first absolute path in `path_text`, or ''."""
    m = _ABS_PATH_RX.search(_norm(path_text))
    if not m:
        return ""
    p = Path(m.group(0).rstrip(".,;)"))
    for cand in [p] + list(p.parents):
        if (cand / ".git").exists():
            return str(cand)
    return ""


def change_refs(text: Any, base_repo: str = "") -> list[tuple[str, str]]:
    """(openspec owner root, change name) for each `openspec/changes/<change>` reference in `text`.
    A relative reference resolves against `base_repo` and is skipped when there is none."""
    norm = _norm(text)
    refs: list[tuple[str, str]] = []
    for m in _ABS_CHANGE_RX.finditer(norm):
        ref = (m.group(1), m.group(2).rstrip("."))
        if ref[1] and ref[1] != "archive" and ref not in refs:
            refs.append(ref)
    if base_repo:
        for m in _REL_CHANGE_RX.finditer(norm):
            ref = (_norm(base_repo), m.group(1).rstrip("."))
            if ref[1] and ref[1] != "archive" and ref not in refs:
                refs.append(ref)
    return refs


def is_cross_repo(root: str, change: str) -> bool:
    """`.openspec.yaml` of the change declares `x-crossRepo: true` (live or archived change folder)."""
    changes = Path(root) / "openspec" / "changes"
    folders = [changes / change]
    archive = changes / "archive"
    if archive.is_dir():
        folders += [d for d in archive.iterdir() if d.is_dir() and (d.name == change or d.name.endswith("-" + change))]
    for folder in folders:
        try:
            if _CROSS_REPO_RX.search((folder / ".openspec.yaml").read_text(encoding="utf-8")):
                return True
        except OSError:
            continue
    return False


# ---------------------------------------------------------------- board reads


def _card_row(tool: Any, card_id: str) -> Optional[tuple]:
    db = tool.kanban_db() if tool is not None else None
    if not db or not card_id:
        return None
    rows = tool.q_db(db, "select status, body, result from tasks where id = ?", (card_id,))
    return rows[0] if rows else None


def _artifact_text(tool: Any, body: str) -> str:
    """Contents of the card's declared `Artifact:` file(s) (absolute paths + relative paths under `Lands at`, capped)."""
    candidates: list[Path] = []
    base_dirs: list[Path] = []
    for key in ("Artifact", "Lands at"):
        for m in _ABS_PATH_RX.finditer(_norm(tool.field(body, key) or "")):
            p = Path(m.group(0).rstrip(".,;)"))
            if p.is_file() and p not in candidates:
                candidates.append(p)
            elif key == "Lands at" and p.is_dir() and p not in base_dirs:
                base_dirs.append(p)
    art_raw = _norm(tool.field(body, "Artifact") or "").strip().strip("`'\"")
    if art_raw and not _ABS_PATH_RX.match(art_raw) and ".." not in Path(art_raw).parts:
        for bdir in base_dirs:
            rel_target = bdir / art_raw
            if rel_target.is_file() and rel_target not in candidates:
                candidates.append(rel_target)
    out = []
    for p in candidates:
        try:
            out.append(p.read_bytes()[:_ARTIFACT_MAX].decode("utf-8", "replace"))
        except OSError:
            pass
    return "\n".join(out)


def verifier_verdict(tool: Any, card_id: str, body: str, summary: str = "", result: str = "",
                     rejected_rx: re.Pattern = REJECTED_VERDICT_RX) -> str:
    """"REJECTED", "APPROVED" or "" for a review card: its completion summary, stored result, newest run summary
    and declared artifact file(s). REJECTED anywhere wins."""
    texts = [summary or "", result or ""]
    db = tool.kanban_db() if tool is not None else None
    if db and card_id:
        texts += [r[0] or "" for r in tool.q_db(
            db, "select summary from task_runs where task_id = ? order by id desc limit 1", (card_id,))]
    texts.append(_artifact_text(tool, body))
    blob = "\n".join(texts)
    if rejected_rx.search(blob):
        return "REJECTED"
    if APPROVED_VERDICT_RX.search(blob):
        return "APPROVED"
    return ""


def is_review_card(tool: Any, body: str) -> bool:
    return (tool.field(body, "Role") or "").strip().lower() == "verifier" and tool.verify_mode(body) == "agent"


# ---------------------------------------------------------------- gates


def parent_fence(tool: Any, role: Any, parents: Any) -> Optional[str]:
    """Refusal text when a writer (Apply) card is chained under a review card that is not done with APPROVED."""
    if str(role or "").strip().lower() not in WRITER_ROLES or not parents:
        return None
    if isinstance(parents, str):
        parents = [parents]
    for pid in [str(p).strip() for p in parents if str(p).strip()]:
        row = _card_row(tool, pid)
        if row is None:
            continue
        status, pbody, presult = row[0] or "", row[1] or "", row[2] or ""
        if not is_review_card(tool, pbody):
            continue
        verdict = verifier_verdict(tool, pid, pbody, result=presult)
        if status in ("done", "archived") and verdict == "APPROVED":
            continue
        return ("a %s (Apply) card cannot be chained under review card %s (status %s, verdict %s): open Apply "
                "cards only after the Proposal Review is APPROVED and the Commander passes the Phase Approval Gate"
                % (role, pid, status or "?", verdict or "none"))
    return None


def ownership_fence(inputs: Any, lands: Any) -> Optional[str]:
    """Refusal text when `Inputs:` / `Lands at:` names an OpenSpec change outside the target repo's openspec/
    root while that repo owns openspec/specs/ (unless the change sets `x-crossRepo: true`)."""
    repo = target_repo(lands)
    owner = owning_repo(repo)
    if not owner or not (Path(owner) / "openspec" / "specs").is_dir():
        return None
    for root, change in change_refs("%s\n%s" % (inputs or "", lands or ""), base_repo=owner):
        root_owner = owning_repo(target_repo(root) or root)
        if _same_path(root, owner) or _same_path(root, repo) or (root_owner and _same_path(root_owner, owner)) or is_cross_repo(root, change):
            continue
        return ("OPENSPEC_ROOT ownership mismatch: change `%s` lives under %s/openspec but the target repository "
                "%s owns its own openspec/specs/; move the change there or set `x-crossRepo: true` in its "
                ".openspec.yaml" % (change, root, _norm(owner)))
    return None


def verify_close_gate(tool: Any, body: str, evaluator: Optional[Callable[..., dict]] = None, *,
                      loader: Optional[Callable[[], Optional[Callable[..., dict]]]] = None) -> Optional[str]:
    """Refusal text when a `Verify: dual` card references an OpenSpec change that fails `verify_close`.
    `loader` is called only when the card references a change (the evaluator is loaded lazily)."""
    if tool is None or tool.verify_mode(body) != "dual":
        return None
    lands = tool.field(body, "Lands at") or ""
    refs = change_refs("%s\n%s" % (tool.contract_inputs(body), lands), base_repo=target_repo(lands))
    if not refs:
        return None
    if evaluator is None:
        evaluator = loader() if loader is not None else load_openspec_evaluator()
    if evaluator is None:
        return ("the OpenSpec evaluator (openspec plugin artifacts_index.evaluate_change_gate) is unavailable, so "
                "the verify_close gate cannot pass; install the openspec plugin")
    for root, change in refs:
        try:
            res = evaluator(root, change, "verify_close")
        except Exception as exc:  # noqa: BLE001 - an evaluator error never lets a card close
            return "the OpenSpec verify_close gate failed for `%s` (%s)" % (change, exc)
        if not (isinstance(res, dict) and res.get("allowed") is True):
            missing = ", ".join((res or {}).get("missing") or ["unknown"]) if isinstance(res, dict) else "unknown"
            return ("OpenSpec change `%s` fails verify_close (missing: %s). Record an APPROVED verification review "
                    "under openspec/changes/%s/reviews/ and complete every task in tasks.md first"
                    % (change, missing, change))
    return None


def _block_rows(tool: Any, children: list[str], reason: str, parent: str) -> list[str]:
    """todo/ready children -> blocked (kind needs_input, sticky `blocked` event). The kernel's block_task first;
    a `todo` card it refuses is moved in the kernel's own write transaction."""
    blocked: list[str] = []
    payload = {"reason": reason, "kind": "needs_input", "rejected_parent": parent}
    try:
        kb, conn = tool.kb_conn()
    except Exception:  # noqa: BLE001 - no hermes_cli here: the same rows by plain sqlite
        kb, conn = None, None
    if kb is not None:
        try:
            for cid in children:
                ok = False
                try:
                    ok = kb.block_task(conn, cid, reason=reason, kind="needs_input")
                except Exception:  # noqa: BLE001
                    ok = False
                if not ok:
                    with kb.write_txn(conn):
                        n = conn.execute("update tasks set status = 'blocked', block_kind = 'needs_input', "
                                         "block_recurrences = 1 where id = ? and status in ('todo', 'ready')",
                                         (cid,)).rowcount
                        if n == 1:
                            kb._append_event(conn, cid, "blocked", payload)
                            ok = True
                if ok:
                    blocked.append(cid)
        finally:
            conn.close()
        return blocked
    db = tool.kanban_db()
    if not db:
        return blocked
    raw = sqlite3.connect(db, timeout=10)
    try:
        for cid in children:
            n = raw.execute("update tasks set status = 'blocked' where id = ? and status in ('todo', 'ready')",
                            (cid,)).rowcount
            if n == 1:
                raw.execute("insert into task_events (task_id, run_id, kind, payload, created_at) values (?,?,?,?,?)",
                            (cid, None, "blocked", json.dumps(payload), int(time.time())))
                blocked.append(cid)
        raw.commit()
    finally:
        raw.close()
    return blocked


def block_rejected_children(tool: Any, card_id: str, summary: str = "",
                            rejected_rx: re.Pattern = REJECTED_VERDICT_RX) -> list[str]:
    """After `kanban_complete` on a verifier card whose verdict is REJECTED: block its todo/ready children."""
    row = _card_row(tool, card_id)
    if row is None or row[0] not in ("done", "archived"):
        return []
    body, result = row[1] or "", row[2] or ""
    if (tool.field(body, "Role") or "").strip().lower() != "verifier":
        return []
    if verifier_verdict(tool, card_id, body, summary=summary, result=result, rejected_rx=rejected_rx) != "REJECTED":
        return []
    db = tool.kanban_db()
    children = [r[0] for r in tool.q_db(
        db, "select t.id from task_links l join tasks t on t.id = l.child_id "
            "where l.parent_id = ? and t.status in ('todo', 'ready') order by t.id", (card_id,))]
    if not children:
        return []
    reason = ("parent review card %s completed with Verdict: REJECTED; remediate and re-review before this card "
              "runs" % card_id)
    return _block_rows(tool, children, reason, card_id)


def _parse_inline_yaml_list(inline: str, section: str) -> list[str]:
    if not (inline.startswith("[") and inline.endswith("]")):
        raise AssertionError(f"unsupported inline plugins.{section} value: {inline!r}")
    body = inline[1:-1].strip()
    if not body:
        return []
    items: list[str] = []
    for raw_item in body.split(","):
        token = raw_item.strip()
        if not token:
            raise AssertionError(f"malformed empty element in plugins.{section}: {inline!r}")
        if (token.startswith('"') and token.endswith('"')) or (token.startswith("'") and token.endswith("'")):
            token = token[1:-1].strip()
        elif any(ch in token for ch in ("[", "]", "{", "}", ":")):
            raise AssertionError(f"unsupported nested token in plugins.{section}: {inline!r}")
        if not token:
            raise AssertionError(f"empty plugin name in plugins.{section}: {inline!r}")
        items.append(token)
    return items


def _parse_plugins_cfg(cfg_path: Path) -> tuple[list[str], list[str] | None]:
    """Deterministically parse plugins.disabled and plugins.enabled from config.yaml (stdlib only, fail-closed)."""
    if not cfg_path.is_file():
        raise AssertionError(f"missing config.yaml: {cfg_path}")
    text = cfg_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    in_plugins = False
    plugins_indent = 0
    section: str | None = None
    section_indent = 0
    dis: list[str] = []
    en: list[str] | None = None

    for line in lines:
        raw = line.rstrip("\r\n")
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" \t"))
        if not in_plugins:
            m_top = re.match(r"^plugins:\s*(.*?)\s*(#.*)?$", raw)
            if m_top:
                rest = m_top.group(1).strip()
                if rest and rest not in ("{}",):
                    raise AssertionError(f"invalid inline plugins block in {cfg_path}: {rest!r}")
                in_plugins = True
                plugins_indent = indent
                section = None
            continue

        if indent <= plugins_indent:
            in_plugins = False
            section = None
            continue

        if section is not None and indent >= section_indent:
            m_item = re.match(r"^\s*-\s+(.+?)\s*(#.*)?$", raw)
            if m_item:
                val = m_item.group(1).strip().strip("'\"")
                if not val:
                    raise AssertionError(f"empty item in plugins.{section} of {cfg_path}")
                if section == "disabled":
                    dis.append(val)
                elif en is not None:
                    en.append(val)
                continue
            if indent > section_indent:
                raise AssertionError(f"malformed entry under plugins.{section} in {cfg_path}: {raw!r}")
            section = None

        m_sec = re.match(r"^\s+(disabled|enabled):\s*(.*?)\s*(#.*)?$", raw)
        if m_sec:
            sec_name = str(m_sec.group(1))
            section = sec_name
            section_indent = indent
            inline = m_sec.group(2).strip()
            if sec_name == "enabled" and en is None:
                en = []
            if inline:
                parsed_items = _parse_inline_yaml_list(inline, sec_name)
                if sec_name == "disabled":
                    dis.extend(parsed_items)
                elif en is not None:
                    en.extend(parsed_items)
                section = None
            continue

        if not re.match(r"^\s+[A-Za-z0-9_.-]+:\s*(.*?)\s*(#.*)?$", raw):
            raise AssertionError(f"malformed line inside plugins block of {cfg_path}: {raw!r}")

    return dis, en


def verify_seven_profile_plugin_parity(
    hermes_home: str | Path | None = None,
    *,
    required_plugins: tuple[str, ...] = ("nerve", "crew", "openspec"),
    specialist_profiles: tuple[str, ...] = ("coder", "reviewer", "qa", "leader", "designer", "researcher"),
) -> dict[str, Any]:
    """Verify 7-root directory presence, config.yaml enablement, and SHA-256 (.py/.yaml) manifest parity."""
    import hashlib

    base_raw = hermes_home or os.environ.get("HERMES_HOME")
    if not base_raw:
        raise AssertionError("hermes_home or HERMES_HOME is required")
    base = Path(base_raw).resolve()
    roots = [("default", base / "plugins", base / "config.yaml")] + [
        (p, base / "profiles" / p / "plugins", base / "profiles" / p / "config.yaml")
        for p in specialist_profiles
    ]

    def _manifest(pdir: Path) -> dict[str, str]:
        return {
            f.relative_to(pdir).as_posix(): hashlib.sha256(f.read_bytes()).hexdigest()
            for f in sorted(pdir.rglob("*"))
            if f.is_file() and "__pycache__" not in f.parts and f.suffix in (".py", ".yaml")
        }

    ref: dict[str, dict[str, str]] = {}
    for pl in required_plugins:
        default_pl = roots[0][1] / pl
        if not (default_pl / "__init__.py").is_file() or not (default_pl / "plugin.yaml").is_file():
            raise AssertionError(f"default:{pl}: missing __init__.py or plugin.yaml")
        mf = _manifest(default_pl)
        if not mf:
            raise AssertionError(f"default:{pl}: empty manifest")
        ref[pl] = mf

    for name, rdir, cfg_path in roots:
        if not cfg_path.is_file():
            raise AssertionError(f"{name}: missing config.yaml at {cfg_path}")
        disabled, enabled = _parse_plugins_cfg(cfg_path)
        for pl in required_plugins:
            pdir = rdir / pl
            if not (pdir / "__init__.py").is_file() or not (pdir / "plugin.yaml").is_file():
                raise AssertionError(f"{name}:{pl}: missing plugin directory or entrypoint")
            if pl in disabled:
                raise AssertionError(f"{name}:{pl}: listed in plugins.disabled")
            if enabled is not None and pl not in enabled:
                raise AssertionError(f"{name}:{pl}: missing from plugins.enabled")
            cur = _manifest(pdir)
            if cur != ref[pl]:
                raise AssertionError(f"{name}:{pl}: SHA-256 manifest mismatch vs default")

    return {
        "ok": True,
        "roots": [r[0] for r in roots],
        "plugins": list(required_plugins),
        "file_counts": {pl: len(ref[pl]) for pl in required_plugins},
    }

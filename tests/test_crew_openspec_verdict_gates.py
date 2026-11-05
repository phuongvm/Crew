#!/usr/bin/env python3
"""Real OpenSpec evaluator and real Hermes Kanban-kernel proofs for the Crew verdict gates."""
from __future__ import annotations

import importlib.util
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PROOF_OK_CMD = f'"{sys.executable}" -c "raise SystemExit(0)"'

os.environ.setdefault("HERMES_BIN", os.path.join(tempfile.gettempdir(), "hermes-unit-test-stub"))
for _dir in (str(REPO / "scripts"), str(REPO / "tests")):
    if _dir not in sys.path:
        sys.path.insert(0, _dir)
import crew_card  # noqa: E402
import kernel_board  # noqa: E402


def load_plugin():
    spec = importlib.util.spec_from_file_location("crew_openspec_gates_plugin", str(REPO / "__init__.py"))
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_native_tools():
    spec = importlib.util.spec_from_file_location("crew_openspec_gates_native", str(REPO / "native_tools.py"))
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _has_real_evaluator(plugin_dir: Path) -> bool:
    idx = plugin_dir / "artifacts_index.py"
    if not idx.is_file():
        return False
    try:
        return "def evaluate_change_gate" in idx.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False


def _discover_real_openspec_plugin_dir(orig_env: dict[str, str]) -> Path | None:
    """Resolve the real OpenSpec plugin directory from env or relative sibling checkouts without host literals."""
    candidates: list[Path] = []
    explicit = (orig_env.get("HERMES_OPENSPEC_PLUGIN_DIR") or "").strip()
    if explicit:
        candidates.append(Path(explicit))
    candidates.append(REPO.parent / "wt-openspec-hard-gates")
    candidates.append(REPO.parent / "hermes-openspec")
    orig_home = (orig_env.get("HERMES_HOME") or "").strip()
    if orig_home:
        candidates.append(Path(orig_home) / "plugins" / "openspec")
    for cand in candidates:
        if _has_real_evaluator(cand):
            return cand
    return None


class CrewOpenSpecVerdictGateTests(unittest.TestCase):
    def setUp(self):
        self.env = dict(os.environ)
        self.tmp = tempfile.mkdtemp(prefix="crew-openspec-gates-")
        self.real_openspec_dir = _discover_real_openspec_plugin_dir(self.env)
        os.environ["HERMES_HOME"] = self.tmp
        if self.real_openspec_dir is not None:
            os.environ["HERMES_OPENSPEC_PLUGIN_DIR"] = str(self.real_openspec_dir)
        else:
            os.environ.pop("HERMES_OPENSPEC_PLUGIN_DIR", None)
        for key in ("HERMES_KANBAN_TASK", "HERMES_SESSION_PLATFORM", "HERMES_SESSION_SOURCE"):
            os.environ.pop(key, None)
        self.kb, self.conn, self.db = kernel_board.open_board(self.tmp)
        self.plugin = load_plugin()
        self.native = load_native_tools()

    def tearDown(self):
        self.conn.close()
        os.environ.clear()
        os.environ.update(self.env)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def review_body(self, *, artifact: str = "review.md", lands: Path | None = None) -> str:
        target = (lands or (Path(self.tmp) / "review.md")).as_posix()
        return (
            "Role: verifier\n"
            "Verify: agent\n"
            "Coordinator: owner/session\n"
            "Budget: 200000 tokens\n\n"
            "GOAL: Review proposal\n"
            f"Artifact: {artifact}\n"
            f"Lands at: {target}\n"
            "For: commander\n"
            "Done when: verdict recorded\n"
            f"proof command: {PROOF_OK_CMD}\n"
        )

    def worker_body(self, *, lands: Path | None = None) -> str:
        target = (lands or (Path(self.tmp) / "out.txt")).as_posix()
        return (
            "Role: worker\n"
            "Verify: proof\n"
            "Coordinator: owner/session\n"
            "Budget: 200000 tokens\n\n"
            "GOAL: Implement feature\n"
            "Artifact: out.txt\n"
            f"Lands at: {target}\n"
            "For: commander\n"
            "Done when: test passes\n"
            f"proof command: {PROOF_OK_CMD}\n"
        )

    def _make_sample_openspec_change(self, slug: str = "sample-gate-change") -> tuple[Path, Path]:
        project_root = Path(self.tmp) / "sample-project"
        change_dir = project_root / "openspec" / "changes" / slug
        (change_dir / "specs" / "sample-cap").mkdir(parents=True)
        (change_dir / "reviews").mkdir(parents=True)
        (change_dir / "proposal.md").write_text("# Proposal\n\nEnforce sample gate.\n", encoding="utf-8")
        (change_dir / "design.md").write_text("# Design\n\nSample design.\n", encoding="utf-8")
        (change_dir / "specs" / "sample-cap" / "spec.md").write_text(
            "## ADDED Requirements\n\n### Requirement: Sample Gate\nThe system SHALL enforce the gate.\n\n"
            "#### Scenario: Gate enforced\n- WHEN checked\n- THEN it blocks invalid state\n",
            encoding="utf-8",
        )
        (change_dir / "tasks.md").write_text("- [ ] 1.1 Implement gate\n", encoding="utf-8")
        (change_dir / "reviews" / "findings-proposal-v1.md").write_text(
            "# Proposal Review\n\nVerdict: APPROVED\n",
            encoding="utf-8",
        )
        return project_root, change_dir

    def _require_real_openspec_dir(self) -> Path:
        if self.real_openspec_dir is None:
            self.skipTest("real hermes-openspec plugin checkout not found; set HERMES_OPENSPEC_PLUGIN_DIR")
        return self.real_openspec_dir

    def test_shared_gates_module_is_not_duplicated(self):
        self.assertIs(self.plugin._gates(), self.native._openspec_gates())

    def test_loader_executes_real_hard_gates_evaluator(self):
        real_dir = self._require_real_openspec_dir()
        evaluator = self.plugin._load_openspec_evaluator()
        self.assertTrue(callable(evaluator))
        self.assertEqual(
            Path(evaluator.__code__.co_filename).resolve(),
            (real_dir / "artifacts_index.py").resolve(),
        )

        project_root, change_dir = self._make_sample_openspec_change()
        blocked = evaluator(project_root, change_dir.name, "verify_close")
        self.assertFalse(blocked["allowed"])
        self.assertIn("tasks_incomplete", blocked["missing"])
        self.assertIn("verification_review_missing", blocked["missing"])

        (change_dir / "tasks.md").write_text("- [x] 1.1 Implement gate\n", encoding="utf-8")
        (change_dir / "reviews" / "findings-verify-v1.md").write_text(
            "# Verification Review\n\nVerdict: APPROVED\n",
            encoding="utf-8",
        )
        passed = evaluator(project_root, change_dir.name, "verify_close")
        self.assertTrue(passed["allowed"])
        self.assertEqual(passed["missing"], [])

    def test_create_guard_rejects_apply_child_of_unapproved_verifier(self):
        parent = kernel_board.add_card(self.conn, status="ready", body=self.review_body(), title="proposal review")
        self.plugin.crew_intake_preload(user_message="/crew implement", session_id="S", turn_id="T")
        verdict = self.plugin.crew_tool_guard(
            tool_name="kanban_create",
            args={"title": "apply", "assignee": "crew-worker", "body": self.worker_body(), "parents": [parent]},
            session_id="S",
            turn_id="T",
        )
        self.assertEqual(verdict["action"], "block")
        self.assertIn("cannot be chained", verdict["message"])
        self.assertIn(parent, verdict["message"])

    def test_native_create_handler_enforces_same_parent_fence(self):
        parent = kernel_board.add_card(self.conn, status="ready", body=self.review_body(), title="proposal review")
        result = self.native.handle_crew_card_create({
            "title": "apply",
            "role": "worker",
            "goal": "implement",
            "artifact": "out.txt",
            "lands": (Path(self.tmp) / "out.txt").as_posix(),
            "audience": "commander",
            "done_when": "test passes",
            "proof_cmd": PROOF_OK_CMD,
            "parents": [parent],
            "dry_run": True,
        })
        self.assertEqual(result["status"], "refused")
        self.assertIn("cannot be chained", result["error"])

    def test_native_plan_split_enforces_same_parent_fence(self):
        parent = kernel_board.add_card(self.conn, status="ready", body=self.review_body(), title="proposal review")
        result = self.native.handle_crew_plan_split({
            "goal": "implement",
            "children": [{
                "title": "apply",
                "role": "worker",
                "goal": "implement",
                "artifact": "out.txt",
                "lands": (Path(self.tmp) / "out.txt").as_posix(),
                "audience": "commander",
                "done_when": "test passes",
                "proof_cmd": PROOF_OK_CMD,
                "parents": [parent],
            }],
            "dry_run": True,
        })
        self.assertEqual(result["status"], "refused")
        self.assertIn("cannot be chained", result["error"])

    def test_failed_verifier_completion_does_not_block_child(self):
        parent = kernel_board.add_card(self.conn, status="ready", body=self.review_body(), title="proposal review")
        child = kernel_board.add_card(self.conn, status="todo", body=self.worker_body(), title="apply", parents=(parent,))
        events_before = kernel_board.events(self.conn, child)
        self.plugin.crew_open_hook(
            tool_name="kanban_complete",
            args={"task_id": parent, "summary": "Verdict: REJECTED"},
            result={"status": "error", "error": "completion refused"},
        )
        self.assertEqual(self.kb.get_task(self.conn, parent).status, "ready")
        self.assertEqual(self.kb.get_task(self.conn, child).status, "todo")
        self.assertEqual(kernel_board.events(self.conn, child), events_before)
        self.assertEqual(self.plugin._gates().block_rejected_children(
            crew_card, parent, summary="Verdict: REJECTED"), [])
        self.assertEqual(self.kb.get_task(self.conn, child).status, "todo")

    def test_rejected_verifier_completion_blocks_ready_child_via_kernel_board(self):
        parent = kernel_board.add_card(self.conn, status="ready", body=self.review_body(), title="proposal review")
        child = kernel_board.add_card(self.conn, status="todo", body=self.worker_body(), title="apply", parents=(parent,))
        self.assertTrue(self.kb.complete_task(self.conn, parent, result="Verdict: REJECTED", summary="Verdict: REJECTED"))
        self.assertEqual(self.kb.get_task(self.conn, child).status, "ready")  # kernel released it before post-hook

        self.plugin.crew_open_hook(
            tool_name="kanban_complete",
            args={"task_id": parent, "summary": "Verdict: REJECTED"},
            result={"status": "ok"},
        )
        self.assertEqual(self.kb.get_task(self.conn, child).status, "blocked")
        event_kinds = kernel_board.events(self.conn, child)
        self.assertIn("blocked", event_kinds)
        self.kb.recompute_ready(self.conn)
        self.assertEqual(self.kb.get_task(self.conn, child).status, "blocked")

    def test_rejected_artifact_file_blocks_child_when_summary_is_generic(self):
        change_dir = Path(self.tmp) / "change-under-review"
        findings = change_dir / "reviews" / "findings-proposal-v1.md"
        findings.parent.mkdir(parents=True)
        findings.write_text("# Review\n\nVerdict: REJECTED\n", encoding="utf-8")
        rbody = self.review_body(artifact="reviews/findings-proposal-v1.md", lands=change_dir)
        parent = kernel_board.add_card(self.conn, status="ready", body=rbody, title="proposal review")
        child = kernel_board.add_card(self.conn, status="todo", body=self.worker_body(), title="apply", parents=(parent,))
        self.assertTrue(self.kb.complete_task(self.conn, parent, result="Findings recorded", summary="Findings recorded"))
        self.plugin.crew_open_hook(
            tool_name="kanban_complete",
            args={"task_id": parent, "summary": "Findings recorded"},
            result=f'{{"ok": true, "task_id": "{parent}"}}',
        )
        self.assertEqual(self.kb.get_task(self.conn, child).status, "blocked")
        self.kb.recompute_ready(self.conn)
        self.assertEqual(self.kb.get_task(self.conn, child).status, "blocked")

    def test_dual_close_is_blocked_by_real_verify_close_gate_and_fails_closed_when_missing(self):
        self._require_real_openspec_dir()
        _project_root, change_dir = self._make_sample_openspec_change()
        change_posix = change_dir.as_posix()
        body = (
            "Role: worker\n"
            "Verify: dual\n"
            "Coordinator: owner/session\n"
            "Budget: 200000 tokens\n\n"
            "GOAL: Apply OpenSpec change\n"
            "Artifact: out.txt\n"
            f"Lands at: {change_posix}\n"
            "For: commander\n"
            f"Inputs: {change_posix}\n"
            "Done when: verified\n"
            f"proof command: {PROOF_OK_CMD}\n"
        )
        card = kernel_board.add_card(self.conn, status="ready", body=body, title="dual apply")
        verdict = self.plugin._close_guard("kanban_complete", {"task_id": card})
        self.assertEqual(verdict["action"], "block")
        self.assertIn("verify_close", verdict["message"])
        self.assertIn("tasks_incomplete", verdict["message"])

        empty_dir = Path(self.tmp) / "missing-openspec-plugin"
        empty_dir.mkdir(parents=True)
        os.environ["HERMES_OPENSPEC_PLUGIN_DIR"] = str(empty_dir)
        unavailable = self.plugin._close_guard("kanban_complete", {"task_id": card})
        self.assertEqual(unavailable["action"], "block")
        self.assertIn("unavailable", unavailable["message"])

    def test_ownership_fence_rejects_foreign_change_unless_cross_repo(self):
        gates = self.plugin._gates()
        target = Path(self.tmp) / "target"
        foreign = Path(self.tmp) / "foreign"
        (target / ".git").mkdir(parents=True)
        (target / "openspec" / "specs").mkdir(parents=True)
        (foreign / "openspec" / "changes" / "foreign-change").mkdir(parents=True)
        inputs = str(foreign / "openspec" / "changes" / "foreign-change")
        why = gates.ownership_fence(inputs, str(target / "src" / "thing.py"))
        self.assertIn("ownership mismatch", why)

        (foreign / "openspec" / "changes" / "foreign-change" / ".openspec.yaml").write_text(
            "x-crossRepo: true\n", encoding="utf-8"
        )
        self.assertIsNone(gates.ownership_fence(inputs, str(target / "src" / "thing.py")))

        wt = Path(self.tmp) / "wt-target"
        wt.mkdir(parents=True)
        gitdir = target / ".git" / "worktrees" / "wt-target"
        gitdir.mkdir(parents=True)
        (gitdir / "commondir").write_text("../..\n", encoding="utf-8")
        (wt / ".git").write_text(f"gitdir: {gitdir.as_posix()}\n", encoding="utf-8")
        (target / "openspec" / "changes" / "own-change").mkdir(parents=True)
        own_inputs = str(target / "openspec" / "changes" / "own-change")
        self.assertIsNone(gates.ownership_fence(own_inputs, str(wt / "src" / "thing.py")))
        self.assertIn(
            "ownership mismatch",
            gates.ownership_fence(str(Path(self.tmp) / "other" / "openspec" / "changes" / "bad"), str(wt / "src" / "thing.py")),
        )


if __name__ == "__main__":
    unittest.main()

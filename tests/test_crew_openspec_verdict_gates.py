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
HARD_GATES = Path("O:/workspaces/.worktrees/wt-openspec-hard-gates")
CHANGE_ROOT = Path("O:/workspaces/ai_agents/hermes-agent")
CHANGE = "unify-openspec-nerve-crew-kanban-dod-gates"

os.environ.setdefault("HERMES_BIN", "/bin/false")
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "tests"))
import crew_card  # noqa: E402
import kernel_board  # noqa: E402


def load_plugin():
    spec = importlib.util.spec_from_file_location("crew_openspec_gates_plugin", str(REPO / "__init__.py"))
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def load_native_tools():
    spec = importlib.util.spec_from_file_location("crew_openspec_gates_native", str(REPO / "native_tools.py"))
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


REVIEW_BODY = """Role: verifier
Verify: agent
Coordinator: owner/session
Budget: 200000 tokens

GOAL: Review proposal
Artifact: review.md
Lands at: /tmp/review.md
For: commander
Done when: verdict recorded
proof command: true
"""
WORKER_BODY = """Role: worker
Verify: proof
Coordinator: owner/session
Budget: 200000 tokens

GOAL: Implement feature
Artifact: out.txt
Lands at: /tmp/out.txt
For: commander
Done when: test passes
proof command: true
"""


class CrewOpenSpecVerdictGateTests(unittest.TestCase):
    def setUp(self):
        self.env = dict(os.environ)
        self.tmp = tempfile.mkdtemp(prefix="crew-openspec-gates-")
        os.environ["HERMES_HOME"] = self.tmp
        os.environ["HERMES_OPENSPEC_PLUGIN_DIR"] = str(HARD_GATES)
        os.environ.pop("HERMES_KANBAN_TASK", None)
        self.kb, self.conn, self.db = kernel_board.open_board(self.tmp)
        self.plugin = load_plugin()
        self.native = load_native_tools()

    def tearDown(self):
        self.conn.close()
        os.environ.clear()
        os.environ.update(self.env)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_loader_executes_real_hard_gates_evaluator(self):
        evaluator = self.plugin._load_openspec_evaluator()
        self.assertTrue(callable(evaluator))
        self.assertEqual(Path(evaluator.__code__.co_filename).resolve(), (HARD_GATES / "artifacts_index.py").resolve())

        result = evaluator(CHANGE_ROOT, CHANGE, "verify_close")
        self.assertFalse(result["allowed"])
        self.assertIn("tasks_incomplete", result["missing"])
        self.assertIn("verification_review_missing", result["missing"])

    def test_create_guard_rejects_apply_child_of_unapproved_verifier(self):
        parent = kernel_board.add_card(self.conn, status="ready", body=REVIEW_BODY, title="proposal review")
        self.plugin.crew_intake_preload(user_message="/crew implement", session_id="S", turn_id="T")
        verdict = self.plugin.crew_tool_guard(
            tool_name="kanban_create",
            args={"title": "apply", "assignee": "crew-worker", "body": WORKER_BODY, "parents": [parent]},
            session_id="S",
            turn_id="T",
        )
        self.assertEqual(verdict["action"], "block")
        self.assertIn("cannot be chained", verdict["message"])
        self.assertIn(parent, verdict["message"])

    def test_native_create_handler_enforces_same_parent_fence(self):
        parent = kernel_board.add_card(self.conn, status="ready", body=REVIEW_BODY, title="proposal review")
        result = self.native.handle_crew_card_create({
            "title": "apply",
            "role": "worker",
            "goal": "implement",
            "artifact": "out.txt",
            "lands": "/tmp/out.txt",
            "audience": "commander",
            "done_when": "test passes",
            "proof_cmd": "true",
            "parents": [parent],
            "dry_run": True,
        })
        self.assertEqual(result["status"], "refused")
        self.assertIn("cannot be chained", result["error"])

    def test_native_plan_split_enforces_same_parent_fence(self):
        parent = kernel_board.add_card(self.conn, status="ready", body=REVIEW_BODY, title="proposal review")
        result = self.native.handle_crew_plan_split({
            "goal": "implement",
            "children": [{
                "title": "apply",
                "role": "worker",
                "goal": "implement",
                "artifact": "out.txt",
                "lands": "/tmp/out.txt",
                "audience": "commander",
                "done_when": "test passes",
                "proof_cmd": "true",
                "parents": [parent],
            }],
            "dry_run": True,
        })
        self.assertEqual(result["status"], "refused")
        self.assertIn("cannot be chained", result["error"])

    def test_failed_verifier_completion_does_not_block_child(self):
        parent = kernel_board.add_card(self.conn, status="ready", body=REVIEW_BODY, title="proposal review")
        child = kernel_board.add_card(self.conn, status="todo", body=WORKER_BODY, title="apply", parents=(parent,))
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
        parent = kernel_board.add_card(self.conn, status="ready", body=REVIEW_BODY, title="proposal review")
        child = kernel_board.add_card(self.conn, status="todo", body=WORKER_BODY, title="apply", parents=(parent,))
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
        review_body = (
            REVIEW_BODY
            .replace("Artifact: review.md", "Artifact: reviews/findings-proposal-v1.md")
            .replace("Lands at: /tmp/review.md", f"Lands at: {change_dir.as_posix()}")
        )
        parent = kernel_board.add_card(self.conn, status="ready", body=review_body, title="proposal review")
        child = kernel_board.add_card(self.conn, status="todo", body=WORKER_BODY, title="apply", parents=(parent,))
        self.assertTrue(self.kb.complete_task(self.conn, parent, result="Findings recorded", summary="Findings recorded"))
        self.plugin.crew_open_hook(
            tool_name="kanban_complete",
            args={"task_id": parent, "summary": "Findings recorded"},
            result=f'{{"ok": true, "task_id": "{parent}"}}',
        )
        self.assertEqual(self.kb.get_task(self.conn, child).status, "blocked")
        self.kb.recompute_ready(self.conn)
        self.assertEqual(self.kb.get_task(self.conn, child).status, "blocked")

    def test_dual_close_is_blocked_by_real_verify_close_gate(self):
        body = """Role: worker
Verify: dual
Coordinator: owner/session
Budget: 200000 tokens

GOAL: Apply OpenSpec change
Artifact: out.txt
Lands at: O:/workspaces/ai_agents/hermes-agent/openspec/changes/unify-openspec-nerve-crew-kanban-dod-gates
For: commander
Inputs: O:/workspaces/ai_agents/hermes-agent/openspec/changes/unify-openspec-nerve-crew-kanban-dod-gates
Done when: verified
proof command: true
"""
        card = kernel_board.add_card(self.conn, status="ready", body=body, title="dual apply")
        verdict = self.plugin._close_guard("kanban_complete", {"task_id": card})
        self.assertEqual(verdict["action"], "block")
        self.assertIn("verify_close", verdict["message"])
        self.assertIn("tasks_incomplete", verdict["message"])

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

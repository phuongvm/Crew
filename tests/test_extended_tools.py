#!/usr/bin/env python3
"""Tests for the 8 extended Crew native tools (OpenSpec change `crew-extended-tools`).

  1. Core ops          crew_stop_card
  2. Pipeline ops      crew_review_handoff, crew_request_changes, crew_plan_split
  3. Workspace ops     crew_worktree_create, crew_worktree_cleanup
  4. Intelligence ops  crew_flow_graph, crew_lesson_record

Board tests run on a throwaway kanban board made by Hermes's own kernel (tests/kernel_board.py), never the live
one; git tests run on a throwaway repository; lessons go to a scratch HERMES_HOME. Needs the Hermes venv python.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
TESTS = Path(__file__).resolve().parent
for p in (str(REPO), str(REPO / "scripts"), str(TESTS)):
    if p not in sys.path:
        sys.path.insert(0, p)



def _scratch_base():
    """A temp root outside the delegated-child fence (HERMES_DELEGATED_CHILD_CONTEXT): a dispatcher-spawned worker
    may not write boards under its owner's Hermes root, and the fence stays in force for the live board."""
    fence = os.environ.get("HERMES_DELEGATED_CHILD_CONTEXT", "").strip()
    cands = [tempfile.gettempdir(), os.path.join(os.environ.get("LOCALAPPDATA", ""), "Temp"),
             os.path.join(os.path.expanduser("~"), ".crew-test-tmp")]
    for cand in cands:
        if not cand or not os.path.isabs(cand):
            continue
        if fence and fence != "1":
            try:
                Path(cand).resolve().relative_to(Path(fence).resolve())
                continue
            except ValueError:
                pass
        os.makedirs(cand, exist_ok=True)
        return cand
    return tempfile.gettempdir()


SCRATCH = tempfile.mkdtemp(prefix="crew-ext-tools-", dir=_scratch_base())
HOME = os.path.join(SCRATCH, "home")
os.makedirs(HOME, exist_ok=True)

import module_env  # noqa: E402
# The board under test is named by KANBAN_DB only. HERMES_KANBAN_DB stays unset for the module: a dispatcher pins
# it to the live board (which crew_card.kanban_db would read first), and the kernel fences whatever it names.
module_env.pin(globals(), HERMES_HOME=HOME, KANBAN_DB=os.path.join(SCRATCH, "no-board", "kanban.db"),
               HERMES_KANBAN_DB=None, HERMES_KANBAN_BOARD=None, HERMES_BIN=os.path.join(SCRATCH, "no-hermes"))

import contracts  # noqa: E402
import crew_card  # noqa: E402
import crew_lessons  # noqa: E402
import crew_stop  # noqa: E402
import kernel_board as K  # noqa: E402
import hermes_cli  # noqa: E402

# Hermes's root modules (hermes_state, hermes_dir_acl) sit beside the hermes_cli package this python imports; under a
# scratch HERMES_HOME crew_card.hermes_root() names no tree, so the kernel's lazy imports need that root on the path.
_HERMES_SRC = os.path.dirname(os.path.dirname(os.path.abspath(hermes_cli.__file__)))
if _HERMES_SRC not in sys.path:
    sys.path.append(_HERMES_SRC)
import native_tools  # noqa: E402
from native_tools import (  # noqa: E402
    CREW_EXTENDED_TOOLS,
    CREW_NATIVE_TOOLS,
    graph_to_mermaid,
    handle_crew_flow_graph,
    handle_crew_lesson_record,
    handle_crew_plan_split,
    handle_crew_request_changes,
    handle_crew_review_handoff,
    handle_crew_stop_card,
    handle_crew_worktree_cleanup,
    handle_crew_worktree_create,
    parse_worktree_porcelain,
    register_extended_tools,
    worktrees_root_for,
)

EXTENDED = {
    "crew_stop_card", "crew_review_handoff", "crew_request_changes", "crew_plan_split",
    "crew_worktree_create", "crew_worktree_cleanup", "crew_flow_graph", "crew_lesson_record",
}
CORE = {"crew_card_create", "crew_diagnose", "crew_verdict", "crew_status", "crew_event_subscribe"}

PROOF_BODY = ("Role: worker\nCoordinator: owner/s\nVerify: proof\nBudget: 200000 tokens\n\nGOAL: g\nDone when: d\n\n"
              "proof command: true\n")
INDEPENDENT_BODY = PROOF_BODY.replace("Verify: proof", "Verify: independent")


def child(i, **over):
    c = {"title": "child %d" % i, "role": "worker", "goal": "goal %d" % i, "artifact": "file%d.py" % i,
         "lands": ".", "audience": "commander", "done_when": "tests pass", "proof_cmd": "true"}
    c.update(over)
    return c


class Ctx:
    def __init__(self):
        self.tools, self.commands, self.hooks, self.skills = [], [], [], []

    def register_tool(self, name, toolset, schema, handler, description="", **kw):
        self.tools.append({"name": name, "toolset": toolset, "schema": schema, "handler": handler})

    def register_command(self, name, handler, description="", args_hint=""):
        self.commands.append(name)

    def register_skill(self, name, path, description="", frontmatter=None):
        self.skills.append(name)

    def register_hook(self, name, fn):
        self.hooks.append(name)


class BoardCase(unittest.TestCase):
    """A fresh kernel board per test; HERMES_KANBAN_DB points at it."""

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="board-", dir=SCRATCH)
        self.db = os.path.join(self.dir, "kanban.db")
        self.kb = K.kb
        self.conn = K.kbc.connect(Path(self.db))
        self.addCleanup(self.conn.close)
        p = mock.patch.dict(os.environ, {"KANBAN_DB": self.db})
        p.start()
        self.addCleanup(p.stop)
        os.environ.pop("HERMES_KANBAN_DB", None)
        self.assertEqual(os.path.normcase(self.db), os.path.normcase(crew_card.kanban_db() or ""))

    def status(self, cid):
        return self.kb.get_task(self.conn, cid).status


# ============================================================ registration & schemas


class RegistrationTests(unittest.TestCase):
    def test_extended_catalog_has_eight_distinct_tools(self):
        names = [n for n, _, _ in CREW_EXTENDED_TOOLS]
        self.assertEqual(8, len(names))
        self.assertEqual(EXTENDED, set(names))
        self.assertFalse(set(names) & {n for n, _, _ in CREW_NATIVE_TOOLS})

    def test_schemas_are_valid_function_definitions(self):
        for name, schema, handler in CREW_EXTENDED_TOOLS:
            self.assertEqual(name, schema["name"])
            self.assertGreater(len(schema["description"]), 20)
            params = schema["parameters"]
            self.assertEqual("object", params["type"])
            for req in params.get("required", []):
                self.assertIn(req, params["properties"], "%s requires undeclared %s" % (name, req))
            self.assertTrue(callable(handler))
            json.dumps(schema)

    def test_register_extended_tools_under_crew_toolset_with_string_handlers(self):
        ctx = Ctx()
        register_extended_tools(ctx)
        self.assertEqual(EXTENDED, {t["name"] for t in ctx.tools})
        for t in ctx.tools:
            self.assertEqual("crew", t["toolset"])
            out = t["handler"]({})
            self.assertIsInstance(out, str)
            self.assertIn(json.loads(out)["status"], ("error", "refused", "ok", "dry_run"))

    def test_plugin_register_exposes_all_thirteen_tools(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("crew_plugin_ext", str(REPO / "__init__.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        ctx = Ctx()
        mod.register(ctx)
        self.assertEqual(CORE | EXTENDED, {t["name"] for t in ctx.tools})

    def test_manifest_declares_every_tool(self):
        text = (REPO / "plugin.yaml").read_text(encoding="utf-8")
        for name in CORE | EXTENDED:
            self.assertIn("  - %s" % name, text)


# ============================================================ contracts


class ContractHelperTests(unittest.TestCase):
    def test_card_id_and_worktree_name(self):
        self.assertTrue(contracts.is_valid_card_id("t_ab12cd34"))
        self.assertFalse(contracts.is_valid_card_id("ab12"))
        self.assertTrue(contracts.is_valid_worktree_name("crew-extended-tools"))
        for bad in ("", "..", "a/b", "a\\b", "-x", "x" * 65, "a..b"):
            self.assertFalse(contracts.is_valid_worktree_name(bad), bad)

    def test_branch_name_gaps(self):
        self.assertEqual([], contracts.branch_name_gaps("feat/crew-extended-tools"))
        for bad in ("", "main", "master", "-x", "a..b", "a//b", "x.lock", "feat/a b", "x/"):
            self.assertTrue(contracts.branch_name_gaps(bad), bad)
        self.assertIsInstance(contracts.branch_name_gaps("main"), contracts.ContractGaps)

    def test_lesson_and_change_request_gaps(self):
        self.assertEqual([], contracts.lesson_gaps("worker", "keep proofs deterministic"))
        self.assertTrue(contracts.lesson_gaps("", "x"))
        self.assertTrue(contracts.lesson_gaps("pilot", "x"))
        self.assertTrue(contracts.lesson_gaps("worker", ""))
        self.assertTrue(contracts.lesson_gaps("worker", "x" * 401))
        self.assertEqual([], contracts.change_request_gaps("t_1234", "fix the failing assertion in x"))
        self.assertTrue(contracts.change_request_gaps("", "fix the failing assertion"))
        self.assertTrue(contracts.change_request_gaps("t_1234", "fix"))

    def test_plan_split_spec(self):
        ok = contracts.PlanSplitSpec.from_dict({"goal": "g", "children": [child(1), child(2)]})
        self.assertEqual([], ok.validate_gaps())
        self.assertTrue(contracts.PlanSplitSpec.from_dict({"goal": "g", "children": []}).validate_gaps())
        dup = contracts.PlanSplitSpec.from_dict({"goal": "g", "children": [child(1), child(2, artifact="file1.py")]})
        self.assertIn("two writers", " ".join(dup.validate_gaps()))
        closeout = contracts.PlanSplitSpec.from_dict({"goal": "g", "children": [child(1, verify="closeout")]})
        self.assertIn("reserved", " ".join(closeout.validate_gaps()))
        # a caller cannot smuggle an owner-confirmed close-out proof through the spec
        self.assertNotIn("closeout_proof", contracts.PlanSplitSpec.from_dict(
            {"goal": "g", "children": [child(1)], "closeout_proof": "rm -rf /"}).to_dict())


# ============================================================ 1. Core ops


class StopCardTests(BoardCase):
    def setUp(self):
        super().setUp()
        self.cli = K.kernel_cli(self.db)
        for p in (mock.patch.object(crew_stop.subprocess, "run", self.cli),
                  mock.patch.dict(os.environ, {"CREW_STOP_HERMES_ROOT": os.path.join(self.dir, "hermes")})):
            p.start()
            self.addCleanup(p.stop)

    def test_parks_a_ready_crew_card(self):
        cid = K.add_card(self.conn, "ready")
        res = handle_crew_stop_card({"card_id": cid})
        self.assertEqual("ok", res["status"], res)
        self.assertTrue(res["stopped"])
        self.assertEqual("blocked", self.status(cid))
        self.assertTrue(crew_card.parked_by_owner(self.db, cid))
        self.assertEqual("block", self.cli.calls[0][2])

    def test_parks_a_todo_card_by_scheduling_it(self):
        cid = K.add_card(self.conn, "blocked")
        res = handle_crew_stop_card({"card_id": cid})
        self.assertEqual("ok", res["status"], res)
        self.assertEqual("scheduled", self.status(cid))

    def test_archive_drops_the_card(self):
        cid = K.add_card(self.conn, "ready")
        res = handle_crew_stop_card({"card_id": cid, "archive": True})
        self.assertEqual("ok", res["status"], res)
        self.assertTrue(res["archived"])
        self.assertEqual("archived", self.status(cid))

    def test_dry_run_changes_nothing(self):
        cid = K.add_card(self.conn, "ready")
        res = handle_crew_stop_card({"card_id": cid, "dry_run": True})
        self.assertEqual("dry_run", res["status"])
        self.assertEqual("ready", self.status(cid))
        self.assertEqual([], self.cli.calls)

    def test_module_board_binding_is_restored_after_the_call(self):
        before = crew_stop.KANBAN_DB
        cid = K.add_card(self.conn, "ready")
        handle_crew_stop_card({"card_id": cid, "dry_run": True})
        self.assertEqual(before, crew_stop.KANBAN_DB)

    def test_refuses_non_crew_card_and_unknown_or_missing_id(self):
        cid = K.add_card(self.conn, "ready", body="just a plain note, no contract")
        res = handle_crew_stop_card({"card_id": cid})
        self.assertEqual("refused", res["status"])
        self.assertEqual("ready", self.status(cid))
        self.assertEqual("error", handle_crew_stop_card({"card_id": "t_deadbeef"})["status"])
        self.assertEqual("error", handle_crew_stop_card({})["status"])


# ============================================================ 2. Pipeline ops


class ReviewHandoffTests(BoardCase):
    def setUp(self):
        super().setUp()
        p = mock.patch.object(crew_card, "repin_for_review", return_value={"action": "unchanged"})
        p.start()
        self.addCleanup(p.stop)

    def test_independent_card_moves_to_review(self):
        cid = K.add_card(self.conn, "ready", body=INDEPENDENT_BODY)
        res = handle_crew_review_handoff({"card_id": cid, "summary": "implemented x; tests pass",
                                          "reviewer": "reviewer"})
        self.assertEqual("ok", res["status"], res)
        self.assertTrue(res["moved_to_review"])
        task = self.kb.get_task(self.conn, cid)
        self.assertEqual(("review", "reviewer"), (task.status, task.assignee))

    def test_proof_card_is_refused(self):
        cid = K.add_card(self.conn, "ready", body=PROOF_BODY)
        res = handle_crew_review_handoff({"card_id": cid, "summary": "done"})
        self.assertEqual("refused", res["status"])
        self.assertEqual("proof", res["verify"])
        self.assertEqual("ready", self.status(cid))

    def test_handoff_needs_summary_and_known_card(self):
        cid = K.add_card(self.conn, "ready", body=INDEPENDENT_BODY)
        self.assertEqual("error", handle_crew_review_handoff({"card_id": cid})["status"])
        self.assertEqual("error", handle_crew_review_handoff({"card_id": "t_deadbeef", "summary": "s"})["status"])
        self.assertEqual("error", handle_crew_review_handoff({"card_id": cid, "action": "bogus"})["status"])

    def test_preview_reports_prior_runs(self):
        cid = K.add_card(self.conn, "ready", body=INDEPENDENT_BODY)
        first = handle_crew_review_handoff({"card_id": cid, "action": "preview"})
        self.assertEqual(("ok", False), (first["status"], first["has_prior_runs"]))
        self.kb.claim_task(self.conn, cid, claimer="test")
        with mock.patch.dict(os.environ, {"HERMES_KANBAN_RUN_ID": ""}):
            second = handle_crew_review_handoff({"card_id": cid, "action": "preview"})
        self.assertTrue(second["has_prior_runs"], second)
        self.assertIn("[crew hand-off]", second["handoff"])


class RequestChangesTests(BoardCase):
    def _in_review_run(self):
        cid = K.add_card(self.conn, "ready", body=INDEPENDENT_BODY, assignee="coder")
        task = self.kb.claim_task(self.conn, cid, claimer="coder")
        ok = self.kb.request_review(self.conn, cid, summary="impl", reviewer="reviewer",
                                    expected_run_id=task.current_run_id)
        self.assertTrue(ok)
        self.assertIsNotNone(self.kb.claim_review_task(self.conn, cid, claimer="reviewer"))
        return cid

    def test_returns_card_to_implementer(self):
        cid = self._in_review_run()
        res = handle_crew_request_changes({"card_id": cid, "reason": "assert the exit code in test_x, not stdout"})
        self.assertEqual("ok", res["status"], res)
        task = self.kb.get_task(self.conn, cid)
        self.assertEqual(task.assignee, res["returned_to"])
        self.assertIn(task.status, ("ready", "todo"))
        self.assertIn("changes_requested", K.events(self.conn, cid))

    def test_refused_outside_a_review_run(self):
        cid = K.add_card(self.conn, "ready", body=INDEPENDENT_BODY)
        res = handle_crew_request_changes({"card_id": cid, "reason": "assert the exit code in test_x"})
        self.assertEqual("refused", res["status"])
        self.assertEqual("ready", self.status(cid))

    def test_vague_reason_is_rejected_before_the_kernel(self):
        res = handle_crew_request_changes({"card_id": "t_deadbeef", "reason": "fix"})
        self.assertEqual("error", res["status"])
        self.assertTrue(res["gaps"])


class PlanSplitTests(BoardCase):
    def test_dry_run_previews_parent_children_and_closeout(self):
        res = handle_crew_plan_split({"title": "split", "goal": "ship x", "children": [child(1), child(2)]})
        self.assertEqual("dry_run", res["status"], res)
        self.assertEqual(2, res["child_count"])
        plan = res["plan"]
        self.assertTrue(plan["parent"]["dry_run"])
        self.assertTrue(plan["closeout"]["dry_run"])
        self.assertIn("closeout --cards", plan["closeout"]["body"])
        for ch in plan["children"]:
            self.assertEqual("true", ch["proof_cmd"])
        self.assertEqual(0, self.conn.execute("select count(*) from tasks").fetchone()[0])

    def test_invalid_plans_are_refused(self):
        self.assertEqual("error", handle_crew_plan_split({"goal": "g", "children": []})["status"])
        dup = handle_crew_plan_split({"goal": "g", "children": [child(1), child(2, artifact="file1.py")]})
        self.assertIn("two writers", dup["error"])
        gap = handle_crew_plan_split({"goal": "g", "children": [child(1, proof_cmd="")]})
        self.assertIn("proof command", gap["error"])

    def test_closeout_proof_from_caller_is_ignored(self):
        res = handle_crew_plan_split({"goal": "g", "children": [child(1)], "closeout_proof": "echo owned"})
        self.assertEqual("dry_run", res["status"], res)
        self.assertNotIn("echo owned", res["plan"]["closeout"]["body"])


# ============================================================ 3. Workspace ops


def _git(*args, cwd):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "core.hooksPath=" + os.devnull]
                          + list(args), cwd=cwd, capture_output=True, text=True, check=True)


@unittest.skipUnless(shutil.which("git"), "git not installed")
class WorktreeTests(unittest.TestCase):
    def setUp(self):
        self.base = tempfile.mkdtemp(prefix="wt-", dir=SCRATCH)
        self.repo = os.path.join(self.base, "repo")
        self.root = os.path.join(self.base, ".worktrees")
        os.makedirs(self.repo)
        _git("init", "-q", "-b", "main", cwd=self.repo)
        Path(self.repo, "a.txt").write_text("a\n", encoding="utf-8")
        _git("add", "a.txt", cwd=self.repo)
        _git("commit", "-q", "-m", "init", cwd=self.repo)
        self.addCleanup(shutil.rmtree, self.base, True)

    def branch_of_repo(self):
        return _git("rev-parse", "--abbrev-ref", "HEAD", cwd=self.repo).stdout.strip()

    def create(self, **over):
        args = {"repo": self.repo, "name": "feat-x", "branch": "feat/x", "worktrees_root": self.root}
        args.update(over)
        return handle_crew_worktree_create(args)

    def test_create_makes_isolated_worktree_without_touching_primary_branch(self):
        res = self.create()
        self.assertEqual("ok", res["status"], res)
        path = os.path.join(self.root, "feat-x")
        self.assertEqual(os.path.normcase(os.path.normpath(path)), os.path.normcase(res["path"]))
        self.assertTrue(os.path.isfile(os.path.join(path, "a.txt")))
        self.assertEqual("feat/x", _git("rev-parse", "--abbrev-ref", "HEAD", cwd=path).stdout.strip())
        self.assertEqual("main", self.branch_of_repo())

    def test_create_refusals(self):
        self.assertEqual("refused", self.create(branch="main")["status"])
        self.assertEqual("error", self.create(name="../escape")["status"])
        self.assertEqual("error", self.create(base="--orphan")["status"])
        self.assertEqual("error", self.create(repo=self.base)["status"])  # not a git repository
        self.assertEqual("ok", self.create()["status"])
        self.assertEqual("refused", self.create()["status"])  # path exists
        self.assertEqual("refused", self.create(name="other")["status"])  # branch exists
        self.assertEqual("main", self.branch_of_repo())

    def test_create_dry_run(self):
        res = self.create(dry_run=True)
        self.assertEqual("dry_run", res["status"])
        self.assertIn("worktree", res["argv"])
        self.assertFalse(os.path.exists(os.path.join(self.root, "feat-x")))

    def test_cleanup_removes_worktree_and_branch(self):
        self.assertEqual("ok", self.create()["status"])
        res = handle_crew_worktree_cleanup({"repo": self.repo, "name": "feat-x", "worktrees_root": self.root,
                                            "delete_branch": True})
        self.assertEqual("ok", res["status"], res)
        self.assertTrue(res["removed"])
        self.assertFalse(os.path.exists(os.path.join(self.root, "feat-x")))
        branches = _git("branch", "--list", "feat/x", cwd=self.repo).stdout.strip()
        self.assertEqual("", branches)
        self.assertEqual("main", self.branch_of_repo())

    def test_cleanup_refuses_dirty_unless_forced(self):
        self.assertEqual("ok", self.create()["status"])
        Path(self.root, "feat-x", "new.txt").write_text("wip\n", encoding="utf-8")
        args = {"repo": self.repo, "name": "feat-x", "worktrees_root": self.root}
        dirty = handle_crew_worktree_cleanup(args)
        self.assertEqual("refused", dirty["status"])
        self.assertTrue(os.path.exists(os.path.join(self.root, "feat-x", "new.txt")))
        forced = handle_crew_worktree_cleanup(dict(args, force=True))
        self.assertEqual("ok", forced["status"], forced)

    def test_cleanup_refuses_unregistered_and_main(self):
        os.makedirs(os.path.join(self.root, "stray"))
        res = handle_crew_worktree_cleanup({"repo": self.repo, "name": "stray", "worktrees_root": self.root})
        self.assertEqual("refused", res["status"])
        self.assertTrue(os.path.isdir(os.path.join(self.root, "stray")))
        main = handle_crew_worktree_cleanup({"repo": self.repo, "name": "repo", "worktrees_root": self.base})
        self.assertEqual("refused", main["status"])
        self.assertTrue(os.path.isfile(os.path.join(self.repo, "a.txt")))

    def test_root_resolution_and_porcelain_parser(self):
        os.makedirs(self.root)
        self.assertEqual(os.path.normpath(self.root), worktrees_root_for(self.repo))
        self.assertEqual(os.path.normpath(os.path.abspath("x")), worktrees_root_for(self.repo, "x"))
        trees = parse_worktree_porcelain("worktree /r\nHEAD abc\nbranch refs/heads/main\n\n"
                                         "worktree /w\nHEAD def\ndetached\n")
        self.assertEqual(["main", ""], [t["branch"] for t in trees])
        self.assertTrue(trees[1]["detached"])


# ============================================================ 4. Intelligence ops


class FlowGraphTests(BoardCase):
    GRAPH = {
        "card_id": "t_1", "card_title": "T", "card_status": "done",
        "nodes": [{"id": "brief:t_1", "kind": "brief", "label": "t_1", "status": "done", "title": 'owner "brief"'},
                  {"id": "card:t_1", "kind": "card", "label": "t_1", "status": "running"},
                  {"id": "run:7", "kind": "run", "label": "7", "status": "blocked"}],
        "edges": [{"from": "brief:t_1", "to": "card:t_1"}, {"from": "card:t_1", "to": "run:7"},
                  {"from": "card:t_1", "to": "missing"}],
    }

    def test_graph_to_mermaid_is_deterministic_and_escaped(self):
        out = graph_to_mermaid(self.GRAPH, "LR")
        self.assertTrue(out.startswith("flowchart LR\n"))
        self.assertIn("n0 --> n1", out)
        self.assertIn("n1 --> n2", out)
        self.assertEqual(2, out.count("-->"))  # the dangling edge is dropped
        self.assertIn("#quot;brief#quot;", out)
        self.assertIn("classDef st_blocked", out)
        self.assertEqual(out, graph_to_mermaid(self.GRAPH, "LR"))

    def test_handler_renders_mermaid_and_json(self):
        import crew_graph
        with mock.patch.object(crew_graph, "build_graph", return_value=(self.GRAPH, None)):
            m = handle_crew_flow_graph({"card_id": "t_1"})
            j = handle_crew_flow_graph({"card_id": "t_1", "format": "json"})
        self.assertEqual(("ok", 3, 3), (m["status"], m["node_count"], m["edge_count"]))
        self.assertTrue(m["mermaid"].startswith("flowchart TD"))
        self.assertEqual(["brief", "card", "run"], [n["kind"] for n in j["nodes"]])

    def test_real_board_card_renders(self):
        cid = K.add_card(self.conn, "ready", body=PROOF_BODY, title="flow")
        res = handle_crew_flow_graph({"card_id": cid})
        self.assertEqual("ok", res["status"], res)
        self.assertEqual(cid, res["card_id"])
        self.assertIn("flowchart TD", res["mermaid"])

    def test_errors(self):
        self.assertEqual("error", handle_crew_flow_graph({"card_id": "t_deadbeef"})["status"])
        self.assertEqual("error", handle_crew_flow_graph({"format": "svg"})["status"])
        self.assertEqual("error", handle_crew_flow_graph({"direction": "UP"})["status"])


class LessonRecordTests(unittest.TestCase):
    def setUp(self):
        self.path = crew_lessons.path()
        self.assertTrue(os.path.abspath(self.path).startswith(os.path.abspath(SCRATCH)), self.path)
        if os.path.exists(self.path):
            os.remove(self.path)
        env = {k: v for k, v in os.environ.items() if k not in ("HERMES_KANBAN_TASK", "CREW_COORDINATOR_TURN")}
        p = mock.patch.dict(os.environ, env, clear=True)
        p.start()
        self.addCleanup(p.stop)

    def test_add_show_and_duplicate(self):
        res = handle_crew_lesson_record({"role": "worker", "text": "run  the proof through the verdict tool"})
        self.assertEqual(("ok", "added"), (res["status"], res["result"]))
        self.assertEqual("run the proof through the verdict tool", res["text"])
        again = handle_crew_lesson_record({"role": "worker", "text": "run the proof through the verdict tool"})
        self.assertEqual("duplicate", again["result"])
        shown = handle_crew_lesson_record({"action": "show", "role": "worker"})
        self.assertEqual(["run the proof through the verdict tool"], shown["lessons"])
        self.assertEqual(0, handle_crew_lesson_record({"action": "show", "role": "content"})["count"])

    def test_validation(self):
        self.assertEqual("error", handle_crew_lesson_record({"role": "pilot", "text": "x"})["status"])
        self.assertEqual("error", handle_crew_lesson_record({"role": "worker", "text": ""})["status"])
        self.assertEqual("error", handle_crew_lesson_record({"role": "worker", "text": "x" * 401})["status"])
        self.assertEqual("error", handle_crew_lesson_record({"action": "drop", "role": "worker"})["status"])
        self.assertFalse(os.path.exists(self.path))

    def test_agent_may_not_write_all_lessons(self):
        with mock.patch.dict(os.environ, {"HERMES_KANBAN_TASK": "t_1"}):
            res = handle_crew_lesson_record({"role": "all", "text": "everyone reads this"})
        self.assertEqual("refused", res["status"])
        self.assertFalse(os.path.exists(self.path))


if __name__ == "__main__":
    unittest.main()

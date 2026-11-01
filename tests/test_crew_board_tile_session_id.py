"""board_data tiles carry `session_id`: the chat session a card came from, resolved to the durable lineage root so it
matches the id Desktop's sidebar row passes to the Crew session chip. The one owner of that policy is the public
crew_graph.resolve_tile_session_id(); crew_graph_serve.board_data() only calls it. Boards are hand-made sqlite files
(the tables the resolver reads) and the profile scan is patched, so the tests run without Hermes."""
import importlib.util
import json
import os
import re
import shutil
import sqlite3
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(os.path.dirname(HERE), "scripts")
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

import crew_graph as cg  # noqa: E402

SESSION_COLS = ("id text primary key, parent_session_id text, source text, model text, title text, "
                "started_at real, ended_at real, message_count int, tool_call_count int, input_tokens int, "
                "output_tokens int, profile_name text")


def make_board(directory, cards, session_column=True, name="kanban.db"):
    """cards: dicts with id, status, optional session_id, body, origin (task_events origin), run_session, parents."""
    path = os.path.join(directory, name)
    conn = sqlite3.connect(path)
    cols = ("id text, title text, status text, assignee text, created_at int, started_at int, completed_at int, "
            "body text, skills text, last_failure_error text")
    if session_column:
        cols += ", session_id text"
    conn.execute("create table tasks (%s)" % cols)
    conn.execute("create table task_events (id integer primary key, task_id text, run_id int, kind text, payload text)")
    conn.execute("create table task_links (parent_id text, child_id text)")
    conn.execute("create table task_runs (id integer primary key, task_id text, profile text, status text, "
                 "started_at int, ended_at int, last_heartbeat_at int, outcome text, worker_pid text)")
    for c in cards:
        row = [c["id"], "card " + c["id"], c.get("status", "ready"), "crew-worker", 1000, None, None,
               c.get("body", ""), "", ""]
        marks = "?,?,?,?,?,?,?,?,?,?"
        if session_column:
            row.append(c.get("session_id"))
            marks += ",?"
        conn.execute("insert into tasks values (%s)" % marks, row)
        if c.get("origin"):
            conn.execute("insert into task_events (task_id, kind, payload) values (?,?,?)",
                         (c["id"], "origin", json.dumps({"session": c["origin"], "by": "default"})))
        if c.get("run_session"):
            conn.execute("insert into task_events (task_id, run_id, kind, payload) values (?,?,?,?)",
                         (c["id"], 1, "session", json.dumps({"session": c["run_session"]})))
        for p in c.get("parents", ()):
            conn.execute("insert into task_links values (?,?)", (p, c["id"]))
    conn.commit()
    conn.close()
    return path


def make_state(directory, sessions, name="state_sessions.db"):
    """sessions: (id, parent_session_id, source, message_count)."""
    path = os.path.join(directory, name)
    conn = sqlite3.connect(path)
    conn.execute("create table sessions (%s)" % SESSION_COLS)
    for sid, parent, source, count in sessions:
        conn.execute("insert into sessions values (?,?,?,?,?,?,?,?,?,?,?,?)",
                     (sid, parent, source, "m", "t", 1000.0, None, count, 0, 0, 0, "default"))
    conn.commit()
    conn.close()
    return path


def make_lineage_state(directory, sessions, name="state_lineage.db"):
    """sessions: (id, parent_session_id, source, end_reason, model_config dict or None): the real state.db columns the
    lineage walk reads to tell a compression continuation from a branch, a reset or a delegation."""
    path = os.path.join(directory, name)
    conn = sqlite3.connect(path)
    conn.execute("create table sessions (%s, end_reason text, model_config text)" % SESSION_COLS)
    for sid, parent, source, end_reason, config in sessions:
        conn.execute("insert into sessions values (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                     (sid, parent, source, "m", "t", 1000.0, None, 4, 0, 0, 0, "default", end_reason,
                      json.dumps(config) if config is not None else None))
    conn.commit()
    conn.close()
    return path


class ResolveTileSessionId(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        for cache in (cg._ORIGIN_CACHE, cg._ROOT_CACHE):
            cache.clear()
            self.addCleanup(cache.clear)

    def resolve(self, board, card, body="", created_at=None, states=()):
        with mock.patch.object(cg, "discover_state_dbs", return_value=list(states)):
            return cg.resolve_tile_session_id(board, card, body, created_at)

    def test_tasks_session_id_column_names_the_origin_session(self):
        board = make_board(self.tmp.name, [{"id": "t_a", "session_id": "sess-a"}])
        self.assertEqual("sess-a", self.resolve(board, "t_a"))

    def test_task_events_origin_names_the_origin_session(self):
        board = make_board(self.tmp.name, [{"id": "t_b", "origin": "sess-b"}])
        self.assertEqual("sess-b", self.resolve(board, "t_b"))

    def test_coordinator_body_line_names_the_origin_session(self):
        body = "Role: worker\nCoordinator: default/sess-c\n\nGOAL: g\n"
        board = make_board(self.tmp.name, [{"id": "t_c", "body": body}])
        self.assertEqual("sess-c", self.resolve(board, "t_c", body))

    def test_coordinator_line_is_read_from_the_card_when_no_body_is_passed(self):
        board = make_board(self.tmp.name, [{"id": "t_c2", "body": "Coordinator: default/sess-c2\n"}])
        self.assertEqual("sess-c2", self.resolve(board, "t_c2"))

    def test_worker_run_session_is_never_the_origin(self):
        board = make_board(self.tmp.name, [{"id": "t_w", "session_id": "sess-worker", "run_session": "sess-worker",
                                             "body": "Coordinator: default/sess-worker\n"}])
        self.assertEqual("", self.resolve(board, "t_w", "Coordinator: default/sess-worker\n"))

    def test_no_session_and_local_drafts_resolve_to_nothing(self):
        board = make_board(self.tmp.name, [
            {"id": "t_n", "session_id": "no-session"},
            {"id": "t_l", "session_id": "local-abc123", "body": "Coordinator: default/local-abc123\n"}])
        self.assertEqual("", self.resolve(board, "t_n"))
        self.assertEqual("", self.resolve(board, "t_l", "Coordinator: default/local-abc123\n"))

    def test_kanban_worker_session_in_state_db_is_rejected(self):
        state = make_state(self.tmp.name, [("sess-kw", None, "kanban", 5)])
        board = make_board(self.tmp.name, [{"id": "t_k", "body": "Coordinator: default/sess-kw\n"}])
        self.assertEqual("", self.resolve(board, "t_k", "Coordinator: default/sess-kw\n", states=[("default", state)]))

    def test_child_inherits_the_parent_cards_session(self):
        board = make_board(self.tmp.name, [
            {"id": "t_parent", "session_id": "s_parent"},
            {"id": "t_child", "parents": ["t_parent"]}])
        self.assertEqual("s_parent", self.resolve(board, "t_child"))

    def test_child_inherits_a_parent_that_only_carries_a_coordinator_line(self):
        board = make_board(self.tmp.name, [
            {"id": "t_parent2", "body": "Coordinator: default/s_parent2\n"},
            {"id": "t_child2", "parents": ["t_parent2"]}])
        self.assertEqual("s_parent2", self.resolve(board, "t_child2"))

    def test_parent_cycle_terminates_without_a_session(self):
        board = make_board(self.tmp.name, [
            {"id": "t_x", "parents": ["t_y"]}, {"id": "t_y", "parents": ["t_x"]}])
        self.assertEqual("", self.resolve(board, "t_x"))

    def test_continuation_session_resolves_to_the_durable_lineage_root(self):
        state = make_state(self.tmp.name, [("s_root", None, "cli", 4), ("s_mid", "s_root", "cli", 4),
                                           ("s_child", "s_mid", "cli", 4)])
        board = make_board(self.tmp.name, [{"id": "t_r", "session_id": "s_child"}])
        self.assertEqual("s_root", self.resolve(board, "t_r", states=[("default", state)]))

    def test_lineage_walk_survives_a_parent_cycle(self):
        state = make_state(self.tmp.name, [("s_a", "s_b", "cli", 4), ("s_b", "s_a", "cli", 4)])
        board = make_board(self.tmp.name, [{"id": "t_cyc", "session_id": "s_a"}])
        self.assertIn(self.resolve(board, "t_cyc", states=[("default", state)]), ("s_a", "s_b"))

    def lineage(self, sessions, card_session):
        n = len(os.listdir(self.tmp.name))
        state = make_lineage_state(self.tmp.name, sessions, name="lineage-%d.db" % n)
        board = make_board(self.tmp.name, [{"id": "t_l1", "session_id": card_session}], name="board-%d.db" % n)
        return self.resolve(board, "t_l1", states=[("default", state)])

    def test_branch_of_a_local_cron_session_keeps_its_own_id(self):
        local = "local-371cf5d68f9a8708fad179bb64210fb9fe4518e7f25a30793a836878666cf3c5"
        got = self.lineage([(local, None, "cron", None, None),
                            ("20261101_064445_40877a", local, "desktop", None, {"_branched_from": local})],
                           "20261101_064445_40877a")
        self.assertEqual("20261101_064445_40877a", got)

    def test_branch_marker_stops_the_walk_even_for_a_normal_parent(self):
        got = self.lineage([("s_a", None, "cli", "compression", None),
                            ("s_b", "s_a", "cli", None, {"_branched_from": "s_a"})], "s_b")
        self.assertEqual("s_b", got)

    def test_reset_and_delegate_markers_stop_the_walk(self):
        for marker in ("_reset_from", "_delegate_from"):
            with self.subTest(marker=marker):
                cg._ROOT_CACHE.clear()
                got = self.lineage([("s_a", None, "cli", None, None), ("s_b", "s_a", "cli", None, {marker: "s_a"})], "s_b")
                self.assertEqual("s_b", got)

    def test_tool_source_child_stops_the_walk(self):
        got = self.lineage([("s_a", None, "cli", None, None), ("s_t", "s_a", "tool", None, None)], "s_t")
        self.assertEqual("s_t", got)

    def test_parent_not_ended_by_compression_stops_the_walk(self):
        got = self.lineage([("s_a", None, "cli", "user_exit", None), ("s_b", "s_a", "cli", None, None)], "s_b")
        self.assertEqual("s_b", got)

    def test_sessions_store_without_a_parent_column_keeps_every_field_in_place(self):
        # a valid minimal store: sessions(id, source, model_config, end_reason) has no parent_session_id; the row must not
        # be zipped against a column list that still names it (source would land in parent_session_id)
        path = os.path.join(self.tmp.name, "no-parent.db")
        conn = sqlite3.connect(path)
        conn.execute("create table sessions (id text, source text, model_config text, end_reason text)")
        conn.execute("insert into sessions values ('s_x', 'interactive', '{}', null)")
        conn.commit()
        conn.close()
        with mock.patch.object(cg, "discover_state_dbs", return_value=[("default", path)]):
            row = cg._session_lineage_row("s_x")
            self.assertEqual(("", "interactive", {}, None, True), row)
            self.assertEqual("s_x", cg._root_session_id("s_x"))

    def test_compression_continuation_of_a_branch_resolves_to_the_branch_root(self):
        local = "local-cron1"
        got = self.lineage([(local, None, "cron", None, None),
                            ("br_root", local, "desktop", "compression", {"_branched_from": local}),
                            ("br_tip", "br_root", "desktop", None, None)], "br_tip")
        self.assertEqual("br_root", got)

    def test_compression_ended_chain_walks_to_the_root(self):
        got = self.lineage([("s_a", None, "cli", "compression", None), ("s_b", "s_a", "cli", "compression", None),
                            ("s_c", "s_b", "cli", None, None)], "s_c")
        self.assertEqual("s_a", got)

    def test_minimal_tasks_table_without_a_session_column_resolves_from_the_body(self):
        board = make_board(self.tmp.name, [{"id": "t_m", "body": "Coordinator: default/sess-m\n"}], session_column=False)
        self.assertEqual("sess-m", self.resolve(board, "t_m", "Coordinator: default/sess-m\n"))
        self.assertEqual("", self.resolve(board, "t_unknown"))

    def test_unusable_inputs_resolve_to_nothing(self):
        self.assertEqual("", cg.resolve_tile_session_id(None, "t_z"))
        self.assertEqual("", cg.resolve_tile_session_id("", ""))


class BoardDataStampsSessionId(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        spec = importlib.util.spec_from_file_location("cgs_tile_session",
                                                      os.path.join(SCRIPTS, "crew_graph_serve.py"))
        self.mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.mod)
        self.mod.CG._ORIGIN_CACHE.clear()
        self.mod.CG._ROOT_CACHE.clear()

    def tiles(self, board):
        with mock.patch.object(self.mod.CG, "kanban_db_path", return_value=board), \
             mock.patch.object(self.mod.CG, "discover_state_dbs", return_value=[]):
            out = {}
            for lane in self.mod.board_data()["lanes"]:
                out.update({t["id"]: t for t in lane["tiles"]})
            return out

    def test_every_open_tile_carries_its_origin_session(self):
        board = make_board(self.tmp.name, [
            {"id": "t_1", "status": "running", "session_id": "sess-a"},
            {"id": "t_2", "status": "ready", "origin": "sess-b"},
            {"id": "t_3", "status": "review", "body": "Coordinator: default/sess-c\n"},
            {"id": "t_4", "status": "ready", "parents": ["t_1"]},
            {"id": "t_5", "status": "done", "session_id": "sess-a"},
            {"id": "t_6", "status": "ready"}])
        t = self.tiles(board)
        self.assertEqual(
            {"t_1": "sess-a", "t_2": "sess-b", "t_3": "sess-c", "t_4": "sess-a", "t_5": "sess-a", "t_6": ""},
            {k: v["session_id"] for k, v in t.items()})

    def test_archived_tiles_carry_an_empty_session_id(self):
        board = make_board(self.tmp.name, [{"id": "t_old", "status": "archived", "session_id": "sess-a"}])
        t = self.tiles(board)
        self.assertEqual("", t["t_old"]["session_id"])

    def test_minimal_tasks_table_keeps_its_tiles(self):
        board = make_board(self.tmp.name, [
            {"id": "t_1", "status": "running", "body": "Coordinator: default/sess-a\n"},
            {"id": "t_2", "status": "ready"}], session_column=False)
        t = self.tiles(board)
        self.assertEqual({"t_1", "t_2"}, set(t))
        self.assertEqual("sess-a", t["t_1"]["session_id"])
        self.assertEqual("", t["t_2"]["session_id"])

    def test_server_module_touches_no_private_graph_name(self):
        with open(os.path.join(SCRIPTS, "crew_graph_serve.py"), encoding="utf-8") as f:
            src = f.read()
        self.assertIn("CG.resolve_tile_session_id(", src)
        self.assertEqual([], re.findall(r"\bCG\._\w+", src))
        self.assertNotIn("def tile_session_id", src)


class HotReloadOnCutover(unittest.TestCase):
    """A cutover replaces scripts/*.py under a process that stays up (the Hermes dashboard); the next render must run
    the new code. Scripts are copied to a scratch dir so the test rewrites a copy, never the real ones."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.scripts = os.path.join(self.tmp.name, "scripts")
        shutil.copytree(SCRIPTS, self.scripts, ignore=shutil.ignore_patterns("__pycache__", "crew_dashboard"))

    def bump(self, name, marker):
        path = os.path.join(self.scripts, name)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write("\n%s = True\n" % marker)
        st = os.stat(path)
        os.utime(path, ns=(st.st_atime_ns, st.st_mtime_ns + 5_000_000_000))

    def load_serve(self):
        spec = importlib.util.spec_from_file_location("cgs_hot_reload", os.path.join(self.scripts, "crew_graph_serve.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_serve_reloads_crew_graph_when_its_file_changes(self):
        mod = self.load_serve()
        before = mod.CG
        self.assertFalse(mod.refresh_graph())
        self.assertIs(before, mod.CG)
        self.bump("crew_graph.py", "HOT_RELOAD_MARKER")
        self.assertTrue(mod.refresh_graph())
        self.assertIsNot(before, mod.CG)
        self.assertTrue(mod.CG.HOT_RELOAD_MARKER)
        self.assertFalse(mod.refresh_graph())

    def test_direct_card_json_route_reloads_the_graph_too(self):
        # /card/<id>.json served by a standalone daemon may be the only route hit after a cutover
        mod = self.load_serve()
        before = mod.CG
        self.bump("crew_graph.py", "HOT_RELOAD_MARKER")
        mod.card_response("t_none.json")
        self.assertIsNot(before, mod.CG)
        self.assertTrue(mod.CG.HOT_RELOAD_MARKER)

    def test_serve_keeps_the_loaded_graph_when_the_new_file_is_broken(self):
        mod = self.load_serve()
        before = mod.CG
        with open(os.path.join(self.scripts, "crew_graph.py"), "a", encoding="utf-8") as fh:
            fh.write("\nraise RuntimeError('broken cutover')\n")
        path = os.path.join(self.scripts, "crew_graph.py")
        os.utime(path, ns=(0, os.stat(path).st_mtime_ns + 5_000_000_000))
        self.assertFalse(mod.refresh_graph())
        self.assertIs(before, mod.CG)

    def test_dashboard_plugin_reloads_the_server_module_when_a_script_changes(self):
        api_path = os.path.join(os.path.dirname(HERE), "dashboard", "plugin_api.py")
        spec = importlib.util.spec_from_file_location("crew_plugin_api_hot_reload", api_path)
        api = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(api)
        except ImportError as exc:
            self.skipTest("plugin_api deps unavailable: %s" % exc)
        api.SCRIPTS_DIR = self.scripts
        self.addCleanup(sys.modules.pop, "crew_graph_serve", None)
        sys.modules.pop("crew_graph_serve", None)
        first = api._crew()
        self.assertIs(first, api._crew())
        self.bump("crew_graph.py", "HOT_RELOAD_MARKER")
        second = api._crew()
        self.assertIsNot(first, second)
        self.assertTrue(second.CG.HOT_RELOAD_MARKER)
        self.assertIs(second, api._crew())


if __name__ == "__main__":
    unittest.main(verbosity=2)

"""board_data tiles carry `session_id`: the chat session a card came from, resolved to the durable lineage root so it
matches the id Desktop's sidebar row passes to the Crew session chip. The one owner of that policy is the public
crew_graph.resolve_tile_session_id(); crew_graph_serve.board_data() only calls it. Boards are hand-made sqlite files
(the tables the resolver reads) and the profile scan is patched, so the tests run without Hermes."""
import importlib.util
import json
import os
import re
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


if __name__ == "__main__":
    unittest.main(verbosity=2)

"""crew_observe.observe_delivered (OpenSpec stewardship-core-adoption, Ticket 03, CREW-INV-7).

Seam: the post-delivery regression observer on a disposable kernel board (tests/kernel_board.py) with an injected
clock and an injected sender. It re-runs a done card's owner-confirmed proof, records improved/regressed in
observations.json and a crew_observation task event, alerts once per regression through crew_notify, and never
reopens the card.
"""
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "tests"))

import kernel_board as K  # noqa: E402
import crew_card  # noqa: E402
import crew_notify  # noqa: E402
import crew_observe as O  # noqa: E402
import crew_proc  # noqa: E402

DAY = 86400
ORIGIN = "buzz:11111111-2222-3333-4444-555555555555"


def body(proof="exit 0", extra=""):
    return ("Role: worker\nCoordinator: owner/s\nVerify: proof\nBudget: 200000 tokens\n\nGOAL: g\nArtifact: a\n"
            "Done when: d\n%s\nproof command: %s\n" % (extra, proof))


class Sender:
    def __init__(self):
        self.calls = []

    def __call__(self, target, text):
        self.calls.append((target, text))
        return True, "rc=0 sent"


class Runner:
    """Stands in for the bounded proof run: answers by command text, records what ran."""

    def __init__(self, answers):
        self.answers, self.ran = answers, []

    def __call__(self, cmd, *, cwd=None, timeout_s=60.0, card_id=None, db=None):
        self.ran.append(cmd)
        code, timed_out = self.answers.get(cmd, (0, False))
        return crew_proc.BoundedResult(code, "out of %s" % cmd, "err" if code else "", timed_out, 0.01, "m")


class BoardCase(unittest.TestCase):
    """A disposable kernel board, scratch HERMES_HOME, injected clock and sender."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="crew-observe-unit-")
        self._env = mock.patch.dict(os.environ, {"HERMES_HOME": os.path.join(self.tmp, "home"),
                                                 "CREW_OWNER_PROFILE": "owner", "CREW_CARD_BASE": "http://dash"})
        self._env.start()
        self.addCleanup(self._env.stop)
        self.kb, self.conn, self.db = K.open_board(self.tmp)
        self.addCleanup(self.conn.close)
        self.state = os.path.join(self.tmp, "home", "crew", "observations.json")
        self.notify_state = os.path.join(self.tmp, "home", "crew", "notify-state.json")
        self.now = time.time()
        self.sender = Sender()

    def done_card(self, proof="exit 0", extra="", age_days=1, origin=ORIGIN, snapshot=True):
        cid = K.add_card(self.conn, body=body(proof, extra))
        if snapshot:
            payload = {"proof_cmd": proof, "ts": 0}
            if origin:
                payload["origin"] = origin
            crew_card._append_card_event(cid, "origin", payload, db=self.db)
        self.kb.claim_task(self.conn, cid)
        self.assertTrue(self.kb.complete_task(self.conn, cid, summary="shipped"))
        when = int(self.now - age_days * DAY)
        self.conn.execute("update tasks set completed_at=? where id=?", (when, cid))
        self.conn.commit()
        return cid

    def observe(self, runner, **kw):
        kw.setdefault("clock", lambda: self.now)
        return O.observe_delivered(db_path=self.db, state_path=self.state, runner=runner,
                                   send=self.sender, notify_state_path=self.notify_state, **kw)

    def status_of(self, cid):
        return self.conn.execute("select status from tasks where id=?", (cid,)).fetchone()[0]

    def observations(self):
        with open(self.state, encoding="utf-8") as fh:
            return json.load(fh)["cards"]

    def events(self, cid):
        return [json.loads(r[0]) for r in self.conn.execute(
            "select payload from task_events where task_id=? and kind='crew_observation' order by id", (cid,))]


class ObserveTests(BoardCase):
    # ------------------------------------------------------------------ classification
    def test_passing_proof_is_recorded_improved_without_alert(self):
        cid = self.done_card("exit 0")
        res = self.observe(Runner({"exit 0": (0, False)}))
        self.assertEqual(res["results"][cid]["status"], "improved")
        self.assertEqual(self.observations()[cid]["status"], "improved")
        self.assertEqual([e["status"] for e in self.events(cid)], ["improved"])
        self.assertEqual(self.sender.calls, [])
        self.assertEqual(self.status_of(cid), "done")

    def test_failing_proof_is_regressed_alerted_once_and_never_reopened(self):
        cid = self.done_card("exit 3")
        runner = Runner({"exit 3": (3, False)})
        res = self.observe(runner)
        self.assertEqual(res["results"][cid]["status"], "regressed")
        self.assertEqual(self.observations()[cid]["status"], "regressed")
        ev = self.events(cid)
        self.assertEqual(ev[-1]["status"], "regressed")
        self.assertEqual(ev[-1]["exit_code"], 3)
        self.assertEqual(self.status_of(cid), "done", "no auto-reopen")
        self.assertEqual(len(self.sender.calls), 1)
        target, text = self.sender.calls[0]
        self.assertEqual(target, ORIGIN)
        self.assertIn(cid, text)
        self.assertIn("regress", text.lower())
        self.assertIn("exit 3", text)
        # a second pass still failing: same regression, no second alert
        self.observe(runner)
        self.assertEqual(len(self.sender.calls), 1)
        self.assertEqual(self.status_of(cid), "done")
        sent = crew_notify.sent_keys(self.notify_state, cid)
        self.assertEqual(len(sent), 1)
        self.assertTrue(sent[0].startswith("regressed:%s:" % cid), sent)

    def test_timeout_is_regressed(self):
        cid = self.done_card("sleep 99")
        res = self.observe(Runner({"sleep 99": (124, True)}))
        self.assertEqual(res["results"][cid]["status"], "regressed")
        self.assertTrue(self.observations()[cid]["timed_out"])

    def test_recovery_then_new_regression_alerts_again(self):
        cid = self.done_card("exit 3")
        self.observe(Runner({"exit 3": (3, False)}))
        self.observe(Runner({"exit 3": (0, False)}))
        self.assertEqual(self.observations()[cid]["status"], "improved")
        self.observe(Runner({"exit 3": (3, False)}))
        self.assertEqual(len(self.sender.calls), 2)
        keys = crew_notify.sent_keys(self.notify_state, cid)
        self.assertEqual(len(set(keys)), 2)

    # ------------------------------------------------------------------ eligibility
    def test_window_excludes_old_cards_unless_always_or_requested(self):
        old = self.done_card("exit 0", age_days=20)
        always = self.done_card("exit 0", extra="Observe: always", age_days=40)
        fresh = self.done_card("exit 0", age_days=13)
        res = self.observe(Runner({}))
        self.assertNotIn(old, res["results"])
        self.assertIn(always, res["results"])
        self.assertIn(fresh, res["results"])
        res = self.observe(Runner({}), card_id=old)
        self.assertEqual(list(res["results"]), [old])

    def test_injected_clock_moves_the_window(self):
        cid = self.done_card("exit 0", age_days=1)
        res = self.observe(Runner({}), clock=lambda: self.now + 20 * DAY)
        self.assertNotIn(cid, res["results"])
        res = self.observe(Runner({}), window_days=30, clock=lambda: self.now + 20 * DAY)
        self.assertIn(cid, res["results"])

    def test_observe_off_is_skipped_even_when_requested(self):
        cid = self.done_card("exit 3", extra="Observe: off")
        runner = Runner({"exit 3": (3, False)})
        res = self.observe(runner)
        self.assertNotIn(cid, res["results"])
        res = self.observe(runner, card_id=cid)
        self.assertNotIn(cid, res["results"])
        self.assertIn(cid, res["skipped"])
        self.assertEqual(runner.ran, [])

    def test_cards_without_confirmed_proof_or_not_done_are_ineligible(self):
        no_snap = self.done_card("exit 0", snapshot=False)
        running = K.add_card(self.conn, body=body("exit 0"))
        crew_card._append_card_event(running, "origin", {"proof_cmd": "exit 0"}, db=self.db)
        runner = Runner({})
        res = self.observe(runner)
        self.assertNotIn(no_snap, res["results"])
        self.assertNotIn(running, res["results"])
        self.assertEqual(runner.ran, [])

    def test_cards_outside_the_window_are_not_reported_as_skipped(self):
        old_no_snap = self.done_card("exit 0", age_days=30, snapshot=False)
        res = self.observe(Runner({}))
        self.assertNotIn(old_no_snap, res["results"])
        self.assertNotIn(old_no_snap, res["skipped"], "out-of-window cards are silent, not SKIP noise")
        res = self.observe(Runner({}), card_id=old_no_snap)
        self.assertIn(old_no_snap, res["skipped"], "a requested card still says why it did not run")

    def test_the_snapshot_runs_not_the_edited_body_line(self):
        cid = self.done_card("exit 0")
        self.conn.execute("update tasks set body=? where id=?", (body("exit 7"), cid))
        self.conn.commit()
        runner = Runner({"exit 7": (7, False)})
        res = self.observe(runner)
        self.assertEqual(runner.ran, ["exit 0"])
        self.assertEqual(res["results"][cid]["status"], "improved")

    def test_dry_run_lists_without_running_or_writing(self):
        cid = self.done_card("exit 3")
        runner = Runner({"exit 3": (3, False)})
        res = self.observe(runner, dry_run=True)
        self.assertEqual(res["eligible"], [cid])
        self.assertEqual(runner.ran, [])
        self.assertFalse(os.path.exists(self.state))
        self.assertEqual(self.events(cid), [])
        self.assertEqual(self.sender.calls, [])

    def test_blocked_proof_is_unknown_and_not_alerted(self):
        cid = self.done_card("exit 0")

        def blocked(cmd, **kw):
            return O.BLOCKED

        res = self.observe(blocked)
        self.assertEqual(res["results"][cid]["status"], "unknown")
        self.assertEqual(self.sender.calls, [])
        self.assertEqual(self.status_of(cid), "done")


class RegistrationTests(unittest.TestCase):
    """crew_observe is a tool in the `crew` toolset and /crew-observe a plain plugin command (no model call)."""

    def plugin(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("crew_plugin_observe", str(REPO / "__init__.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_register_exposes_the_tool_and_the_command(self):
        mod = self.plugin()

        class Ctx:
            def __init__(self):
                self.tools, self.commands = [], []

            def register_tool(self, name, toolset, schema, handler, description="", **kw):
                self.tools.append((name, toolset, handler))

            def register_command(self, name, handler, description="", args_hint=""):
                self.commands.append((name, handler))

            def register_skill(self, *a, **k):
                pass

            def register_hook(self, *a, **k):
                pass

        ctx = Ctx()
        mod.register(ctx)
        tools = {n: (ts, h) for n, ts, h in ctx.tools}
        self.assertIn("crew_observe", tools)
        self.assertEqual(tools["crew_observe"][0], "crew")
        self.assertIn("crew-observe", [n for n, _h in ctx.commands])

    def test_manifest_declares_the_tool(self):
        text = (REPO / "plugin.yaml").read_text(encoding="utf-8")
        self.assertIn("  - crew_observe\n", text)

    def test_command_rejects_a_bad_card_id_and_runs_the_script_otherwise(self):
        mod = self.plugin()
        handler = mod._option_handler("observe")
        self.assertIn("Usage: /crew-observe", handler("not a card; rm -rf"))
        with mock.patch.object(mod.subprocess, "run") as run:
            run.return_value = mock.Mock(returncode=0, stdout="[RESULT] observed=0", stderr="")
            out = handler(" t_ab12cd34 ")
        argv = run.call_args[0][0]
        self.assertTrue(argv[1].endswith("crew_observe.py"), argv)
        self.assertEqual(argv[2:], ["t_ab12cd34"])
        self.assertIn("[RESULT] observed=0", out)

    def test_tool_handler_dry_run_on_an_empty_board(self):
        import native_tools
        with tempfile.TemporaryDirectory() as tmp:
            _kb, conn, db = K.open_board(tmp)
            conn.close()
            res = native_tools.handle_crew_observe({"dry_run": True, "db_path": db})
        self.assertEqual(res["status"], "ok", res)
        self.assertEqual(res["eligible"], [])
        bad = native_tools.handle_crew_observe({"card_id": "../x"})
        self.assertEqual(bad["status"], "error")


class DefaultRunnerTests(BoardCase):
    """The real path: Hermes safety floors, then crew_proc.run_bounded in the proof shell."""

    def test_default_runner_executes_the_proof_through_run_bounded(self):
        ok = self.done_card("exit 0")
        bad = self.done_card("exit 3")
        res = O.observe_delivered(db_path=self.db, state_path=self.state, send=self.sender,
                                  notify_state_path=self.notify_state, clock=lambda: self.now, timeout_s=60)
        self.assertEqual(res["results"][ok]["status"], "improved", res)
        self.assertEqual(res["results"][bad]["status"], "regressed", res)
        self.assertEqual(res["results"][bad]["exit_code"], 3)
        self.assertEqual(len(self.sender.calls), 1)


class RegressionTextTests(unittest.TestCase):
    def test_text_is_bounded_and_redacts_secrets(self):
        task = {"id": "t_x", "title": "a card", "body": ""}
        obs = {"exit_code": 1, "timed_out": False, "proof_cmd": "pytest -q",
               "output": "z" * 5000 + " token=sk-abcdef0123456789 FAILED test_x"}
        text = crew_notify.regression_text(task, obs)
        self.assertIn("t_x", text)
        self.assertIn("[redacted]", text)
        self.assertNotIn("sk-abcdef0123456789", text)
        self.assertLess(len(text), 1500)


if __name__ == "__main__":
    unittest.main()

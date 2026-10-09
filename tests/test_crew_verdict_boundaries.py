import os
import sys
import tempfile
import unittest
from unittest import mock

# Ensure scripts dir is on sys.path
scripts_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)

import crew_card
import crew_graph_serve


class CrewVerdictBoundariesTests(unittest.TestCase):
    def test_cmd_verdict_refuses_non_crew_card_without_recording_verdict(self):
        """When a card has no owner-confirmed proof command and is NOT a crew contract card,
        cmd_verdict must exit with code 1 and must NOT record a FAIL verdict to disk."""
        non_crew_body = "Regular task body without crew headers\nDone when: test passes"
        fake_row = ("t_test_noncrew", "Test non-crew card", "todo", "coder", non_crew_body)

        with mock.patch("crew_card.card_row", return_value=fake_row), \
             mock.patch("crew_card.close_proof_command", return_value=""), \
             mock.patch("crew_card.record_verdict") as mock_record:

            args = mock.Mock()
            args.card = "t_test_noncrew"
            args.command = ""
            args.by = "coder"
            args.timeout = 20

            rc = crew_card.cmd_verdict(args)
            self.assertEqual(1, rc)
            mock_record.assert_not_called()

    def test_cmd_verdict_records_fail_for_real_crew_card_without_proof(self):
        """When a real crew contract card has no owner-confirmed proof command,
        cmd_verdict records a FAIL line (preserving existing strict contract behavior)."""
        crew_body = "Role: worker\nCoordinator: default\nproof command: \nDone when: complete"
        fake_row = ("t_test_crew", "Test crew card", "todo", "coder", crew_body)

        with mock.patch("crew_card.card_row", return_value=fake_row), \
             mock.patch("crew_card.close_proof_command", return_value=""), \
             mock.patch("crew_card.rework_fails", return_value=1), \
             mock.patch("crew_card.record_verdict", return_value={"verdict": "FAIL"}) as mock_record:

            args = mock.Mock()
            args.card = "t_test_crew"
            args.command = ""
            args.by = "coder"
            args.timeout = 20

            rc = crew_card.cmd_verdict(args)
            self.assertEqual(1, rc)
            mock_record.assert_called_once()

    def test_tile_verdict_returns_none_for_non_crew_card(self):
        """tile_verdict returns None for non-crew cards, even if rogue verdict lines exist."""
        non_crew_body = "Just an ad-hoc card"
        db = "mock.db"
        rogue_verdicts = [{
            "ts": 1000.0,
            "card": "t_adhoc",
            "verdict": "FAIL",
            "rc": 1
        }]

        with mock.patch("crew_graph_serve.CG.crew_card.all_verdicts", return_value=rogue_verdicts), \
             mock.patch("crew_graph_serve.CG.load_task_events", return_value=[("claimed", 2000.0, None)]):
            res = crew_graph_serve.tile_verdict(db, "t_adhoc", non_crew_body)
            self.assertIsNone(res)

    def test_tile_verdict_returns_chip_for_crew_card(self):
        """tile_verdict returns verdict status for actual crew cards."""
        crew_body = "Role: worker\nCoordinator: default\nVerifier: crew-verifier"
        db = "mock.db"
        pass_verdicts = [{
            "ts": 2500.0,
            "card": "t_crew",
            "verdict": "PASS",
            "rc": 0
        }]

        with mock.patch("crew_graph_serve.CG.crew_card.all_verdicts", return_value=pass_verdicts), \
             mock.patch("crew_graph_serve.CG.load_task_events", return_value=[("claimed", 2000.0, None)]), \
             mock.patch("crew_graph_serve.CG.crew_card.verdict_lines", return_value=pass_verdicts):
            res = crew_graph_serve.tile_verdict(db, "t_crew", crew_body)
            self.assertEqual("PASS", res)


if __name__ == "__main__":
    unittest.main()

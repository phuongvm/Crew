import os
import sys
import tempfile
import unittest
from unittest import mock

# Ensure scripts dir is on sys.path
scripts_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)

import crew_safety


class CrewSafetyResolutionTests(unittest.TestCase):
    def test_non_openspec_command_preserves_caller_cwd_when_none(self):
        """When run_proof is called with cwd=None and a non-openspec command,
        it must execute in the caller's working directory, not in a fixed workspace root."""
        with tempfile.TemporaryDirectory(prefix="crew-cwd-test-") as td:
            orig_cwd = os.getcwd()
            os.chdir(td)
            try:
                cmd = "python -c \"import os; print(os.getcwd())\""
                res = crew_safety.run_proof(cmd, cwd=None, timeout=20, mode="brave")
                self.assertEqual(0, res.rc)
                self.assertEqual(os.path.realpath(td), os.path.realpath(res.out.strip()))
            finally:
                os.chdir(orig_cwd)

    def test_relative_path_resolves_to_ancestor_root_when_missing_in_caller_cwd(self):
        """When relative paths in cmd are missing in caller cwd, run_proof resolves to ancestor root."""
        with tempfile.TemporaryDirectory(prefix="crew-ancestor-test-") as td:
            # create ancestor workspace structure
            sub_pkg = os.path.join(td, "pkg", "desktop")
            os.makedirs(sub_pkg, exist_ok=True)
            target_file = os.path.join(sub_pkg, "dummy.js")
            with open(target_file, "w") as f:
                f.write("// dummy")

            caller_dir = os.path.join(td, "scripts", "subdir")
            os.makedirs(caller_dir, exist_ok=True)

            orig_cwd = os.getcwd()
            os.chdir(caller_dir)
            try:
                with mock.patch.dict(os.environ, {"WORKSPACE": td}):
                    cmd = "node --check pkg/desktop/dummy.js"
                    res = crew_safety.run_proof(cmd, cwd=None, timeout=20, mode="safe")
                    self.assertEqual(0, res.rc)
            finally:
                os.chdir(orig_cwd)

    def test_openspec_command_resolves_change_directory(self):
        """When run_proof has cwd=None and an openspec command,
        it resolves the directory containing openspec/changes/<change_name>."""
        resolved = crew_safety._resolve_openspec_cwd("integrate-crew-desktop-dashboard")
        self.assertIsNotNone(resolved)
        expected_spec_dir = os.path.join(resolved, "openspec", "changes", "integrate-crew-desktop-dashboard")
        self.assertTrue(os.path.isdir(expected_spec_dir))

    def test_openspec_cwd_resolution_portable_in_mock_tree(self):
        """Resolution works in an arbitrary mock directory tree without hardcoded paths."""
        with tempfile.TemporaryDirectory(prefix="crew-mock-ws-") as td:
            change_dir = os.path.join(td, "repo_a", "openspec", "changes", "sample-change")
            os.makedirs(change_dir, exist_ok=True)

            with mock.patch.dict(os.environ, {"WORKSPACE": td}):
                resolved = crew_safety._resolve_openspec_cwd("sample-change")
                self.assertIsNotNone(resolved)
                self.assertEqual(os.path.realpath(os.path.join(td, "repo_a")), os.path.realpath(resolved))

    def test_no_hardcoded_drive_or_workspace_paths_in_module(self):
        """crew_safety.py must not contain hardcoded O:/ paths or hardcoded machine directories."""
        safety_path = os.path.join(scripts_dir, "crew_safety.py")
        with open(safety_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Must not contain hardcoded drive path references
        self.assertNotIn("O:/", content)
        self.assertNotIn("O:\\", content)
        self.assertNotIn(".venv/Lib/site-packages", content)

    def test_base_home_resolution(self):
        """_base_home strips the 'profiles/<name>' component if present."""
        with tempfile.TemporaryDirectory(prefix="crew-home-test-") as td:
            profile_dir = os.path.join(td, "profiles", "reviewer")
            os.makedirs(profile_dir, exist_ok=True)
            with mock.patch.dict(os.environ, {"HERMES_HOME": profile_dir}):
                self.assertEqual(os.path.realpath(td), os.path.realpath(crew_safety._base_home()))

            with mock.patch.dict(os.environ, {"HERMES_HOME": td}):
                self.assertEqual(os.path.realpath(td), os.path.realpath(crew_safety._base_home()))

    def test_hermes_loader_fails_closed_when_dependencies_missing(self):
        """When tools.approval_detection fails to import, _hermes raises ImportError with a helpful message."""
        with mock.patch.dict("sys.modules", {"tools.approval_detection": None}):
            with self.assertRaises(ImportError) as ctx:
                crew_safety._hermes()
            self.assertIn("Hermes safety checks could not be loaded", str(ctx.exception))
            self.assertIn("Hermes venv interpreter", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()

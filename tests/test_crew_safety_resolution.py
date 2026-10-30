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
        it resolves the directory containing openspec/changes/<change_name> or archive."""
        import glob
        resolved = crew_safety._resolve_openspec_cwd("integrate-crew-desktop-dashboard")
        self.assertIsNotNone(resolved)
        active_spec_dir = os.path.join(resolved, "openspec", "changes", "integrate-crew-desktop-dashboard")
        arch_matches = glob.glob(os.path.join(resolved, "openspec", "changes", "archive", "*integrate-crew-desktop-dashboard*"))
        self.assertTrue(os.path.isdir(active_spec_dir) or (len(arch_matches) > 0 and os.path.isdir(arch_matches[0])))

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

    def test_find_hermes_sources_accepts_only_real_checkouts(self):
        """A dir without hermes_cli/__init__.py (e.g. debris from a failed install) never becomes a Hermes
        source, so proof_env() never puts it on the proof PYTHONPATH; a real checkout is still found."""
        with tempfile.TemporaryDirectory(prefix="crew-src-test-") as td:
            debris = os.path.join(td, "debris")
            os.makedirs(os.path.join(debris, "venv"))
            with open(os.path.join(debris, "half.txt"), "w") as f:
                f.write("left from the failed install")
            checkout = os.path.join(td, "checkout")
            os.makedirs(os.path.join(checkout, "hermes_cli"))
            with open(os.path.join(checkout, "hermes_cli", "__init__.py"), "w") as f:
                f.write("")

            with mock.patch.dict(os.environ, {"HERMES_AGENT_SRC": debris}):
                self.assertNotIn(os.path.abspath(debris), crew_safety._find_hermes_sources())
            with mock.patch.dict(os.environ, {"HERMES_AGENT_SRC": checkout}):
                self.assertIn(os.path.abspath(checkout), crew_safety._find_hermes_sources())

    def test_find_hermes_sources_resolves_links_to_the_real_checkout(self):
        """A Hermes home often holds `hermes-agent` as a link to the real checkout. The source must be the
        link's target, listed once: the lexical path sits inside the Hermes home, and on the proof PYTHONPATH the
        hermes-agent tests' real-home I/O guard refuses it (importlib.metadata stats every sys.path entry)."""
        with tempfile.TemporaryDirectory(prefix="crew-src-link-") as td:
            checkout = os.path.join(td, "checkout")
            os.makedirs(os.path.join(checkout, "hermes_cli"))
            with open(os.path.join(checkout, "hermes_cli", "__init__.py"), "w") as f:
                f.write("")
            home = os.path.join(td, "home")
            os.makedirs(home)
            link = os.path.join(home, "hermes-agent")
            if sys.platform == "win32":
                import subprocess
                subprocess.run(["cmd", "/c", "mklink", "/J", link, checkout], check=True, capture_output=True)
            else:
                os.symlink(checkout, link)
            real = os.path.realpath(checkout)

            with mock.patch.dict(os.environ, {"HERMES_AGENT_SRC": link, "HERMES_AGENT_DIR": checkout}):
                sources = crew_safety._find_hermes_sources()
            self.assertIn(real, sources)
            self.assertNotIn(os.path.abspath(link), sources)
            self.assertEqual(1, sum(1 for s in sources if os.path.normcase(s) == os.path.normcase(real)))

    def test_proof_env_adds_only_site_packages_matching_proof_python_version(self):
        """proof_env(cmd=...) keeps pure-Python Hermes source checkouts on PYTHONPATH for any interpreter,
        includes site-packages whose pyvenv.cfg version matches the proof interpreter, and excludes
        site-packages from mismatched Python minor versions (e.g. cp314 vs cp312)."""
        with tempfile.TemporaryDirectory(prefix="crew-pyver-") as td:
            home = os.path.join(td, "home")
            env314_v = os.path.join(home, "installs", "i1", "environments", "e314", "venv")
            sp314 = os.path.join(env314_v, "Lib", "site-packages")
            os.makedirs(sp314)
            with open(os.path.join(env314_v, "pyvenv.cfg"), "w", encoding="utf-8") as fh:
                fh.write("version_info = 3.14.9\n")

            env312_v = os.path.join(home, "installs", "i1", "environments", "e312", "venv")
            sp312 = os.path.join(env312_v, "Lib", "site-packages")
            os.makedirs(sp312)
            with open(os.path.join(env312_v, "pyvenv.cfg"), "w", encoding="utf-8") as fh:
                fh.write("version_info = 3.12.11\n")

            checkout = os.path.join(td, "hermes-src")
            os.makedirs(os.path.join(checkout, "hermes_cli"))
            with open(os.path.join(checkout, "hermes_cli", "__init__.py"), "w", encoding="utf-8") as fh:
                fh.write("")
            src_venv314 = os.path.join(checkout, "venv")
            src_sp314 = os.path.join(src_venv314, "Lib", "site-packages")
            os.makedirs(src_sp314)
            with open(os.path.join(src_venv314, "pyvenv.cfg"), "w", encoding="utf-8") as fh:
                fh.write("version = 3.14.2\n")

            proof_venv = os.path.join(td, "proj-venv")
            proof_scripts = os.path.join(proof_venv, "Scripts")
            os.makedirs(proof_scripts)
            with open(os.path.join(proof_venv, "pyvenv.cfg"), "w", encoding="utf-8") as fh:
                fh.write("version_info = 3.12.11\n")
            proof_py = os.path.join(proof_scripts, "python.exe")
            with open(proof_py, "w", encoding="utf-8") as fh:
                fh.write("")

            with mock.patch.dict(os.environ, {"HERMES_HOME": home, "HERMES_AGENT_SRC": checkout}), \
                 mock.patch.object(crew_safety, "_hermes", side_effect=ImportError("isolated")):
                env_312 = crew_safety.proof_env(cmd='"%s" -m pytest tests -q' % proof_py.replace("\\", "/"))
                pp_312 = [os.path.normcase(p) for p in env_312.get("PYTHONPATH", "").split(os.pathsep) if p]
                self.assertIn(os.path.normcase(os.path.realpath(checkout)), pp_312)
                self.assertIn(os.path.normcase(os.path.realpath(sp312)), pp_312)
                self.assertNotIn(os.path.normcase(os.path.realpath(sp314)), pp_312)
                self.assertNotIn(os.path.normcase(os.path.realpath(src_sp314)), pp_312)

                proof_py314 = os.path.join(env314_v, "Scripts", "python.exe")
                os.makedirs(os.path.dirname(proof_py314), exist_ok=True)
                with open(proof_py314, "w", encoding="utf-8") as fh:
                    fh.write("")
                with crew_safety.proof_cmd_scope('"%s" -m pytest -q' % proof_py314):
                    env_314 = crew_safety.proof_env()
                pp_314 = [os.path.normcase(p) for p in env_314.get("PYTHONPATH", "").split(os.pathsep) if p]
                self.assertIn(os.path.normcase(os.path.realpath(checkout)), pp_314)
                self.assertIn(os.path.normcase(os.path.realpath(sp314)), pp_314)
                self.assertIn(os.path.normcase(os.path.realpath(src_sp314)), pp_314)
                self.assertNotIn(os.path.normcase(os.path.realpath(sp312)), pp_314)


if __name__ == "__main__":
    unittest.main()

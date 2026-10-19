"""One version for the whole package: plugin.yaml's.

Issue #15: plugin.yaml said 0.9.11 while skills/crew/SKILL.md said 0.8.1 and the role skills 0.2.0, and every
version-shaped check (install.py --check's headline included) read plugin.yaml only, so a skill whose body
changed and whose frontmatter did not looked current. The skill body is the text an agent copies into tool
calls, so its version is pinned to the release here.
"""
import json
import os
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def plugin_version():
    return re.search(r"^version:\s*(\S+)", (REPO / "plugin.yaml").read_text(encoding="utf-8"), re.M).group(1)


def plugin_tools():
    text = (REPO / "plugin.yaml").read_text(encoding="utf-8")
    m = re.search(r"provides_tools:\n((?:\s+-\s+\S+\n?)+)", text)
    if not m:
        return []
    return re.findall(r"-\s+(\S+)", m.group(1))


class VersionTests(unittest.TestCase):
    def test_every_shipped_skill_carries_the_plugin_version(self):
        want = plugin_version()
        skills = sorted((REPO / "skills").glob("*/SKILL.md"))
        self.assertTrue(skills)
        for p in skills:
            m = re.search(r"^version:\s*(\S+)", p.read_text(encoding="utf-8"), re.M)
            self.assertIsNotNone(m, "%s has no version line" % p.parent.name)
            self.assertEqual(want, m.group(1), "%s/SKILL.md version" % p.parent.name)

    def test_every_registered_tool_is_documented_in_shipped_skills(self):
        tools = plugin_tools()
        self.assertEqual(17, len(tools), "plugin.yaml must register exactly 17 tools")
        skills = sorted((REPO / "skills").glob("*/SKILL.md"))
        skill_texts = [p.read_text(encoding="utf-8") for p in skills]
        for tool in tools:
            found = any(tool in text for text in skill_texts)
            self.assertTrue(found, f"Tool {tool} is missing from all shipped skills under skills/*/SKILL.md")

    def test_every_force_loaded_skill_in_card_templates_exists(self):
        skills = sorted((REPO / "skills").glob("*/SKILL.md"))
        shipped_skill_names = {p.parent.name for p in skills}
        discovered_skills = set(shipped_skill_names)
        candidate_roots = [
            REPO.parents[1] / ".agents" / "skills",
            REPO.parents[1] / "rules" / "skills",
            Path(os.environ.get("HERMES_HOME", "")) / "skills",
            Path(r"O:/workspaces/.agents/skills"),
            Path(r"O:/workspaces/rules/skills"),
            Path(r"O:/workspaces/_config/agent4070/hermes/skills"),
        ]
        for root in candidate_roots:
            if root and root.exists():
                for item in root.iterdir():
                    if item.is_dir() and (item / "SKILL.md").exists():
                        discovered_skills.add(item.name)
        known_valid_skills = discovered_skills or (shipped_skill_names | {"openspec-verifier", "openspec-developer", "sdlc-review"})
        for p in skills:
            content = p.read_text(encoding="utf-8")
            for m in re.finditer(r'skills\s*=\s*\[([^\]]+)\]', content):
                raw_names = re.findall(r'["\']([^"\']+)["\']', m.group(1))
                for name in raw_names:
                    self.assertIn(
                        name,
                        known_valid_skills,
                        f"Skill '{name}' referenced in {p.parent.name}/SKILL.md does not exist in shipped or valid skill registry",
                    )

    def test_the_readme_badge_and_the_dashboard_manifest_match(self):
        want = plugin_version()
        badge = re.search(r"badge/version-([0-9.]+)-", (REPO / "README.md").read_text(encoding="utf-8"))
        self.assertEqual(want, badge.group(1), "README version badge")
        manifest = REPO / "dashboard" / "manifest.json"
        if manifest.exists():
            self.assertEqual(want, json.loads(manifest.read_text(encoding="utf-8")).get("version"))

    def test_the_registered_verifier_skill_reads_its_version_instead_of_a_literal(self):
        src = (REPO / "__init__.py").read_text(encoding="utf-8")
        self.assertNotRegex(src, r'frontmatter=\{"version":\s*"[0-9.]+"\}')

    def test_documented_tool_call_signatures_match_registered_schemas(self):
        import importlib
        import sys
        scripts_dir = str(REPO / "scripts")
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        crew_tools = importlib.import_module("crew_tools")
        import native_tools

        schemas = {}
        for name, schema, _ in native_tools.CREW_NATIVE_TOOLS:
            schemas[name] = schema
        for name, schema, _ in native_tools.CREW_EXTENDED_TOOLS:
            schemas[name] = schema
        for name, schema in crew_tools.SCHEMAS.items():
            if name not in schemas:
                schemas[name] = schema

        self.assertEqual(17, len(schemas), "Must have all 17 registered tool schemas")

        skills = sorted((REPO / "skills").glob("*/SKILL.md"))
        call_pattern = re.compile(r'(crew_[a-z_]+)\(([^)]*)\)')
        for p in skills:
            content = p.read_text(encoding="utf-8")
            for m in call_pattern.finditer(content):
                tool_name = m.group(1)
                args_str = m.group(2)
                self.assertIn(tool_name, schemas, f"Unknown tool {tool_name} called in {p.name}")
                allowed_props = set(schemas[tool_name]["parameters"].get("properties", {}).keys())
                arg_names = re.findall(r'([a-z_]+)\s*=', args_str)
                for arg in arg_names:
                    self.assertIn(
                        arg,
                        allowed_props,
                        f"Argument '{arg}' in {tool_name}(...) in {p.parent.name}/SKILL.md is not in schema properties {allowed_props}",
                    )
            for line in content.splitlines():
                if not line.startswith("|") or "---" in line or "Arguments" in line:
                    continue
                for tool_name, schema in schemas.items():
                    if f"`{tool_name}`" in line:
                        allowed_props = set(schema["parameters"].get("properties", {}).keys())
                        arg_names = re.findall(r'([a-z_]+)\s*=', line)
                        for arg in arg_names:
                            self.assertIn(
                                arg,
                                allowed_props,
                                f"Table argument '{arg}' for {tool_name} in {p.parent.name}/SKILL.md is not in schema properties {allowed_props}",
                            )

    def test_installed_skills_byte_identical_parity(self):
        import hashlib
        installed_root = Path(r"O:/workspaces/_config/agent4070/hermes/skills/crew")
        if not installed_root.exists():
            return
        skills = sorted((REPO / "skills").glob("*/SKILL.md"))
        for p in skills:
            inst = installed_root / p.parent.name / "SKILL.md"
            self.assertTrue(inst.exists(), f"Installed skill missing: {inst}")
            h1 = hashlib.sha256(p.read_bytes()).hexdigest()
            h2 = hashlib.sha256(inst.read_bytes()).hexdigest()
            self.assertEqual(h1, h2, f"Parity mismatch for {p.parent.name}/SKILL.md")


if __name__ == "__main__":
    unittest.main()

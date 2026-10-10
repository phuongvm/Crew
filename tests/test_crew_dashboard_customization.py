import unittest
import os
import re

HERE = os.path.dirname(__file__)
CREW_ROOT = os.path.dirname(HERE)


class CrewDashboardCustomizationTests(unittest.TestCase):
    def test_tokens_css_hermes_teal_defaults(self):
        tokens_path = os.path.join(CREW_ROOT, "scripts", "crew_dashboard", "tokens.css")
        with open(tokens_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("--crew-bg: var(--color-background, var(--dt-background, #041c1c));", content)
        self.assertIn("--crew-fg: var(--color-foreground, var(--ui-base, #ffffff));", content)

    def test_graph_serve_link_target_blank(self):
        serve_path = os.path.join(CREW_ROOT, "scripts", "crew_graph_serve.py")
        with open(serve_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("target='_blank'", content)
        self.assertIn("open in new tab ↗", content)
        self.assertIn("frame-ancestors 'self' file: app: vscode-file: http://127.0.0.1:* http://localhost:*", content)

    def test_plugin_api_proxy_rules(self):
        api_path = os.path.join(CREW_ROOT, "dashboard", "plugin_api.py")
        with open(api_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("hermes-theme-sync", content)
        self.assertIn("#041c1c", content)
        self.assertIn("open in new tab ↗", content)
        self.assertIn('<base href="/api/plugins/crew/">', content)
        self.assertIn("@router.api_route(\"/avatars/{path:path}\"", content)
        self.assertIn("_public_crew_url", content)
        self.assertIn('html.replace(\'href="/"\', \'href="board"\')', content)
        self.assertIn('res.set_cookie', content)
        self.assertIn('hermes_session', content)
        self.assertIn('path="/api/plugins/crew/"', content)
        self.assertIn('samesite="lax"', content)
        self.assertIn('get_board', content)
        self.assertIn('token = request.query_params.get("token")', content)

    def test_avatar_fallback_and_relative_path(self):
        board_path = os.path.join(CREW_ROOT, "scripts", "crew_dashboard", "board.js")
        with open(board_path, "r", encoding="utf-8") as f:
            board_js = f.read()
        self.assertIn("avatar fallback", board_js)
        self.assertIn("onerror=", board_js)

        lib_path = os.path.join(CREW_ROOT, "scripts", "crew_dashboard", "lib.js")
        with open(lib_path, "r", encoding="utf-8") as f:
            lib_js = f.read()
        self.assertIn('return "avatars/role/"', lib_js)

    def test_config_yaml_board_resolution(self):
        graph_path = os.path.join(CREW_ROOT, "scripts", "crew_graph.py")
        with open(graph_path, "r", encoding="utf-8") as f:
            graph_py = f.read()
        self.assertIn('crew_card.config_value("board")', graph_py)

        card_path = os.path.join(CREW_ROOT, "scripts", "crew_card.py")
        with open(card_path, "r", encoding="utf-8") as f:
            card_py = f.read()
        self.assertIn('config_value("board")', card_py)

    def test_detail_card_theme_synchronization(self):
        card_js_path = os.path.join(CREW_ROOT, "scripts", "crew_dashboard", "card.js")
        with open(card_path := card_js_path, "r", encoding="utf-8") as f:
            card_js = f.read()
        self.assertIn("applyDynamicTheme", card_js)
        self.assertIn("hermes:theme", card_js)
        self.assertIn("page-card", card_js)
        self.assertIn("preserveThemeLinks", card_js)

        board_js_path = os.path.join(CREW_ROOT, "scripts", "crew_dashboard", "board.js")
        with open(board_js_path, "r", encoding="utf-8") as f:
            board_js = f.read()
        self.assertIn("applyDynamicTheme", board_js)
        self.assertIn("hermes:theme", board_js)
        self.assertIn("href=\"/card/'+esc(t.id)+q+'\"", board_js)
        self.assertIn("href=\"/card/'+esc(r.id)+q+'\"", board_js)

        api_path = os.path.join(CREW_ROOT, "dashboard", "plugin_api.py")
        with open(api_path, "r", encoding="utf-8") as f:
            api_py = f.read()
        self.assertIn("appendToken", api_py)
        self.assertIn("page-card", api_py)
        self.assertIn("['theme', 'bg', 'fg']", api_py)

    # Board names the owner has used; none of them may be baked into the title code paths.
    HARDCODED_NAMES = ("Custom Crew", "Crew Board", "crew board")

    def _read(self, *parts):
        with open(os.path.join(CREW_ROOT, *parts), "r", encoding="utf-8") as f:
            return f.read()

    def _load_serve(self):
        import importlib.util
        import sys
        sys.path.insert(0, os.path.join(CREW_ROOT, "scripts"))
        spec = importlib.util.spec_from_file_location(
            "cgs_test", os.path.join(CREW_ROOT, "scripts", "crew_graph_serve.py"))
        assert spec is not None and spec.loader is not None
        cgs = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cgs)
        return cgs

    def _with_home(self, home, fn, board_env=None):
        keys = ("HERMES_HOME", "HERMES_KANBAN_BOARD", "HERMES_KANBAN_DB", "KANBAN_DB")
        saved = {k: os.environ.get(k) for k in keys}
        os.environ["HERMES_HOME"] = home
        for k in ("HERMES_KANBAN_DB", "KANBAN_DB"):
            os.environ.pop(k, None)
        if board_env is None:
            os.environ.pop("HERMES_KANBAN_BOARD", None)
        else:
            os.environ["HERMES_KANBAN_BOARD"] = board_env
        try:
            return fn()
        finally:
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    def _make_board(self, home, slug, name=None):
        import json
        d = os.path.join(home, "kanban", "boards", slug)
        os.makedirs(d, exist_ok=True)
        if name is not None:
            with open(os.path.join(d, "board.json"), "w", encoding="utf-8-sig") as f:
                json.dump({"slug": slug, "name": name}, f)

    def _graph(self):
        import sys
        sys.path.insert(0, os.path.join(CREW_ROOT, "scripts"))
        import crew_graph as cg
        return cg

    def test_no_hardcoded_board_names_in_title_code(self):
        for parts in (("scripts", "crew_dashboard", "board.js"), ("desktop", "plugin.js"),
                      ("scripts", "crew_graph_serve.py"), ("scripts", "crew_graph.py")):
            src = self._read(*parts)
            for name in self.HARDCODED_NAMES:
                self.assertNotIn(name, src, "%s hardcodes board name %r" % ("/".join(parts), name))
        self.assertNotIn("useState('Crew", self._read("desktop", "plugin.js"))

    def test_board_title_text_is_the_name_as_given(self):
        cgs = self._load_serve()
        self.assertEqual(cgs.board_title_text("Ops Queue"), "Ops Queue")
        self.assertEqual(cgs.board_title_text("  skills-kb "), "skills-kb")
        self.assertEqual(cgs.board_title_text(""), "Board")
        self.assertEqual(cgs.board_title_text(None), "Board")

    def test_formatted_board_slug_fallback(self):
        cg = self._graph()
        self.assertEqual(cg.formatted_board_slug("default"), "Default Board")
        self.assertEqual(cg.formatted_board_slug("skills-kb"), "Skills Kb Board")
        self.assertEqual(cg.formatted_board_slug("night_board"), "Night Board")
        self.assertEqual(cg.formatted_board_slug(""), "Board")
        self.assertEqual(cg.formatted_board_slug(None), "Board")

    def test_active_board_name_reads_board_json_live(self):
        import json
        import tempfile
        cg = self._graph()
        with tempfile.TemporaryDirectory() as home:
            self._make_board(home, "ops", "Ops Queue")
            self._make_board(home, "bare", "")
            with open(os.path.join(home, "kanban", "board.json"), "w", encoding="utf-8") as f:
                json.dump({"name": "Main Queue"}, f)

            def check():
                self.assertEqual(cg.active_board_name("ops"), "Ops Queue")
                self.assertEqual(cg.active_board_name("bare"), "Bare Board")
                self.assertEqual(cg.active_board_name("missing-one"), "Missing One Board")
                self.assertEqual(cg.active_board_name("default"), "Main Queue")
                # A rename in board.json shows on the next read: nothing is cached or baked in.
                with open(os.path.join(home, "kanban", "boards", "ops", "board.json"), "w",
                          encoding="utf-8") as f:
                    json.dump({"slug": "ops", "name": "Renamed Ops"}, f)
                self.assertEqual(cg.active_board_name("ops"), "Renamed Ops")
            self._with_home(home, check)

    def test_active_board_follows_current_pointer(self):
        import tempfile
        cg = self._graph()
        orig = cg.crew_card.config_value
        cg.crew_card.config_value = lambda *a, **k: None
        try:
            with tempfile.TemporaryDirectory() as home:
                self._make_board(home, "night-shift", "Night Shift Team")
                with open(os.path.join(home, "kanban", "current"), "w", encoding="utf-8") as f:
                    f.write("night-shift\n")

                def check():
                    self.assertEqual(cg.active_board_slug(), "night-shift")
                    self.assertEqual(cg.active_board_name(), "Night Shift Team")
                self._with_home(home, check)

                # The env pin wins over the pointer.
                self._make_board(home, "pinned", "Pinned Name")
                self._with_home(home, lambda: self.assertEqual(cg.active_board_name(), "Pinned Name"),
                                board_env="pinned")
            with tempfile.TemporaryDirectory() as home:
                # Nothing configured at all: the default board, shown as its formatted slug.
                def check_default():
                    self.assertEqual(cg.active_board_slug(), "default")
                    self.assertEqual(cg.active_board_name(), "Default Board")
                self._with_home(home, check_default)
        finally:
            cg.crew_card.config_value = orig

    def test_board_page_renders_active_board_name(self):
        import tempfile
        cgs = self._load_serve()
        with tempfile.TemporaryDirectory() as home:
            self._make_board(home, "ops", "Ops Queue")

            def check():
                orig = cgs.CG.kanban_db_path
                cgs.CG.kanban_db_path = lambda: None  # board metadata only; no task DB needed
                try:
                    data = cgs.board_data()
                    self.assertEqual(data["board"], "ops")
                    self.assertEqual(data["board_name"], "Ops Queue")
                    html = cgs.board_page()
                finally:
                    cgs.CG.kanban_db_path = orig
                self.assertIn("<title>Ops Queue</title>", html)
                for name in self.HARDCODED_NAMES:
                    self.assertNotIn(name, html)
            self._with_home(home, check, board_env="ops")

    def test_frontends_bind_title_to_board_payload(self):
        board_js = self._read("scripts", "crew_dashboard", "board.js")
        self.assertIn("d.board_name || d.board", board_js)
        self.assertIn('return name || "Board"', board_js)
        self.assertIn("board_name: boardTitle(d)", board_js)
        self.assertIn("document.title = title", board_js)
        self.assertIn("h1.textContent = title", board_js)

        plugin_js = self._read("desktop", "plugin.js")
        self.assertIn("React.useState('Board')", plugin_js)
        self.assertIn("e.data.board_name || e.data.board", plugin_js)
        self.assertIn("setBoardTitle(name)", plugin_js)
        self.assertIn("children: boardTitle", plugin_js)
        self.assertIn("title: boardTitle", plugin_js)

    def test_board_js_title_resolution_in_node(self):
        import shutil
        import subprocess
        node = shutil.which("node")
        if not node:
            self.skipTest("node not installed")
        src = self._read("scripts", "crew_dashboard", "board.js")
        start = src.index("function boardTitle(d)")
        fn = src[start:src.index("\n}", start) + 2]
        script = fn + (";console.log(JSON.stringify([boardTitle({board:'ops',board_name:'Ops Queue'}),"
                       "boardTitle({board:'ops'}),boardTitle({board_name:'  '}),boardTitle(null)]))")
        out = subprocess.run([node, "-e", script], capture_output=True, text=True, timeout=30)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.strip(), '["Ops Queue","ops","Board","Board"]')

    def test_card_view_contract_metadata_and_specification(self):
        card_js = self._read("scripts", "crew_dashboard", "card.js")
        self.assertIn("ev.goal", card_js)
        self.assertIn("ev.artifact", card_js)
        self.assertIn("ev.lands_at", card_js)
        self.assertIn("ev.inputs", card_js)
        self.assertIn("ev.proof_cmd", card_js)
        self.assertIn("Contract Specification &amp; Details", card_js)
        self.assertIn("ev.body", card_js)

        cg_src = self._read("scripts", "crew_graph.py")
        self.assertIn('"goal": body_field(body, "Goal")', cg_src)
        self.assertIn('"artifact": body_field(body, "Artifact")', cg_src)
        self.assertIn('"lands_at": body_field(body, "Lands at")', cg_src)
        self.assertIn('"inputs": body_field(body, "Inputs")', cg_src)
        self.assertIn('"proof_cmd": body_field(body, "proof command")', cg_src)
        self.assertIn('"body": body or ""', cg_src)

if __name__ == "__main__":
    unittest.main()

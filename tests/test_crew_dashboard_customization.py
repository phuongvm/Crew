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


if __name__ == "__main__":
    unittest.main()

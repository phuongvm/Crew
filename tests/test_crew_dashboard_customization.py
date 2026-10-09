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


if __name__ == "__main__":
    unittest.main()

"""Dashboard plugin proxy (dashboard/plugin_api.py) driven through FastAPI's TestClient.

Covers the PR #3 review: the escaped public host, the allowlisted routes, the
401 a caller without the dashboard session token gets from Hermes's own auth
middleware, the CSP + nonce on the page the tab renders via srcdoc, and an /ack
write that reaches a real crew_graph_serve and passes its same-origin check.
"""
import html
import json
import os
import re
import sys
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

HERE = os.path.dirname(os.path.abspath(__file__))
CREW_ROOT = os.path.dirname(HERE)
for p in (CREW_ROOT, os.path.join(CREW_ROOT, "scripts")):
    if p not in sys.path:
        sys.path.insert(0, p)

from dashboard import plugin_api  # noqa: E402
from dashboard.plugin_api import (  # noqa: E402
    router,
    _sanitize_color,
    _public_crew_url,
    _CARD_ID_RE,
    _ACK_PATH_RE,
    _AVATAR_PATH_RE,
)

UPSTREAM_CSP = ("default-src 'self'; script-src 'self' 'nonce-abc123'; style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data:; connect-src 'self'; base-uri 'none'; form-action 'none'; "
                "frame-ancestors 'none'")


def _load_hermes_auth():
    """Hermes's real web_server auth middleware, imported under a throwaway HERMES_HOME.

    None when hermes-agent is not installed (the crew suite also runs without it).
    """
    saved = {k: os.environ.get(k) for k in ("HERMES_HOME", "HERMES_DASHBOARD_SESSION_TOKEN")}
    os.environ["HERMES_HOME"] = tempfile.mkdtemp(prefix="crew-dash-home-")
    os.environ["HERMES_DASHBOARD_SESSION_TOKEN"] = "crew-test-session-token"
    try:
        import hermes_cli.web_server as ws
    except Exception:
        return None
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    if not hasattr(ws, "auth_middleware") or not hasattr(ws, "_SESSION_TOKEN"):
        return None
    return ws


def _mock_upstream(mock_urlopen, body, content_type, csp=None, status=200):
    resp = MagicMock()
    resp.read.return_value = body.encode("utf-8") if isinstance(body, str) else body
    resp.status = status
    headers = {"Content-Type": content_type}
    if csp:
        headers["Content-Security-Policy"] = csp
    resp.headers = headers
    mock_urlopen.return_value.__enter__.return_value = resp
    return resp


class CrewDashboardCustomizationTests(unittest.TestCase):
    def setUp(self):
        self.app = FastAPI()
        self.app.include_router(router, prefix="/api/plugins/crew")
        self.client = TestClient(self.app)

    def test_manifest_metadata(self):
        manifest_path = os.path.join(CREW_ROOT, "dashboard", "manifest.json")
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data.get("name"), "crew")
        self.assertEqual(data.get("tab", {}).get("path"), "/crew")
        self.assertEqual(data.get("entry"), "dist/index.js")
        self.assertEqual(data.get("api"), "plugin_api.py")
        # The tab ships with the plugin it belongs to: one version for both.
        with open(os.path.join(CREW_ROOT, "plugin.yaml"), "r", encoding="utf-8") as f:
            plugin_version = next(l.split(":", 1)[1].strip() for l in f if l.startswith("version:"))
        self.assertEqual(data.get("version"), plugin_version)

    def test_dist_index_js_never_holds_a_credential(self):
        with open(os.path.join(CREW_ROOT, "dashboard", "dist", "index.js"), "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("Hand-written ES5", content)
        for leak in ("_SESSION_TOKEN", "__HERMES_SESSION_TOKEN__", "X-Hermes-Session-Token", "token="):
            self.assertNotIn(leak, content)

    def test_color_sanitization_rejects_xss(self):
        self.assertEqual(_sanitize_color("#041c1c"), "#041c1c")
        self.assertEqual(_sanitize_color("#fff"), "#fff")
        self.assertEqual(_sanitize_color("#AABBCC"), "#aabbcc")
        for bad in ("</style><script>alert(1)</script>", "#041c1c; alert(1)", "red; background: blue",
                    "expression(alert(1))", "rgba(0,0,0,1)"):
            self.assertIsNone(_sanitize_color(bad), bad)

    def test_public_crew_url_sanitization(self):
        ok = MagicMock()
        ok.headers = {"host": "agent.example.com", "x-forwarded-proto": "https"}
        ok.url.scheme = "https"
        self.assertEqual(_public_crew_url(ok), "https://agent.example.com/api/plugins/crew/board")

        for host, proto in (('attacker.com" onclick="alert(1)', "javascript:alert(1)"),
                            ("evil.com/path", "http"), ("evil.com\\x", "http"), ("a b", "http"),
                            ("user@evil.com", "http"), ("evil.com'><script>", "https ")):
            hostile = MagicMock()
            hostile.headers = {"host": host, "x-forwarded-proto": proto}
            hostile.url.scheme = "http"
            url = _public_crew_url(hostile)
            self.assertRegex(url, r"^https?://127\.0\.0\.1:9119/api/plugins/crew/board$", host)

    def test_route_allowlisting_and_validation(self):
        self.assertTrue(_CARD_ID_RE.match("t_12345"))
        self.assertTrue(_CARD_ID_RE.match("card-abc_12"))
        self.assertTrue(_CARD_ID_RE.match("t_12345.json"))
        for bad in ("../../etc/passwd", "card/subpath", "t_1.json.json", "t_1.html", ".json"):
            self.assertFalse(_CARD_ID_RE.match(bad), bad)
        self.assertTrue(_ACK_PATH_RE.match("all"))
        self.assertTrue(_ACK_PATH_RE.match("t_12345"))
        self.assertFalse(_ACK_PATH_RE.match("all/extra"))
        self.assertTrue(_AVATAR_PATH_RE.match("role/worker.svg"))
        self.assertTrue(_AVATAR_PATH_RE.match("role/verifier.png"))
        self.assertFalse(_AVATAR_PATH_RE.match("../secret.txt"))
        self.assertFalse(_AVATAR_PATH_RE.match("role/worker.exe"))

    @patch("urllib.request.urlopen")
    def test_only_allowlisted_routes_reach_upstream(self, mock_urlopen):
        _mock_upstream(mock_urlopen, "{}", "application/json")
        for path in ("/api/plugins/crew/index.json", "/api/plugins/crew/scripts/crew_card.py",
                     "/api/plugins/crew/card/t_1/extra", "/api/plugins/crew/avatars/role/../../x.svg",
                     "/api/plugins/crew/card/t_1%3Fall%3D1", "/api/plugins/crew/card/..%2F..%2Fx"):
            self.assertIn(self.client.get(path).status_code, (400, 404, 405), path)
        self.assertEqual(self.client.get("/api/plugins/crew/ack/all").status_code, 405)   # writes are POST only
        mock_urlopen.assert_not_called()

    @patch("urllib.request.urlopen")
    def test_card_json_poll_is_proxied(self, mock_urlopen):
        _mock_upstream(mock_urlopen, '{"card_id": "t_abc"}', "application/json")
        resp = self.client.get("/api/plugins/crew/card/t_abc.json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"card_id": "t_abc"})
        self.assertEqual(mock_urlopen.call_args[0][0].full_url, "http://127.0.0.1:8799/card/t_abc.json")

    @patch("urllib.request.urlopen")
    def test_query_and_headers_forwarded_upstream_are_allowlisted(self, mock_urlopen):
        _mock_upstream(mock_urlopen, "{}", "application/json")
        self.client.get(
            "/api/plugins/crew/board.json?all=1&older=1&token=secret&x=%2F..",
            headers={"X-Hermes-Session-Token": "secret", "Authorization": "Bearer secret",
                     "Cookie": "hermes_session=secret", "X-Forwarded-For": "1.2.3.4",
                     "Tailscale-User-Login": "owner@example.com", "Accept": "application/json"},
        )
        req = mock_urlopen.call_args[0][0]
        self.assertEqual(req.full_url, "http://127.0.0.1:8799/board.json?all=1&older=1")
        sent = {k.lower(): v for k, v in req.header_items()}
        for name in ("x-hermes-session-token", "authorization", "cookie", "x-forwarded-for",
                     "tailscale-user-login"):
            self.assertNotIn(name, sent)
        self.assertNotIn("secret", json.dumps(sent))
        self.assertEqual(sent.get("accept"), "application/json")

    @patch("urllib.request.urlopen")
    def test_board_page_escapes_host_and_keeps_the_nonce_csp(self, mock_urlopen):
        upstream = (
            "<!doctype html><html><head><title>Crew</title></head><body>"
            "<span class=node>pc - kanban <a class=tailnet href='http://127.0.0.1:8799/'>link</a></span>"
            '<a href="/card/t_123">Task</a><a class="brand" href="/">Crew</a>'
            '<img src="/avatars/role/worker.svg">'
            '<script nonce="abc123">fetch("/board.json");'
            'function faceUrl(n){ return "/avatars/role/" + (n || "unknown") + ".svg"; }</script>'
            "</body></html>"
        )
        _mock_upstream(mock_urlopen, upstream, "text/html; charset=utf-8", csp=UPSTREAM_CSP)

        resp = self.client.get(
            "/api/plugins/crew/board?bg=%3C/style%3E%3Cscript%3Ealert(1)%3C/script%3E",
            headers={"X-Forwarded-Host": 'evil.com" onmouseover="alert(2)', "X-Forwarded-Proto": "javascript"},
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.text
        self.assertNotIn("alert(1)", body)
        self.assertNotIn("alert(2)", body)
        self.assertNotIn("javascript", body.split("crew-parent-bridge")[0])
        self.assertIn('href="http://127.0.0.1:9119/api/plugins/crew/board" target="_blank"', body)
        self.assertNotIn("set-cookie", resp.headers)

        # Header CSP: the upstream nonce policy, with base-uri opened for the injected <base>.
        csp = resp.headers.get("content-security-policy")
        self.assertIn("'nonce-abc123'", csp)
        self.assertIn("base-uri 'self'", csp)
        self.assertNotIn("base-uri 'none'", csp)
        # srcdoc never sees response headers: the same policy rides in a <meta>, minus frame-ancestors.
        self.assertIn('<meta http-equiv="Content-Security-Policy" content="default-src', body)
        self.assertNotIn("frame-ancestors", body)
        # Inside srcdoc 'self' is the dashboard origin: the meta policy's script-src is nonce-only.
        meta_m = re.search(r'<meta http-equiv="Content-Security-Policy" content="([^"]+)"', body)
        self.assertIsNotNone(meta_m)
        meta_policy = html.unescape(meta_m.group(1))
        script_src = re.search(r"script-src[^;]*", meta_policy).group(0)
        self.assertIn("'nonce-abc123'", script_src)
        self.assertNotIn("'self'", script_src)
        self.assertEqual(script_src.split(), ["script-src", "'nonce-abc123'"])
        # Only script-src loses 'self'; the other directives keep it.
        self.assertIn("default-src 'self'", meta_policy)
        self.assertIn("connect-src 'self'", meta_policy)
        # The header policy is untouched.
        self.assertIn("script-src 'self' 'nonce-abc123'", csp)
        # The injected bridge carries the page's nonce, so that policy lets it run.
        self.assertIn('<script id="crew-parent-bridge" nonce="abc123">', body)
        self.assertLess(body.index('<base href="/api/plugins/crew/">'), body.index("crew-parent-bridge"))
        # Root-absolute links are made relative to the <base>.
        self.assertIn('href="card/t_123"', body)
        self.assertIn('href="board"', body)
        self.assertIn('src="avatars/role/worker.svg"', body)
        self.assertIn('fetch("board.json")', body)
        # An <img> load carries no session header: inside the tab the bridge supplies the role face.
        self.assertIn('return window.__crewFace ? window.__crewFace(p) : p; }', body)

    @patch("urllib.request.urlopen")
    def test_upstream_down_answers_502_with_escaped_error(self, mock_urlopen):
        mock_urlopen.side_effect = OSError("<script>x</script>")
        resp = self.client.get("/api/plugins/crew/healthz")
        self.assertEqual(resp.status_code, 502)
        self.assertNotIn("<script>x", resp.text)


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

    def test_daemon_keeps_strict_framing_and_write_checks(self):
        """crew_graph_serve permits desktop/loopback framing while refusing writes from any other origin."""
        cgs = self._load_serve()
        policy = cgs.csp("n0nce")
        self.assertIn("frame-ancestors 'self' file: app: vscode-file: vscode-webview: http://127.0.0.1:* http://localhost:*", policy)
        for external in ("https://*", "http://*", "*"):
            self.assertNotIn(f"frame-ancestors {external}", policy)

        def allowed(host, origin=None, site=None):
            h = cgs.Handler.__new__(cgs.Handler)
            hdrs = {"Host": host}
            if origin is not None:
                hdrs["Origin"] = origin
            if site is not None:
                hdrs["Sec-Fetch-Site"] = site
            h.headers = hdrs
            return h._same_origin()

        self.assertTrue(allowed("127.0.0.1:8799", "http://127.0.0.1:8799", "same-origin"))
        self.assertTrue(allowed("127.0.0.1:8799", "http://127.0.0.1:8799"))
        self.assertFalse(allowed("127.0.0.1:8799"))                                   # no Origin/Referer
        self.assertFalse(allowed("127.0.0.1:8799", "http://127.0.0.1:9119", "same-site"))
        self.assertFalse(allowed("127.0.0.1:8799", "http://localhost:9119"))
        self.assertFalse(allowed("[::1]:8799", "http://[::1]:9119", "same-site"))
        self.assertFalse(allowed("127.0.0.1:8799", "https://evil.example", "cross-site"))
        self.assertFalse(allowed("box.tailnet.ts.net", "http://127.0.0.1:9119", "same-site"))

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

    def test_handler_send_catches_connection_error_and_client_aborts(self):
        """Handler._send safely handles ConnectionError, ConnectionAbortedError,
        ConnectionResetError, and BrokenPipeError without unhandled exceptions,
        marking close_connection = True."""
        cgs = self._load_serve()

        for exc in (
            BrokenPipeError(32, "Broken pipe"),
            ConnectionAbortedError(10053, "An established connection was aborted by the software in your host machine"),
            ConnectionResetError(10054, "An existing connection was forcibly closed by the remote host"),
            ConnectionError("connection lost"),
        ):
            h = cgs.Handler.__new__(cgs.Handler)
            h.close_connection = False
            h.send_response = MagicMock()
            h.send_header = MagicMock()
            h.end_headers = MagicMock()
            h.wfile = MagicMock()
            h.wfile.write.side_effect = exc

            h._send(200, "hello", "text/plain")
            self.assertTrue(h.close_connection, "close_connection should be True on %r" % exc)

        # Simulate error during header flushing (end_headers)
        h = cgs.Handler.__new__(cgs.Handler)
        h.close_connection = False
        h.send_response = MagicMock()
        h.send_header = MagicMock()
        h.end_headers = MagicMock(side_effect=ConnectionAbortedError(10053, "Aborted in header flush"))
        h.wfile = MagicMock()

        h._send(200, "hello", "text/plain")
        self.assertTrue(h.close_connection)
    def test_card_view_contract_metadata_and_specification(self):
        card_js_path = os.path.join(CREW_ROOT, "scripts", "crew_dashboard", "card.js")
        with open(card_js_path, "r", encoding="utf-8") as f:
            card_js = f.read()
        self.assertIn("ev.goal", card_js)
        self.assertIn("ev.artifact", card_js)
        self.assertIn("ev.lands_at", card_js)
        self.assertIn("ev.inputs", card_js)
        self.assertIn("ev.proof_cmd", card_js)
        self.assertIn("Contract Specification &amp; Details", card_js)
        self.assertIn("ev.body", card_js)

        cg_path = os.path.join(CREW_ROOT, "scripts", "crew_graph.py")
        with open(cg_path, "r", encoding="utf-8") as f:
            cg_src = f.read()
        self.assertIn('"goal": body_field(body, "Goal")', cg_src)
        self.assertIn('"artifact": body_field(body, "Artifact")', cg_src)
        self.assertIn('"lands_at": body_field(body, "Lands at")', cg_src)
        self.assertIn('"inputs": body_field(body, "Inputs")', cg_src)
        self.assertIn('"proof_cmd": body_field(body, "proof command")', cg_src)
        self.assertIn('"body": body or ""', cg_src)


class SessionTraceabilityJsTests(unittest.TestCase):
    """kanban-session-traceability, run in node: the card page's discussion chip (card.js) and the Desktop tile's
    bridge (desktop/plugin.js). The functions are sliced out of the shipped files, so the code under test is the
    code that ships; the DOM, clipboard and window are minimal stand-ins."""

    def setUp(self):
        import shutil
        node = shutil.which("node")
        if not node:
            self.skipTest("node not installed")
        self.node = str(node)

    def _read(self, *parts):
        with open(os.path.join(CREW_ROOT, *parts), "r", encoding="utf-8") as f:
            return f.read()

    @staticmethod
    def _fn(src, name):
        start = src.index("function %s(" % name)
        return src[start:src.index("\n}", start) + 2]

    def _run(self, script):
        import subprocess
        out = subprocess.run([self.node, "-e", script], capture_output=True, text=True, timeout=30)
        self.assertEqual(out.returncode, 0, out.stderr)
        return json.loads(out.stdout.strip().splitlines()[-1])

    # A DOM just big enough for the chip: elements with children, attributes, listeners and classList.
    DOM = r"""
function El(tag){ this.tagName = tag; this.children = []; this.attrs = {}; this.listeners = {}; this.textContent = "";
  var self = this; this.classList = {set: {}, add: function(c){ self.classList.set[c] = 1; },
  remove: function(c){ delete self.classList.set[c]; }}; }
El.prototype.appendChild = function(c){ this.children.push(c); return c; };
El.prototype.setAttribute = function(k, v){ this.attrs[k] = String(v); };
El.prototype.addEventListener = function(k, f){ this.listeners[k] = f; };
El.prototype.click = function(){ this.listeners.click({stopPropagation: function(){}}); };
var byId = {};
var document = {body: new El("body"), createElement: function(t){ return new El(t); },
  getElementById: function(id){ return byId[id] || null; }};
var origAppend = El.prototype.appendChild;
El.prototype.appendChild = function(c){ if(c.id) byId[c.id] = c; return origAppend.call(this, c); };
function setTimeout(){ return 0; } function clearTimeout(){}
var COPYFLASH = {};
function shortId(s){ s=String(s); return s.length<=14 ? s : s.slice(0,7)+".."+s.slice(-5); }
"""

    def _card_fns(self):
        src = self._read("scripts", "crew_dashboard", "card.js")
        self.assertIn("hermes:open-session", src)
        rx = src[src.index("var SESSION_ID_RX"):src.index("\n", src.index("var SESSION_ID_RX"))]
        return rx + "\n" + "\n".join(self._fn(src, n) for n in (
            "parseSessionCoord", "discussionCoord", "sessionRef", "openSessionTarget", "chatUrlFor",
            "openDiscussion", "sitDiscussionChip", "showToast"))

    def test_parse_session_coord_accepts_a_session_and_refuses_the_rest(self):
        script = self._card_fns() + r"""
console.log(JSON.stringify([
  parseSessionCoord("default/20261012_092737_07d8d5"), parseSessionCoord(" owner-chat/s-1 "),
  parseSessionCoord("default/no-session"), parseSessionCoord("default"), parseSessionCoord("a/b/c"),
  parseSessionCoord("x/../etc"), parseSessionCoord("x/a;b"), parseSessionCoord(""), parseSessionCoord(null),
  parseSessionCoord(42), discussionCoord({coordinator: "", session_id: "row_session"}),
  discussionCoord({coordinator: "leader/no-session", session_id: "row_session"}),
  discussionCoord({}), discussionCoord(null)]));
"""
        out = self._run(script)
        self.assertEqual({"profile": "default", "sessionId": "20261012_092737_07d8d5"}, out[0])
        self.assertEqual({"profile": "owner-chat", "sessionId": "s-1"}, out[1])
        self.assertEqual([None] * 8, out[2:10])
        self.assertEqual({"profile": "", "sessionId": "row_session"}, out[10])         # the row's session_id
        self.assertEqual({"profile": "leader", "sessionId": "row_session"}, out[11])
        self.assertEqual([None, None], out[12:])                                        # legacy card: no chip

    def test_the_chip_posts_open_session_to_the_desktop_parent(self):
        script = self.DOM + self._card_fns() + r"""
var posted = [];
var parentWin = {postMessage: function(msg, target){ posted.push([msg, target]); }};
var window = {parent: parentWin};
var box = new El("div");
sitDiscussionChip(box, parseSessionCoord("default/20261012_092737_07d8d5"));
var chip = box.children[0], btn = chip.children[2];
btn.click();
console.log(JSON.stringify({n: box.children.length, label: chip.children[1].textContent, id: btn.id,
  posted: posted, after: btn.textContent, data: btn.attrs["data-session"]}));
"""
        out = self._run(script)
        self.assertEqual(1, out["n"])
        self.assertEqual("cardSessionJump", out["id"])
        self.assertEqual("default/2026101..7d8d5", out["label"])
        self.assertEqual([[{"type": "hermes:open-session", "sessionId": "20261012_092737_07d8d5",
                            "profile": "default"}, "*"]], out["posted"])
        self.assertEqual("opening", out["after"])                                       # visual click feedback
        self.assertEqual("20261012_092737_07d8d5", out["data"])

    def test_a_standalone_browser_copies_the_session_and_shows_a_toast(self):
        script = self.DOM + self._card_fns() + r"""
var copied = [];
function copyText(text, done){ copied.push(text); done(true); }
var window = {}; window.parent = window;
var box = new El("div");
sitDiscussionChip(box, parseSessionCoord("default/20261012_092737_07d8d5"));
box.children[0].children[2].click();
var toast = byId.crewToast;
console.log(JSON.stringify({copied: copied, toast: toast && toast.textContent, on: !!(toast && toast.classList.set.on),
  role: toast && toast.attrs.role}));
"""
        out = self._run(script)
        self.assertEqual(["@session:default/20261012_092737_07d8d5"], out["copied"])
        self.assertEqual("Session link copied: @session:default/20261012_092737_07d8d5", out["toast"])
        self.assertTrue(out["on"])
        self.assertEqual("status", out["role"])

    def test_the_web_dashboard_frame_posts_open_session_to_its_own_origin(self):
        script = self.DOM + self._card_fns() + r"""
var copied = [], posted = [];
function copyText(text, done){ copied.push(text); done(true); }
var window = {parent: {location: {origin: "http://127.0.0.1:9119"},
  postMessage: function(m, t){ posted.push([m, t]); }}, __crewNav: function(){}};
var box = new El("div");
sitDiscussionChip(box, parseSessionCoord("default/s1"));
var btn = box.children[0].children[2];
btn.click();
console.log(JSON.stringify({copied: copied, posted: posted, after: btn.textContent}));
"""
        out = self._run(script)
        self.assertEqual([[{"type": "hermes:open-session", "sessionId": "s1", "profile": "default"},
                           "http://127.0.0.1:9119"]], out["posted"])         # never "*" from the dashboard frame
        self.assertEqual([], out["copied"])
        self.assertEqual("opening", out["after"])

    def test_a_frame_whose_parent_refuses_the_post_falls_back_to_copy(self):
        script = self.DOM + self._card_fns() + r"""
var copied = [];
function copyText(text, done){ copied.push(text); done(true); }
var window = {parent: {postMessage: function(){ throw new Error("cross-origin"); }}};
var box = new El("div");
sitDiscussionChip(box, parseSessionCoord("default/s1"));
box.children[0].children[2].click();
console.log(JSON.stringify({copied: copied}));
"""
        self.assertEqual(["@session:default/s1"], self._run(script)["copied"])

    def test_discovered_session_profile_names_the_chip(self):
        script = self._card_fns() + r"""
console.log(JSON.stringify([
  discussionCoord({coordinator: "", session_id: "20261012_131459_eb9bfb", session_profile: "default"}),
  discussionCoord({coordinator: "leader/no-session", session_id: "s9", session_profile: "coder"}),
  discussionCoord({coordinator: "", session_id: "s9", session_profile: "../x"}),
  discussionCoord({coordinator: "default/c1", session_id: "s9", session_profile: "coder"})]));
"""
        out = self._run(script)
        self.assertEqual({"profile": "default", "sessionId": "20261012_131459_eb9bfb"}, out[0])
        self.assertEqual({"profile": "coder", "sessionId": "s9"}, out[1])               # discovery wins over the line
        self.assertEqual({"profile": "", "sessionId": "s9"}, out[2])                    # a bad profile is dropped
        self.assertEqual({"profile": "default", "sessionId": "c1"}, out[3])             # Coordinator: still first

    def test_a_dashboard_frame_on_another_loopback_origin_posts_to_the_referrer_origin(self):
        # parent.location.origin throws cross-origin (dashboard on localhost:9119, page on 127.0.0.1:8799):
        # the old code fell through to the clipboard; now the embedding origin comes from document.referrer.
        script = self.DOM + self._card_fns() + r"""
var copied = [], posted = [];
function copyText(text, done){ copied.push(text); done(true); }
document.referrer = "http://localhost:9119/crew?x=1";
var parentWin = {postMessage: function(m, t){ posted.push([m, t]); }};
Object.defineProperty(parentWin, "location", {get: function(){ throw new Error("SecurityError"); }});
var window = {parent: parentWin, __crewNav: function(){}};
var box = new El("div");
sitDiscussionChip(box, parseSessionCoord("default/s1"));
var btn = box.children[0].children[2];
btn.click();
console.log(JSON.stringify({copied: copied, posted: posted, after: btn.textContent}));
"""
        out = self._run(script)
        self.assertEqual([[{"type": "hermes:open-session", "sessionId": "s1", "profile": "default"},
                           "http://localhost:9119"]], out["posted"])
        self.assertEqual([], out["copied"])
        self.assertEqual("opening", out["after"])

    def test_open_session_target_never_throws_and_scopes_the_bridge_frame(self):
        script = self._card_fns() + r"""
var document = {referrer: ""};
var out = [];
var window = {parent: {}};                                         out.push(openSessionTarget());   // desktop tile
window = {parent: {location: {origin: "http://127.0.0.1:9119"}}, __crewNav: 1}; out.push(openSessionTarget());
window = {parent: {location: {origin: "null"}}, __crewNav: 1};    document.referrer = "https://dash.example:8443/a";
out.push(openSessionTarget());
window = {parent: {get location(){ throw new Error("x"); }}, __crewNav: 1}; document.referrer = "javascript:alert(1)";
out.push(openSessionTarget());
console.log(JSON.stringify(out));
"""
        self.assertEqual(["*", "http://127.0.0.1:9119", "https://dash.example:8443", "*"], self._run(script))

    def test_a_standalone_browser_opens_the_dashboard_chat_when_it_knows_the_dashboard(self):
        script = self.DOM + self._card_fns() + r"""
var copied = [], opened = [];
function copyText(text, done){ copied.push(text); done(true); }
var state = {hermes_chat_url: "http://127.0.0.1:9119/"};
var window = {open: function(u, n, f){ opened.push([u, n, f]); return null; }}; window.parent = window;
var box = new El("div");
sitDiscussionChip(box, parseSessionCoord("default/20261012_131459_eb9bfb"));
var btn = box.children[0].children[2];
btn.click();
console.log(JSON.stringify({copied: copied, opened: opened, after: btn.textContent}));
"""
        out = self._run(script)
        self.assertEqual([["http://127.0.0.1:9119/chat?resume=20261012_131459_eb9bfb&profile=default",
                           "_blank", "noopener"]], out["opened"])
        self.assertEqual([], out["copied"])
        self.assertEqual("opening", out["after"])

    def test_a_standalone_browser_with_an_unsafe_or_blocked_dashboard_url_copies_instead(self):
        script = self.DOM + self._card_fns() + r"""
var copied = [], opened = [];
function copyText(text, done){ copied.push(text); done(true); }
var state = {hermes_chat_url: "javascript:alert(1)"};
var window = {open: function(u){ opened.push(u); }}; window.parent = window;
var box = new El("div");
sitDiscussionChip(box, parseSessionCoord("default/s1"));
box.children[0].children[2].click();
state = {hermes_chat_url: "http://127.0.0.1:9119"};
window.open = function(){ throw new Error("popup blocked"); };
box.children[0].children[2].click();
console.log(JSON.stringify({copied: copied, opened: opened,
  urls: [chatUrlFor({sessionId: "s1", profile: ""}, "https://d.example/base/"), chatUrlFor({sessionId: "s1"}, "")]}));
"""
        out = self._run(script)
        self.assertEqual([], out["opened"])
        self.assertEqual(["@session:default/s1", "@session:default/s1"], out["copied"])
        self.assertEqual(["https://d.example/base/chat?resume=s1", ""], out["urls"])

    # dashboard/dist/index.js is one IIFE: its helpers are indented two spaces, so they end at "\n  }".
    def _dashboard_fns(self):
        src = self._read("dashboard", "dist", "index.js")
        out = []
        for rx in ("var SESSION_IDENT_RE", "var LOOPBACK_ORIGIN_RE"):
            rx_at = src.index(rx)
            out.append(src[rx_at:src.index("\n", rx_at)])
        for name in ("parseOpenSession", "isSessionOriginAllowed", "chatResumePath", "openChatSession"):
            start = src.index("function %s(" % name)
            out.append(src[start:src.index("\n  }", start) + 4])
        return "\n".join(out)

    def test_web_dashboard_accepts_open_session_from_loopback_origins_only(self):
        script = self._dashboard_fns() + r"""
var cases = [
  ["http://127.0.0.1:9119", "http://127.0.0.1:9119"], ["http://127.0.0.1:8799", "http://127.0.0.1:9119"],
  ["http://localhost:8799", "http://127.0.0.1:9119"], ["http://[::1]:9119", "http://localhost:9119"],
  ["https://agent4070-dashboard.ptdev.vip", "https://agent4070-dashboard.ptdev.vip"],
  ["http://evil.example", "http://127.0.0.1:9119"], ["http://127.0.0.1.evil.example", "http://127.0.0.1:9119"],
  ["http://127.0.0.1:8799", "https://agent4070-dashboard.ptdev.vip"], ["null", "http://127.0.0.1:9119"],
  ["", "http://127.0.0.1:9119"], [null, "http://127.0.0.1:9119"]];
console.log(JSON.stringify(cases.map(function(c){ return isSessionOriginAllowed(c[0], c[1]); })));
"""
        self.assertEqual([True, True, True, True, True, False, False, False, False, False, False], self._run(script))

    def test_web_dashboard_listens_for_open_session_from_its_own_frame_only(self):
        src = self._read("dashboard", "dist", "index.js")
        handler = src[src.index("function onMessage(e)"):src.index("window.addEventListener(\"message\", onMessage)")]
        self.assertIn("e.source !== frame.contentWindow", handler)
        self.assertIn("d.type === \"hermes:open-session\"", handler)
        # open-session: the origin is checked (own or loopback) before the payload is acted on
        self.assertIn("isSessionOriginAllowed(e.origin, window.location.origin)", handler)
        self.assertLess(handler.index("isSessionOriginAllowed"), handler.index("openChatSession(target, window)"))
        self.assertIn("openChatSession(target, window)", handler)
        # crew:navigate stays same-origin only, checked before the page is changed
        self.assertIn("e.origin !== window.location.origin", handler)
        self.assertLess(handler.index("e.origin !== window.location.origin"), handler.index("setPage(d.path)"))
        self.assertIn("crew:navigate", handler)                                     # board/card links still work

    def test_web_dashboard_navigates_to_chat_resume_with_profile(self):
        script = self._dashboard_fns() + r"""
function makeWin(base){
  var events = [], pushed = [], assigned = [];
  var win = {__HERMES_BASE_PATH__: base, events: events, pushed: pushed, assigned: assigned,
    history: {state: {usr: null, key: "k0", idx: 3},
      pushState: function(s, t, u){ this.state = s; pushed.push(u); }},
    PopStateEvent: function(type, init){ this.type = type; this.state = init.state; },
    dispatchEvent: function(ev){ events.push([ev.type, ev.state.idx]); },
    location: {assign: function(u){ assigned.push(u); }}};
  return win;
}
var w1 = makeWin(""), w2 = makeWin("hermes/"), w3 = makeWin("");
openChatSession(parseOpenSession({type: "hermes:open-session", sessionId: "20261012_092737_07d8d5",
  profile: "default"}), w1);
openChatSession(parseOpenSession({type: "hermes:open-session", sessionId: "s1"}), w2);
w3.history = null;                                         // no history API: a plain page load
openChatSession(parseOpenSession({type: "hermes:open-session", sessionId: "s2", profile: "leader"}), w3);
console.log(JSON.stringify({w1: [w1.pushed, w1.events, w1.assigned], w2: w2.pushed, w3: [w3.pushed, w3.assigned]}));
"""
        out = self._run(script)
        self.assertEqual([["/chat?resume=20261012_092737_07d8d5&profile=default"], [["popstate", 4]], []], out["w1"])
        self.assertEqual(["/hermes/chat?resume=s1"], out["w2"])                    # reverse-proxied base path
        self.assertEqual([[], ["/chat?resume=s2&profile=leader"]], out["w3"])

    def test_web_dashboard_drops_malformed_open_session_payloads(self):
        script = self._dashboard_fns() + r"""
var bad = [null, "x", {type: "crew:navigate", sessionId: "s1"}, {type: "hermes:open-session"},
  {type: "hermes:open-session", sessionId: "../../etc/passwd"}, {type: "hermes:open-session", sessionId: "a&b=c"},
  {type: "hermes:open-session", sessionId: "no-session"}, {type: "hermes:open-session", sessionId: "s1", profile: "a/b"},
  {type: "hermes:open-session", sessionId: "s1", profile: "x?y"}, {type: "hermes:open-session", sessionId: "javascript:1"},
  {type: "hermes:open-session", sessionId: new Array(200).join("a")}];
var parsed = bad.map(parseOpenSession);
var calls = 0, win = {location: {assign: function(){ calls++; }}};
parsed.forEach(function(t){ openChatSession(t, win); });
console.log(JSON.stringify({parsed: parsed, calls: calls}));
"""
        out = self._run(script)
        self.assertEqual([None] * 11, out["parsed"])
        self.assertEqual(0, out["calls"])

    def test_a_card_without_a_session_renders_no_chip_and_throws_nothing(self):
        script = self.DOM + self._card_fns() + r"""
var box = new El("div");
sitDiscussionChip(box, discussionCoord({coordinator: "default/no-session"}));
sitDiscussionChip(box, discussionCoord({}));
console.log(JSON.stringify(box.children.length));
"""
        self.assertEqual(0, self._run(script))

    def test_render_sit_fields_adds_the_chip_after_the_coordinator(self):
        src = self._read("scripts", "crew_dashboard", "card.js")
        fields = self._fn(src, "renderSitFields")
        self.assertIn("sitDiscussionChip(box, discussionCoord(state))", fields)
        self.assertLess(fields.index("cardCoCopy"), fields.index("sitDiscussionChip"))

    def _plugin_fns(self):
        src = self._read("desktop", "plugin.js")
        rx = src[src.index("var SESSION_IDENT_RE"):src.index("\n", src.index("var SESSION_IDENT_RE"))]
        return rx + "\n" + self._fn(src, "parseOpenSession") + "\n" + self._fn(src, "openCardSession")

    def test_desktop_bridge_imports_host_and_handles_open_session(self):
        src = self._read("desktop", "plugin.js")
        imports = src[src.index("import {"):src.index("from '@hermes/plugin-sdk'")]
        self.assertIn("host", imports)
        self.assertIn("e.data.type === 'hermes:open-session'", src)
        self.assertIn("e.source !== frame.contentWindow", src)                      # only our own iframe
        self.assertIn("openCardSession(target, host)", src)
        self.assertIn("hermes:board-info", src)                                     # the board title still works

    def test_desktop_bridge_calls_host_open_session_for_a_valid_payload(self):
        script = self._plugin_fns() + r"""
var calls = [];
var host = {openSession: function(sid, opts){ calls.push([sid, opts]); return Promise.resolve(); }};
(async function(){
  var ok = await openCardSession(parseOpenSession({type: "hermes:open-session",
    sessionId: "20261012_092737_07d8d5", profile: "default"}), host);
  var noProfile = await openCardSession(parseOpenSession({type: "hermes:open-session", sessionId: "s1"}), host);
  console.log(JSON.stringify({ok: ok, noProfile: noProfile, calls: calls}));
})();
"""
        out = self._run(script)
        self.assertTrue(out["ok"])
        self.assertTrue(out["noProfile"])
        self.assertEqual([["20261012_092737_07d8d5", {"profile": "default"}], ["s1", {}]], out["calls"])

    def test_desktop_bridge_rejects_malformed_payloads_and_never_calls_the_host(self):
        script = self._plugin_fns() + r"""
var calls = [];
var host = {openSession: function(sid, opts){ calls.push([sid, opts]); return Promise.resolve(); }};
var bad = [null, "x", {type: "hermes:theme", sessionId: "s1"}, {type: "hermes:open-session"},
  {type: "hermes:open-session", sessionId: "../../etc/passwd"}, {type: "hermes:open-session", sessionId: "a;rm -rf"},
  {type: "hermes:open-session", sessionId: "no-session"}, {type: "hermes:open-session", sessionId: "s1", profile: "a/b"},
  {type: "hermes:open-session", sessionId: "s1", profile: "<x>"}, {type: "hermes:open-session", sessionId: "$(id)"},
  {type: "hermes:open-session", sessionId: new Array(200).join("a")}];
(async function(){
  var parsed = bad.map(parseOpenSession);
  for (var i = 0; i < parsed.length; i++) await openCardSession(parsed[i], host);
  console.log(JSON.stringify({parsed: parsed, calls: calls}));
})();
"""
        out = self._run(script)
        self.assertEqual([None] * 11, out["parsed"])
        self.assertEqual([], out["calls"])

    def test_desktop_bridge_survives_a_host_without_open_session_or_a_failing_one(self):
        script = self._plugin_fns() + r"""
var t = parseOpenSession({type: "hermes:open-session", sessionId: "s1", profile: "default"});
var warned = 0; console.warn = function(){ warned++; };
(async function(){
  var r = [await openCardSession(t, null), await openCardSession(t, {}),
           await openCardSession(t, {openSession: function(){ return Promise.reject(new Error("no")); }}),
           await openCardSession(t, {openSession: function(){ throw new Error("sync"); }})];
  console.log(JSON.stringify({r: r, warned: warned}));
})();
"""
        out = self._run(script)
        self.assertEqual([False, False, False, False], out["r"])
        self.assertEqual(2, out["warned"])


class BridgeCardNavigationTests(unittest.TestCase):
    """Web Dashboard bridge (plugin_api._BRIDGE_JS), run in node: board.js appends the page's own query
    (?theme=..&bg=..&fg=..) to every card link, so a card click inside the tab must still post crew:navigate with
    a path the tab accepts (dist/index.js PAGE_RE). The bridge under test is the string the proxy injects."""

    BASE = "http://127.0.0.1:9119/api/plugins/crew/"

    def setUp(self):
        import shutil
        node = shutil.which("node")
        if not node:
            self.skipTest("node not installed")
        self.node = str(node)

    def _page_re(self):
        with open(os.path.join(CREW_ROOT, "dashboard", "dist", "index.js"), "r", encoding="utf-8") as f:
            src = f.read()
        at = src.index("var PAGE_RE")
        return src[at:src.index("\n", at)]

    def _clicks(self, hrefs, crew_nav=()):
        """Load the bridge into a stub srcdoc frame, click an <a href> per entry, call __crewNav per crew_nav.
        Returns {clicks: [[posted path or null, defaultPrevented]], navs: [...], posted_to: [...], page_re: [...]}."""
        import subprocess
        script = r"""
var posted = [], listeners = {};
var parentWin = {location: {origin: "http://127.0.0.1:9119"}, __HERMES_BASE_PATH__: "",
  __HERMES_PLUGIN_SDK__: {authedFetch: function(){ return Promise.reject(new Error("no fetch in test")); }},
  postMessage: function(m, o){ posted.push([m, o]); }};
var window = {parent: parentWin};
var document = {baseURI: %s, documentElement: {},
  addEventListener: function(t, fn){ (listeners[t] = listeners[t] || []).push(fn); }};
function MutationObserver(){ this.observe = function(){}; }
function FileReader(){}
%s
%s
var clicks = %s.map(function(href){
  var before = posted.length;
  var a = {target: "", hasAttribute: function(){ return false; }, getAttribute: function(){ return href; }};
  var e = {defaultPrevented: false, button: 0, target: {closest: function(){ return a; }},
           preventDefault: function(){ this.defaultPrevented = true; }};
  listeners.click.forEach(function(fn){ fn(e); });
  var msg = posted.length > before ? posted[posted.length - 1][0] : null;
  return [msg && msg.type === "crew:navigate" ? msg.path : null, e.defaultPrevented];
});
var navs = %s.map(function(u){
  var before = posted.length; window.__crewNav(u);
  return posted.length > before ? posted[posted.length - 1][0].path : null;
});
console.log(JSON.stringify({clicks: clicks, navs: navs,
  posted_to: posted.map(function(p){ return p[1]; }),
  page_re: posted.map(function(p){ return PAGE_RE.test(p[0].path); })}));
""" % (json.dumps(self.BASE), self._page_re(), plugin_api._BRIDGE_JS, json.dumps(list(hrefs)),
       json.dumps(list(crew_nav)))
        out = subprocess.run([self.node, "-e", script], capture_output=True, text=True, timeout=30)
        self.assertEqual(out.returncode, 0, out.stderr)
        return json.loads(out.stdout.strip().splitlines()[-1])

    def test_card_links_with_theme_query_navigate_to_the_card(self):
        out = self._clicks([
            "card/t_74c73ccb?theme=dark&bg=%23041c1c&fg=%23ffffff",   # board.js card tile inside the tab
            "card/t_abc?theme=light",
            "card/t_abc?bg=%23ffffff&fg=%2317171a",
            "/api/plugins/crew/card/t_abc?fg=%23fff&theme=dark",       # absolute under the plugin prefix
            "card/t_abc",                                              # no query at all: unchanged behaviour
        ])
        self.assertEqual([["card/t_74c73ccb", True], ["card/t_abc", True], ["card/t_abc", True],
                          ["card/t_abc", True], ["card/t_abc", True]], out["clicks"])
        self.assertTrue(all(out["page_re"]))                           # every posted path is one the tab loads
        self.assertEqual({"http://127.0.0.1:9119"}, set(out["posted_to"]))  # never "*"

    def test_board_links_keep_all_and_drop_theme(self):
        out = self._clicks(["board?theme=dark&bg=%23041c1c&fg=%23ffffff", "board?all=1&theme=dark&bg=%23041c1c",
                            "board?theme=light&all=1", "board?all=1", "board", "./"])
        self.assertEqual([["board", True], ["board?all=1", True], ["board?all=1", True], ["board?all=1", True],
                          ["board", True], ["board", True]], out["clicks"])
        self.assertTrue(all(out["page_re"]))

    def test_links_outside_the_navigation_allowlist_are_left_alone(self):
        out = self._clicks([
            "card/t_abc?theme=dark&evil=1",           # an unknown parameter beside the theme ones
            "board?all=0&theme=dark",
            "board?older=1",
            "card/t_abc.json?theme=dark",             # data, not a page
            "card/../ack/x?theme=dark",               # normalises out of card/
            "card/t_abc/extra?theme=dark",
            "http://evil.example/card/t_abc?theme=dark",
            "/api/kanban/card/t_abc?theme=dark",      # another Hermes API
            "#top",
            "",
        ])
        self.assertEqual([[None, False]] * 10, out["clicks"])
        self.assertEqual([], out["posted_to"])

    def test_crew_nav_strips_theme_params_too(self):
        out = self._clicks([], crew_nav=["board", "board?theme=dark&bg=%23041c1c", "card/t_abc?theme=light",
                                         "board?all=1&fg=%23ffffff", "card/t_abc?x=1", "avatars/role/x.svg"])
        self.assertEqual(["board", "board", "card/t_abc", "board?all=1", None, None], out["navs"])
        self.assertTrue(all(out["page_re"]))

    def test_proxied_board_page_carries_the_fixed_bridge(self):
        req = MagicMock()
        req.query_params = {"theme": "dark"}
        req.headers = {"host": "127.0.0.1:9119"}
        req.url.scheme = "http"
        page = plugin_api._rewrite_html("<html><head><title>b</title></head><body></body></html>", req,
                                        UPSTREAM_CSP)
        bridge = page[page.index('<script id="crew-parent-bridge"'):]
        self.assertIn("THEME_KEYS = { theme: 1, bg: 1, fg: 1 }", bridge)
        self.assertIn("window.__crewNav = function (u) { var t = navTarget(u); if (t) nav(t); };", bridge)
        self.assertNotIn('r.search !== "?all=1"', bridge)              # the old exact-match gate is gone


class OriginSessionDiscoveryTests(unittest.TestCase):
    """crew_graph.find_origin_session: a card with no tasks.session_id and no Coordinator: line (a `hermes kanban
    create` from a terminal, an OpenSpec pipeline card such as t_ea95ab52) still names the discussion it came from,
    read from the profiles' state.db; the card's own worker sessions are never taken for its origin."""

    CREATED = 1791811364

    def setUp(self):
        import sqlite3
        import crew_graph
        self.cg = crew_graph
        self.cg._ORIGIN_CACHE.clear()
        self.tmp = tempfile.TemporaryDirectory(prefix="crew-origin-")
        base = self.tmp.name
        self.board = os.path.join(base, "kanban.db")

        def state(path, sessions, messages):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            db = sqlite3.connect(path)
            db.execute("create table sessions (id text primary key, parent_session_id text, source text, model text, "
                       "title text, started_at real, ended_at real, message_count integer, tool_call_count integer, "
                       "input_tokens integer, output_tokens integer, profile_name text)")
            db.execute("create table messages (id integer primary key autoincrement, session_id text, role text, "
                       "content text, tool_calls text, timestamp real)")
            for sid, src in sessions:
                db.execute("insert into sessions (id, source, started_at) values (?,?,?)", (sid, src, self.CREATED - 900))
            db.executemany("insert into messages (session_id, role, content, tool_calls, timestamp) values (?,?,?,?,?)",
                           messages)
            db.commit()
            db.close()

        c = self.CREATED
        # default: the desktop discussion that ran `hermes kanban create` and saw "Created t_ea95ab52" first
        state(os.path.join(base, "state.db"), [("20261012_131459_eb9bfb", "desktop"), ("old_chat", "desktop")], [
            ("old_chat", "user", "talk about t_ea95ab52 last week", None, c - 86400),          # outside the window
            ("20261012_131459_eb9bfb", "assistant", "", '[{"function":{"name":"terminal","arguments":'
             '"{\\"command\\":\\"hermes kanban create ...\\"}"}}]', c - 2),
            ("20261012_131459_eb9bfb", "tool", '{"output": "Created t_ea95ab52  (ready, assignee=coder)"}', None, c + 1),
        ])
        # coder: the card's own worker session mentions it too (earlier than nothing, but it is the worker)
        state(os.path.join(base, "profiles", "coder", "state.db"), [("worker_sess", "kanban")], [
            ("worker_sess", "user", "work kanban task t_ea95ab52", None, c - 1),
        ])
        # leader: a later reviewer-style mention that must lose to the earliest
        state(os.path.join(base, "profiles", "leader", "state.db"), [("later_sess", "oneshot")], [
            ("later_sess", "tool", "read t_ea95ab52 card", None, c + 600),
        ])
        db = sqlite3.connect(self.board)
        db.execute("create table task_events (id integer primary key autoincrement, task_id text, run_id integer, "
                   "kind text, payload text, created_at integer)")
        db.execute("insert into task_events (task_id, run_id, kind, payload, created_at) values (?,?,?,?,?)",
                   ("t_ea95ab52", 1, "session", json.dumps({"session": "worker_sess"}), c + 30))
        db.execute("insert into task_events (task_id, run_id, kind, payload, created_at) values (?,?,?,?,?)",
                   ("t_crew", None, "origin", json.dumps({"session": "20261012_092737_07d8d5", "by": "default"}), c))
        db.execute("insert into task_events (task_id, run_id, kind, payload, created_at) values (?,?,?,?,?)",
                   ("t_nosess", None, "origin", json.dumps({"session": "no-session", "by": "default"}), c))
        db.commit()
        db.close()
        self.env = patch.dict(os.environ, {"HERMES_HOME": base})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.cg._ORIGIN_CACHE.clear()
        self.tmp.cleanup()

    def test_a_cli_created_card_resolves_its_discussion_from_state_db(self):
        prof, sid = self.cg.find_origin_session(self.board, "t_ea95ab52", None, self.CREATED)
        self.assertEqual(("default", "20261012_131459_eb9bfb"), (prof, sid))

    def test_the_cards_own_worker_session_is_never_its_origin(self):
        import sqlite3
        db = sqlite3.connect(os.path.join(self.tmp.name, "state.db"))
        db.execute("delete from messages where session_id = '20261012_131459_eb9bfb'")
        db.commit()
        db.close()
        prof, sid = self.cg.find_origin_session(self.board, "t_ea95ab52", None, self.CREATED)
        self.assertNotEqual("worker_sess", sid)
        self.assertEqual(("leader", "later_sess"), (prof, sid))          # next earliest non-worker mention

    def test_the_row_session_id_wins_and_crews_origin_record_is_next(self):
        self.assertEqual(("", "row_sid"), self.cg.find_origin_session(self.board, "t_ea95ab52", "row_sid", self.CREATED))
        self.assertEqual(("default", "20261012_092737_07d8d5"),
                         self.cg.find_origin_session(self.board, "t_crew", None, self.CREATED))

    def test_no_mention_no_session_and_unsafe_ids_give_no_chip(self):
        self.assertEqual(("", ""), self.cg.find_origin_session(self.board, "t_unknown", None, self.CREATED))
        self.assertEqual(("", ""), self.cg.find_origin_session(self.board, "t_nosess", None, None))
        self.assertEqual(("", ""), self.cg.find_origin_session(self.board, "", None, self.CREATED))
        # a row session_id that is not a plain id is not trusted; discovery runs instead
        self.assertEqual(("default", "20261012_131459_eb9bfb"),
                         self.cg.find_origin_session(self.board, "t_ea95ab52", "../etc", self.CREATED))

    def test_a_found_origin_is_cached_and_a_miss_is_retried_after_the_ttl(self):
        self.cg.find_origin_session(self.board, "t_ea95ab52", None, self.CREATED)
        with patch.object(self.cg, "discover_state_dbs", side_effect=AssertionError("re-scanned")):
            self.assertEqual("20261012_131459_eb9bfb",
                             self.cg.find_origin_session(self.board, "t_ea95ab52", None, self.CREATED)[1])
        self.assertEqual(("", ""), self.cg.find_origin_session(self.board, "t_late", None, self.CREATED))
        prof, sid, found, ts = self.cg._ORIGIN_CACHE["t_late"]
        self.cg._ORIGIN_CACHE["t_late"] = (prof, sid, found, ts - self.cg.ORIGIN_MISS_TTL_S - 1)
        with patch.object(self.cg, "_origin_from_messages", return_value=("coder", "late_sess")) as again:
            self.assertEqual(("coder", "late_sess"),
                             self.cg.find_origin_session(self.board, "t_late", None, self.CREATED))
            again.assert_called_once()

    def test_card_box_fields_carries_the_discovered_profile(self):
        f = self.cg.card_box_fields({"session_id": "20261012_131459_eb9bfb", "session_profile": "default"})
        self.assertEqual("20261012_131459_eb9bfb", f["session_id"])
        self.assertEqual("default", f["session_profile"])
        self.assertEqual("", self.cg.card_box_fields({})["session_profile"])

    def test_hermes_chat_url_is_an_http_base_or_the_loopback_default(self):
        with patch.dict(os.environ, {"CREW_HERMES_DASHBOARD_URL": "https://dash.example/"}):
            self.assertEqual("https://dash.example", self.cg.hermes_chat_url())
        with patch.dict(os.environ, {"CREW_HERMES_DASHBOARD_URL": "javascript:alert(1)"}):
            self.assertEqual("http://127.0.0.1:9119", self.cg.hermes_chat_url())
        with open(os.path.join(self.tmp.name, "config.yaml"), "w") as fh:
            fh.write("dashboard:\n  theme: default\n  public_url: https://agent4070-dashboard.ptdev.vip\n")
        with patch.dict(os.environ, {"CREW_HERMES_DASHBOARD_URL": ""}):
            self.assertEqual("https://agent4070-dashboard.ptdev.vip", self.cg.hermes_chat_url())


@unittest.skipUnless(_load_hermes_auth(), "hermes-agent is not installed")
class HermesTokenAuthTests(unittest.TestCase):
    """The plugin routes behind Hermes's real auth_middleware, as the dashboard mounts them."""

    def setUp(self):
        ws = _load_hermes_auth()
        self.token = ws._SESSION_TOKEN
        self.app = FastAPI()
        self.app.state.startup_ready = True
        self.app.middleware("http")(ws.auth_middleware)
        self.app.include_router(router, prefix="/api/plugins/crew")
        self.client = TestClient(self.app)

    @patch("urllib.request.urlopen")
    def test_no_session_token_is_401_and_never_reaches_upstream(self, mock_urlopen):
        _mock_upstream(mock_urlopen, "<html><head></head></html>", "text/html")
        for path in ("/api/plugins/crew/board", "/api/plugins/crew/card/t_1", "/api/plugins/crew/card/t_1.json",
                     "/api/plugins/crew/board.json", "/api/plugins/crew/avatars/role/worker.svg"):
            self.assertEqual(self.client.get(path).status_code, 401, path)
        self.assertEqual(self.client.post("/api/plugins/crew/ack/all").status_code, 401)
        self.assertEqual(self.client.get("/api/plugins/crew/board",
                                         headers={"X-Hermes-Session-Token": "wrong"}).status_code, 401)
        mock_urlopen.assert_not_called()

    @patch("urllib.request.urlopen")
    def test_session_header_as_sent_by_authed_fetch_is_served(self, mock_urlopen):
        _mock_upstream(mock_urlopen, "<html><head></head><body></body></html>", "text/html", csp=UPSTREAM_CSP)
        resp = self.client.get("/api/plugins/crew/board", headers={"X-Hermes-Session-Token": self.token})
        self.assertEqual(resp.status_code, 200)
        self.assertIn('id="crew-parent-bridge"', resp.text)
        self.assertNotIn(self.token, resp.text)
        sent = dict(mock_urlopen.call_args[0][0].header_items())
        self.assertNotIn(self.token, json.dumps(sent))


class LiveUpstreamTests(unittest.TestCase):
    """The proxy against a real crew_graph_serve on a loopback port."""

    @classmethod
    def setUpClass(cls):
        cls.home = tempfile.mkdtemp(prefix="crew-dash-upstream-")
        cls._env = {k: os.environ.get(k) for k in ("HERMES_HOME", "CREW_ACK_FILE", "HERMES_BIN", "KANBAN_DB")}
        os.environ["HERMES_HOME"] = cls.home
        os.environ["CREW_ACK_FILE"] = os.path.join(cls.home, "crew", "attention_acks.json")
        os.environ.setdefault("HERMES_BIN", "/bin/false")
        os.environ.pop("KANBAN_DB", None)
        import crew_graph_serve
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), crew_graph_serve.Handler)
        cls.thread = threading.Thread(target=cls.srv.serve_forever, daemon=True)
        cls.thread.start()
        cls.upstream = "http://127.0.0.1:%d" % cls.srv.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        for k, v in cls._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def setUp(self):
        p = patch.object(plugin_api, "UPSTREAM", self.upstream)
        p.start()
        self.addCleanup(p.stop)
        app = FastAPI()
        app.include_router(router, prefix="/api/plugins/crew")
        self.client = TestClient(app)

    def test_ack_from_the_dashboard_origin_passes_the_same_origin_check(self):
        # The browser's own Origin/Host are the dashboard's; upstream must still see a same-origin write.
        resp = self.client.post("/api/plugins/crew/ack/all?undo=1",
                                headers={"Origin": "http://127.0.0.1:9119", "Sec-Fetch-Site": "same-origin"})
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertIn("restored", resp.text)

    def test_card_json_reaches_upstream(self):
        resp = self.client.get("/api/plugins/crew/card/t_nosuchcard.json")
        # Upstream answers for the card (no such card -> its own JSON 404), not the proxy's 400.
        self.assertEqual(resp.status_code, 404)
        self.assertIn("error", resp.json())

    def test_healthz(self):
        resp = self.client.get("/api/plugins/crew/healthz")
        self.assertEqual(resp.status_code, 200)
        # The health line names the active board (here the default board, no board.json: its formatted slug).
        self.assertTrue(resp.text.startswith("ok "), resp.text)
        self.assertIn("cards=", resp.text)

    def test_upstream_client_abort_handled_gracefully(self):
        import socket
        import struct
        host, port = self.srv.server_address
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, port))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))
        req = "GET / HTTP/1.1" + chr(13) + chr(10) + "Host: 127.0.0.1" + chr(13) + chr(10) + chr(13) + chr(10)
        s.sendall(req.encode("ascii"))
        s.close()

        resp = self.client.get("/api/plugins/crew/healthz")
        self.assertEqual(resp.status_code, 200)



class DesktopDualModeTests(unittest.TestCase):
    """desktop-flow-graph-pane, run in node: the shipped desktop/plugin.js is loaded as a module with
    @hermes/plugin-sdk, react and react/jsx-runtime swapped for stand-ins, so register(ctx) and the pane helpers
    under test are the code that ships. Dual mode: the /crew tile keeps its route and asTile nav row while the Flow
    Graph pane (PANES_AREA, SandboxedFrame) registers beside it."""

    SDK_STUB = r"""
export const PANES_AREA = 'panes';
export const ROUTES_AREA = 'routes';
export const SIDEBAR_NAV_AREA = 'sidebar.nav';
export function SandboxedFrame(){ return null; }
export function Button(){ return null; }
export function Codicon(){ return null; }
export const host = globalThis.__host || {};
"""
    REACT_STUB = "export default {useRef(){}, useState(){}, useEffect(){}, Fragment: 'frag'};\n"
    JSX_STUB = ("export function jsx(type, props, key){ return {type: type, props: props, key: key}; }\n"
                "export const jsxs = jsx;\n")

    def setUp(self):
        import shutil
        node = shutil.which("node")
        if not node:
            self.skipTest("node not installed")
        self.node = str(node)
        self.tmp = tempfile.mkdtemp(prefix="crew-desktop-pane-")
        with open(os.path.join(CREW_ROOT, "desktop", "plugin.js"), "r", encoding="utf-8") as f:
            src = f.read()
        for spec, name, body in (("@hermes/plugin-sdk", "sdk.mjs", self.SDK_STUB),
                                 ("react/jsx-runtime", "jsx.mjs", self.JSX_STUB),
                                 ("react", "react.mjs", self.REACT_STUB)):
            with open(os.path.join(self.tmp, name), "w", encoding="utf-8") as f:
                f.write(body)
            src = src.replace("from '%s'" % spec, "from './%s'" % name)
        # The helpers under test, exported next to the plugin (export lines only: the code is untouched).
        src += ("\nexport { paneCards, pickFocusCard, cardSignature, resolvePaneFrameSrc, CrewFlowGraphPane, CrewPage,"
                " PANE_ID, PANE_TITLE, LOCAL_BOARD_URL }\n")
        with open(os.path.join(self.tmp, "plugin.mjs"), "w", encoding="utf-8") as f:
            f.write(src)

    def tearDown(self):
        import shutil
        shutil.rmtree(getattr(self, "tmp", ""), ignore_errors=True)

    def _run(self, body):
        import subprocess
        script = os.path.join(self.tmp, "run.mjs")
        with open(script, "w", encoding="utf-8") as f:
            f.write("import * as P from './plugin.mjs';\nconst plugin = P.default;\n" + body)
        out = subprocess.run([self.node, script], capture_output=True, text=True, timeout=30)
        self.assertEqual(out.returncode, 0, out.stderr)
        return json.loads(out.stdout.strip().splitlines()[-1])

    def _registered(self):
        return self._run(r"""
const regs = [];
const rest = function(){ return Promise.resolve({}); };
plugin.register({rest: rest, registerMany: function(cs){ cs.forEach(function(c){ regs.push(c); }); },
                 register: function(c){ regs.push(c); }});
console.log(JSON.stringify(regs.map(function(c){
  const el = c.render ? c.render() : null;
  return {id: c.id, area: c.area, title: c.title || null, data: c.data || null,
          renders: el ? (el.type === P.CrewFlowGraphPane ? 'pane' : el.type === P.CrewPage ? 'page' : 'other') : null,
          rest_passed: !!(el && el.props && el.props.rest === rest)};
})));
""")

    def test_dual_mode_registers_tile_and_pane_together(self):
        regs = {r["id"]: r for r in self._registered()}
        self.assertEqual({"page", "nav", "crew-flow-graph-pane", "crew-pane-companion"}, set(regs))
        # The tile, unchanged: /crew route rendering CrewPage + the asTile sidebar row.
        self.assertEqual("routes", regs["page"]["area"])
        self.assertEqual({"path": "/crew"}, regs["page"]["data"])
        self.assertEqual("page", regs["page"]["renders"])
        self.assertEqual("sidebar.nav", regs["nav"]["area"])
        self.assertEqual({"codicon": "organization", "label": "Crew", "path": "/crew", "asTile": True},
                         regs["nav"]["data"])
        # The pane, beside it.
        pane = regs["crew-flow-graph-pane"]
        self.assertEqual("panes", pane["area"])
        self.assertEqual("Crew Flow Graph", pane["title"])
        self.assertEqual("right", pane["data"]["placement"])
        self.assertEqual("380px", pane["data"]["width"])
        self.assertEqual("pane", pane["renders"])
        self.assertTrue(pane["rest_passed"])            # the board list goes through ctx.rest, not a raw fetch

    def test_pane_is_hide_only_so_closing_it_never_disables_the_tile(self):
        # Desktop disables a plugin when its ONLY pane is closed; registering a companion pane in panes
        # ensures closeTreePane calls dismissTreePane (collapsing the zone) instead of setPluginEnabled(false).
        panes = [r for r in self._registered() if r["area"] == "panes"]
        self.assertGreater(len(panes), 1)
        flow_pane = next(p for p in panes if p["id"] == "crew-flow-graph-pane")
        self.assertIsNone(flow_pane["data"].get("hideOnly"))
        companion = next(p for p in panes if p["id"] == "crew-pane-companion")
        self.assertEqual("floating", companion["data"].get("placement"))

    def test_pane_embeds_through_sandboxed_frame_only(self):
        with open(os.path.join(CREW_ROOT, "desktop", "plugin.js"), "r", encoding="utf-8") as f:
            src = f.read()
        imports = src[src.index("import {"):src.index("from '@hermes/plugin-sdk'")]
        self.assertIn("SandboxedFrame", imports)
        self.assertIn("PANES_AREA", imports)
        pane = src[src.index("function CrewFlowGraphPane("):src.index("var plugin = {")]
        self.assertIn("jsx(SandboxedFrame, {", pane)
        self.assertIn("title: PANE_TITLE", pane)
        self.assertNotIn("jsx('iframe'", pane)
        self.assertNotIn("webview", pane)
        self.assertNotIn("sandbox:", pane)             # the SDK's default posture, no extra tokens

    def test_pane_cards_order_and_focus(self):
        out = self._run(r"""
const board = {lanes: [
  {key: 'done', tiles: [{id: 't_done1', status: 'done'}]},
  {key: 'blocked', tiles: [{id: 't_blk', status: 'blocked'}, {id: 'bad id/..', status: 'blocked'}]},
  {key: 'archived', tiles: [{id: 't_arch', status: 'archived'}]},
  {key: 'running', tiles: [{id: 't_run', status: 'running', runs: 2, active: {run: 7}}]},
  {key: 'queued', tiles: [{id: 't_q', status: 'ready'}]}]};
const cards = P.paneCards(board);
console.log(JSON.stringify({
  ids: cards.map(function(c){ return c.id; }),
  first: P.pickFocusCard(cards, ''),
  keep: P.pickFocusCard(cards, 't_q'),
  gone: P.pickFocusCard(cards, 't_vanished'),
  none: P.pickFocusCard([], 't_q'),
  empty: P.paneCards(null).length + P.paneCards({lanes: 'x'}).length,
  sig: P.cardSignature(cards[0]), sig_idle: P.cardSignature({status: 'done', runs: 1, last_outcome: 'completed'}),
  sig_null: P.cardSignature(null)}));
""")
        self.assertEqual(["t_run", "t_blk", "t_q", "t_done1"], out["ids"])   # archived and unsafe ids left out
        self.assertEqual("t_run", out["first"])
        self.assertEqual("t_q", out["keep"])                                   # no focus jump while it is listed
        self.assertEqual("t_run", out["gone"])
        self.assertEqual("", out["none"])
        self.assertEqual(0, out["empty"])
        self.assertEqual("running|2||7", out["sig"])
        self.assertEqual("done|1|completed|", out["sig_idle"])
        self.assertEqual("", out["sig_null"])

    def test_frame_src_ladder_never_puts_the_gateway_token_in_a_url(self):
        out = self._run(r"""
function desk(conn, ticket, calls){
  return {getConnection: function(){ return Promise.resolve(conn); },
          api: function(req){ calls.push(req.path + ' ' + req.method);
                              return ticket ? Promise.resolve({ticket: ticket}) : Promise.reject(new Error('401')); }};
}
const up = function(){ return Promise.resolve(true); }, down = function(){ return Promise.resolve(false); };
const local = {mode: 'local', baseUrl: 'http://127.0.0.1:9119', token: 'SECRET-TOKEN'};
const remote = {mode: 'remote', baseUrl: 'https://gw.example.test/', token: 'SECRET-TOKEN'};
(async function(){
  const c1 = [], c2 = [], c3 = [], c4 = [], c5 = [];
  const r = {
    local_daemon_up: await P.resolvePaneFrameSrc('t_abc', {probe: up, desktop: desk(local, 'tk1', c1)}),
    local_daemon_down: await P.resolvePaneFrameSrc('t_abc', {probe: down, desktop: desk(local, 'tk2', c2)}),
    remote_ticket: await P.resolvePaneFrameSrc('t_abc', {probe: up, desktop: desk(remote, 'tk3', c3)}),
    remote_no_ticket_daemon_up: await P.resolvePaneFrameSrc('t_abc', {probe: up, desktop: desk(remote, '', c4)}),
    remote_no_ticket_daemon_down: await P.resolvePaneFrameSrc('t_abc', {probe: down, desktop: desk(remote, '', c5)}),
    no_bridge_daemon_up: await P.resolvePaneFrameSrc('t_abc', {probe: up, desktop: null}),
    no_bridge_daemon_down: await P.resolvePaneFrameSrc('t_abc', {probe: down, desktop: null}),
    bad_id: await P.resolvePaneFrameSrc('../board', {probe: up, desktop: null}),
    bad_base: await P.resolvePaneFrameSrc('t_abc', {probe: down,
      desktop: desk({mode: 'remote', baseUrl: 'javascript:alert(1)'}, 'tk', [])}),
    calls: [c1, c2, c3, c4, c5]};
  console.log(JSON.stringify(r));
})();
""")
        self.assertEqual("http://127.0.0.1:8799/card/t_abc", out["local_daemon_up"])
        self.assertEqual("http://127.0.0.1:9119/api/plugins/crew/card/t_abc?ticket=tk2", out["local_daemon_down"])
        self.assertEqual("https://gw.example.test/api/plugins/crew/card/t_abc?ticket=tk3", out["remote_ticket"])
        self.assertEqual("http://127.0.0.1:8799/card/t_abc", out["remote_no_ticket_daemon_up"])
        self.assertIsNone(out["remote_no_ticket_daemon_down"])
        self.assertEqual("http://127.0.0.1:8799/card/t_abc", out["no_bridge_daemon_up"])
        self.assertIsNone(out["no_bridge_daemon_down"])
        self.assertIsNone(out["bad_id"])
        self.assertIsNone(out["bad_base"])
        # A local backend with the daemon up never mints a ticket; a remote one always asks the gateway first.
        self.assertEqual([[], ["/api/auth/ws-ticket POST"], ["/api/auth/ws-ticket POST"],
                          ["/api/auth/ws-ticket POST"], ["/api/auth/ws-ticket POST"]], out["calls"])
        self.assertNotIn("SECRET-TOKEN", json.dumps(out))

    def test_tile_keeps_the_local_daemon_first(self):
        # CrewPage (the tile) is untouched by the pane: the local daemon on :8799 is still its first rung.
        with open(os.path.join(CREW_ROOT, "desktop", "plugin.js"), "r", encoding="utf-8") as f:
            src = f.read()
        self.assertIn("var LOCAL_BOARD_URL = 'http://127.0.0.1:8799/'", src)
        page = src[src.index("function CrewPage("):src.index("function CrewFlowGraphPane(")]
        first = page[page.index("async function resolveBoardUrl()"):]
        self.assertTrue(first.split("\n", 2)[1].strip().startswith("if (await probeLocalDaemon(1500))"))
        self.assertIn("jsx('iframe', {", page)


if __name__ == "__main__":
    unittest.main()

"""Hermes.Crew dashboard plugin — backend proxy routes.

Mounted at /api/plugins/crew/ by the dashboard plugin system
(hermes_cli.web_server._mount_plugin_api_routes).
Proxies requests to the local crew_graph_serve daemon at http://127.0.0.1:8799.
"""

from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import urllib.error
from urllib.parse import urlparse
from fastapi import APIRouter, Request, Response
from starlette.concurrency import run_in_threadpool

router = APIRouter()

UPSTREAM = os.environ.get("CREW_LOCAL_UPSTREAM", "http://127.0.0.1:8799")

# Daemon auto-spawn: a Hermes restart does not restart crew_graph_serve, so the proxy starts it on demand.
DAEMON_READY_TIMEOUT = 2.5          # seconds to wait for a freshly spawned daemon to accept connections
DAEMON_SPAWN_COOLDOWN = 10.0        # never spawn more than once per this window (a crashing daemon must not fork-bomb)
_LOOPBACK_HOSTS = ("127.0.0.1", "localhost", "::1")
_spawn_lock = threading.Lock()
_last_spawn = {"at": 0.0, "pid": None}


def _upstream_host_port() -> tuple[str, int]:
    parsed = urlparse(UPSTREAM)
    return (parsed.hostname or "127.0.0.1"), (parsed.port or 8799)


def _daemon_reachable(timeout: float = 0.5) -> bool:
    host, port = _upstream_host_port()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _hermes_home() -> str:
    env = (os.environ.get("HERMES_HOME") or "").strip()
    if env:
        return env
    try:
        from hermes_constants import get_hermes_home
        return str(get_hermes_home())
    except Exception:
        return os.path.expanduser("~/.hermes")


def _serve_script() -> str | None:
    """crew_graph_serve.py shipped next to this plugin (<plugin>/scripts/), else CREW_SERVE_SCRIPT."""
    env = (os.environ.get("CREW_SERVE_SCRIPT") or "").strip()
    candidates = [env] if env else []
    candidates.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                   "scripts", "crew_graph_serve.py"))
    for path in candidates:
        if path and os.path.isfile(path):
            return path
    return None


def _spawn_daemon(script: str, host: str, port: int) -> int | None:
    home = _hermes_home()
    env = dict(os.environ)
    env["HERMES_HOME"] = home
    env["CREW_GRAPH_BIND"] = host if host != "localhost" else "127.0.0.1"
    env["CREW_GRAPH_PORT"] = str(port)
    log_dir = os.path.join(home, "logs")
    log_fh = None
    try:
        os.makedirs(log_dir, exist_ok=True)
        log_fh = open(os.path.join(log_dir, "crew_graph_serve.log"), "ab")
    except OSError:
        log_fh = None
    sink = log_fh if log_fh is not None else subprocess.DEVNULL
    kwargs = {"stdin": subprocess.DEVNULL, "stdout": sink, "stderr": sink, "env": env,
              "cwd": os.path.dirname(script), "close_fds": True}
    if os.name == "nt":
        kwargs["creationflags"] = (getattr(subprocess, "DETACHED_PROCESS", 0x8)
                                   | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x200)
                                   | getattr(subprocess, "CREATE_NO_WINDOW", 0x8000000))
    else:
        kwargs["start_new_session"] = True
    try:
        proc = subprocess.Popen([sys.executable, script], **kwargs)
    finally:
        if log_fh is not None:
            log_fh.close()
    return proc.pid


def _ensure_daemon_running() -> bool:
    """True when the crew_graph_serve daemon answers on UPSTREAM; spawn it first when it does not.

    Only a loopback UPSTREAM is spawned (a remote one is not ours to start). Spawns are serialized
    and rate-limited; after a spawn it waits up to DAEMON_READY_TIMEOUT seconds for the port.
    """
    if _daemon_reachable():
        return True
    host, port = _upstream_host_port()
    if host.lower() not in _LOOPBACK_HOSTS or os.environ.get("CREW_DAEMON_AUTOSPAWN", "1") == "0":
        return False
    with _spawn_lock:
        if _daemon_reachable():
            return True
        now = time.monotonic()
        if now - _last_spawn["at"] >= DAEMON_SPAWN_COOLDOWN:
            script = _serve_script()
            if not script:
                return False
            try:
                _last_spawn["pid"] = _spawn_daemon(script, host, port)
            except OSError:
                return False
            _last_spawn["at"] = now
        deadline = time.monotonic() + DAEMON_READY_TIMEOUT
        while time.monotonic() < deadline:
            if _daemon_reachable(timeout=0.25):
                return True
            time.sleep(0.1)
        return _daemon_reachable()


def _dashboard_url() -> str:
    """Mirror crew_card.dashboard_url(): env var, then owner.json, then local."""
    env = (os.environ.get("CREW_DASHBOARD_URL") or "").strip()
    if env:
        return env.rstrip("/")
    hermes_home = os.environ.get("HERMES_HOME") or os.path.expanduser("~/.hermes")
    try:
        with open(os.path.join(hermes_home, "crew", "owner.json")) as fh:
            url = str(json.load(fh).get("dashboard_url") or "").strip()
        if url:
            return url.rstrip("/")
    except (OSError, ValueError, AttributeError):
        pass
    return "http://127.0.0.1:%s" % (os.environ.get("CREW_GRAPH_PORT") or "8799")


def _public_crew_url(request: Request) -> str:
    """Resolve the public standalone URL for crew based on the client request host."""
    env = (os.environ.get("CREW_DASHBOARD_URL") or "").strip()
    if env:
        return env.rstrip("/")
    proto = request.headers.get("x-forwarded-proto") or request.url.scheme or "http"
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or "127.0.0.1:9119"
    return f"{proto}://{host}/api/plugins/crew/board"


def _forward_once(url: str, request: Request, body: bytes | None = None) -> Response:
    req = urllib.request.Request(url, data=body, method=request.method)
    for k, v in request.headers.items():
        if k.lower() not in ("host", "content-length", "cookie", "authorization"):
            req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read()
            content_type = resp.headers.get("Content-Type", "text/plain")
            if "text/html" in content_type:
                html = content.decode("utf-8", errors="replace")
                # Rewrite absolute root paths to relative
                html = html.replace('href="/card/', 'href="card/')
                html = html.replace('fetch("/board.json', 'fetch("board.json')
                html = html.replace('fetch("/ack/', 'fetch("ack/')
                html = html.replace('"/card/', '"card/')

                # Fix brand logo and back-to-board links to prevent loading parent dashboard (nested UI)
                html = html.replace('href="/"', 'href="board"')
                html = html.replace("href='/'", "href='board'")

                # Fix avatars path to be relative so base href applies
                html = html.replace('"/avatars/', '"avatars/')
                html = html.replace("'/avatars/", "'avatars/")

                # Fix upper-right link: point to standalone crew board using client hostname
                public_crew_url = _public_crew_url(request)
                html = re.sub(
                    r'<a class=tailnet[^>]*>.*?</a>',
                    f'<a class="tailnet" href="{public_crew_url}" target="_blank" rel="noopener noreferrer" style="color: #34d399; text-decoration: underline; font-weight: 500;" title="Open standalone board in new tab">open in new tab ↗</a>',
                    html
                )

                # Dynamic theme sync: accept query params (bg, fg, theme) or default to #041c1c dark fallback
                default_dark_bg = "#041c1c"
                bg_param = request.query_params.get("bg")
                fg_param = request.query_params.get("fg")
                theme_param = request.query_params.get("theme") or ("light" if bg_param and bg_param.lower() in ("#fff", "#ffffff", "white") else "dark")
                if bg_param or theme_param:
                    theme_bg = bg_param or ("#ffffff" if theme_param == "light" else "#041c1c")
                    theme_fg = fg_param or ("#17171a" if theme_param == "light" else "#ffffff")
                    theme_style = f"""
<style id="hermes-theme-sync">
:root {{
  color-scheme: {theme_param} !important;
  --crew-scheme: {theme_param} !important;
  --crew-bg: {theme_bg} !important;
  --color-background: {theme_bg} !important;
  --crew-fg: {theme_fg} !important;
  --color-foreground: {theme_fg} !important;
}}
html, body, main#board, main, #main, .page-card {{
  background-color: {theme_bg} !important;
  color: {theme_fg} !important;
}}
</style>
"""
                else:
                    theme_style = ""
                # Inject base href so all relative resources resolve under /api/plugins/crew/
                token_param = request.query_params.get("token") or request.query_params.get("ticket")
                try:
                    from hermes_cli.web_server import _SESSION_TOKEN
                    auth_token = _SESSION_TOKEN
                except Exception:
                    auth_token = token_param or ""

                nonce_m = re.search(r'nonce=["\']([^"\']+)["\']', html)
                nonce_attr = f' nonce="{nonce_m.group(1)}"' if nonce_m else ""
                auth_script = f"""
<script id="crew-auth-sync"{nonce_attr}>
(function() {{
  var token = {json.dumps(auth_token)};
  function appendToken(url) {{
    if (typeof url !== 'string') return url;
    if (url.indexOf('board.json') !== -1 || url.indexOf('card/') !== -1 || url.indexOf('/card/') !== -1 || url.indexOf('ack/') !== -1 || url.indexOf('/ack/') !== -1 || url.indexOf('board') !== -1) {{
      var parts = url.split('#');
      var base = parts[0];
      var hash = parts.length > 1 ? ('#' + parts.slice(1).join('#')) : '';
      var query = base.indexOf('?') === -1 ? '' : base.split('?')[1];
      var rootUrl = base.split('?')[0];
      var params = new URLSearchParams(query);
      if (token && !params.has('token')) params.set('token', token);
      var curParams = new URLSearchParams(location.search);
      ['theme', 'bg', 'fg'].forEach(function(k){{
        if (curParams.has(k) && !params.has(k)) params.set(k, curParams.get(k));
      }});
      var q = params.toString();
      return rootUrl + (q ? ('?' + q) : '') + hash;
    }}
    return url;
  }}
  if (window.fetch) {{
    var origFetch = window.fetch;
    window.fetch = function(url, init) {{
      return origFetch.call(this, appendToken(url), init);
    }};
  }}
  if (window.XMLHttpRequest) {{
    var origOpen = XMLHttpRequest.prototype.open;
    XMLHttpRequest.prototype.open = function(method, url, async, user, password) {{
      return origOpen.call(this, method, appendToken(url), async, user, password);
    }};
  }}
  document.addEventListener('click', function(e) {{
    var a = e.target && e.target.closest ? e.target.closest('a') : null;
    if (a && a.href) {{
      if (a.href.indexOf('/card/') !== -1 || a.href.indexOf('card/') !== -1 || a.href.indexOf('/board') !== -1 || a.href.indexOf('board') !== -1) {{
        a.href = appendToken(a.href);
      }}
    }}
  }}, true);
}})();
</script>
"""
                if "<head>" in html and "<base " not in html:
                    html = html.replace("<head>", f'<head><base href="/api/plugins/crew/">{theme_style}{auth_script}', 1)
                content = html.encode("utf-8")
            res = Response(content=content, status_code=resp.status, media_type=content_type)
            token = request.query_params.get("token") or request.query_params.get("ticket")
            if token:
                try:
                    from hermes_cli.web_server import _SESSION_TOKEN
                    cookie_val = _SESSION_TOKEN
                except Exception:
                    cookie_val = token
                is_https = request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"
                res.set_cookie(
                    key="hermes_session",
                    value=cookie_val,
                    path="/api/plugins/crew/",
                    samesite="none" if is_https else "lax",
                    secure=is_https,
                    httponly=True,
                )
            return res
    except urllib.error.HTTPError as exc:
        res = Response(content=exc.read(), status_code=exc.code, media_type=exc.headers.get("Content-Type", "text/plain"))
        token = request.query_params.get("token")
        if token:
            res.set_cookie(
                key="hermes_session",
                value=token,
                path="/api/plugins/crew/",
                samesite="lax",
                httponly=True,
            )
        return res
    except Exception as exc:
        res = Response(
            content=f"<html><body><h3>Crew Dashboard Unavailable</h3><p>Could not reach {UPSTREAM} ({exc}). The proxy tried to start crew_graph_serve.py automatically; see $HERMES_HOME/logs/crew_graph_serve.log, or start it with serve-crew-dashboard.ps1.</p></body></html>",
            status_code=502,
            media_type="text/html"
        )
        res.headers["X-Crew-Upstream"] = "unreachable"
        token = request.query_params.get("token")
        if token:
            res.set_cookie(
                key="hermes_session",
                value=token,
                path="/api/plugins/crew/",
                samesite="lax",
                httponly=True,
            )
        return res


def _forward_request(url: str, request: Request, body: bytes | None = None) -> Response:
    """Forward to the local daemon, starting it first when it is down; retry once after a spawn."""
    _ensure_daemon_running()
    res = _forward_once(url, request, body)
    if res.status_code == 502 and res.headers.get("X-Crew-Upstream") == "unreachable":
        if _ensure_daemon_running():
            res = _forward_once(url, request, body)
    return res


async def _proxy(url: str, request: Request, body: bytes | None = None) -> Response:
    # urllib + a possible spawn wait block: keep them off the dashboard's event loop.
    return await run_in_threadpool(_forward_request, url, request, body)


@router.get("/board")
async def get_board(request: Request):
    query = str(request.url.query)
    target = f"{UPSTREAM}/" + (f"?{query}" if query else "")
    return await _proxy(target, request)


@router.get("/board.json")
async def get_board_json(request: Request):
    query = str(request.url.query)
    target = f"{UPSTREAM}/board.json" + (f"?{query}" if query else "")
    return await _proxy(target, request)


@router.api_route("/card/{path:path}", methods=["GET"])
async def get_card(path: str, request: Request):
    query = str(request.url.query)
    target = f"{UPSTREAM}/card/{path}" + (f"?{query}" if query else "")
    return await _proxy(target, request)


@router.api_route("/ack/{path:path}", methods=["POST"])
async def post_ack(path: str, request: Request):
    body = await request.body()
    target = f"{UPSTREAM}/ack/{path}"
    return await _proxy(target, request, body=body)


@router.api_route("/avatars/{path:path}", methods=["GET"])
async def get_avatars(path: str, request: Request):
    query = str(request.url.query)
    target = f"{UPSTREAM}/avatars/{path}" + (f"?{query}" if query else "")
    return await _proxy(target, request)


@router.get("/healthz")
async def get_healthz(request: Request):
    target = f"{UPSTREAM}/healthz"
    return await _proxy(target, request)

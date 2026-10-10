"""Hermes.Crew dashboard plugin — backend proxy routes.

Mounted at /api/plugins/crew/ by the dashboard plugin system
(hermes_cli.web_server._mount_plugin_api_routes).
Proxies requests to the local crew_graph_serve daemon at http://127.0.0.1:8799.
"""

from __future__ import annotations

import json
import os
import re
import urllib.request
import urllib.error
from fastapi import APIRouter, Request, Response

router = APIRouter()

UPSTREAM = os.environ.get("CREW_LOCAL_UPSTREAM", "http://127.0.0.1:8799")


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


def _forward_request(url: str, request: Request, body: bytes | None = None) -> Response:
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
            content=f"<html><body><h3>Crew Dashboard Unavailable</h3><p>Could not reach {UPSTREAM} ({exc}). Ensure the crew dashboard service is running.</p></body></html>",
            status_code=502,
            media_type="text/html"
        )
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


@router.get("/board")
async def get_board(request: Request):
    query = str(request.url.query)
    target = f"{UPSTREAM}/" + (f"?{query}" if query else "")
    return _forward_request(target, request)


@router.get("/board.json")
async def get_board_json(request: Request):
    query = str(request.url.query)
    target = f"{UPSTREAM}/board.json" + (f"?{query}" if query else "")
    return _forward_request(target, request)


@router.api_route("/card/{path:path}", methods=["GET"])
async def get_card(path: str, request: Request):
    query = str(request.url.query)
    target = f"{UPSTREAM}/card/{path}" + (f"?{query}" if query else "")
    return _forward_request(target, request)


@router.api_route("/ack/{path:path}", methods=["POST"])
async def post_ack(path: str, request: Request):
    body = await request.body()
    target = f"{UPSTREAM}/ack/{path}"
    return _forward_request(target, request, body=body)


@router.api_route("/avatars/{path:path}", methods=["GET"])
async def get_avatars(path: str, request: Request):
    query = str(request.url.query)
    target = f"{UPSTREAM}/avatars/{path}" + (f"?{query}" if query else "")
    return _forward_request(target, request)


@router.get("/healthz")
async def get_healthz(request: Request):
    target = f"{UPSTREAM}/healthz"
    return _forward_request(target, request)

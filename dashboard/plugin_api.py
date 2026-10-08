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

                # Inject theme override to match Hermes Dashboard background and style
                theme_style = """
<style id="hermes-theme-sync">
:root {
  --color-background: #041c1c !important;
  --crew-bg: #041c1c !important;
  --color-foreground: #ffffff !important;
  --crew-fg: #ffffff !important;
}
html, body, main#board {
  background-color: #041c1c !important;
  color: #e2e8f0 !important;
}
header {
  background-color: #031515 !important;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08) !important;
}
.lane {
  background-color: rgba(255, 255, 255, 0.02) !important;
  border: 1px solid rgba(255, 255, 255, 0.06) !important;
}
.card {
  background-color: #062323 !important;
  border: 1px solid rgba(255, 255, 255, 0.08) !important;
}
</style>
"""
                # Inject base href so all relative resources resolve under /api/plugins/crew/
                if "<head>" in html and "<base " not in html:
                    html = html.replace("<head>", f'<head><base href="/api/plugins/crew/">{theme_style}', 1)
                content = html.encode("utf-8")
            return Response(content=content, status_code=resp.status, media_type=content_type)
    except urllib.error.HTTPError as exc:
        return Response(content=exc.read(), status_code=exc.code, media_type=exc.headers.get("Content-Type", "text/plain"))
    except Exception as exc:
        return Response(
            content=f"<html><body><h3>Crew Dashboard Unavailable</h3><p>Could not reach {UPSTREAM} ({exc}). Ensure the crew dashboard service is running.</p></body></html>",
            status_code=502,
            media_type="text/html"
        )


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

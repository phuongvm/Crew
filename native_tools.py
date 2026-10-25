"""Native Hermes tools for the Crew plugin.

Provides first-class Hermes tool definitions (JSON Schemas) and handlers
for card creation, status inspection, diagnosis, and verdict recording,
registered via `ctx.register_tool()`.
"""

from __future__ import annotations

import contextlib
import io
import os
import re
import sys
import types
from typing import Any, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.join(HERE, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)


def _card_tool():
    """Load scripts/crew_card.py."""
    try:
        import crew_card  # type: ignore[import-not-found]
        return crew_card
    except Exception:
        return None


def _diagnose_tool():
    """Load scripts/crew_diagnose.py."""
    try:
        import crew_diagnose  # type: ignore[import-not-found]
        return crew_diagnose
    except Exception:
        return None


# ---------------------------------------------------------------- schemas

CREW_CARD_CREATE_SCHEMA = {
    "name": "crew_card_create",
    "description": (
        "Create a contract-guarded Crew Kanban card without spawning external shell processes. "
        "Enforces role verification, token budget floors, and proof contract requirements."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Short title for the card (max 120 characters)."
            },
            "role": {
                "type": "string",
                "enum": ["worker", "content", "verifier", "reviewer"],
                "description": "The assigned Crew role for the card (worker, content, verifier, reviewer)."
            },
            "goal": {
                "type": "string",
                "description": "Full goal/objective description. Defaults to title if omitted."
            },
            "artifact": {
                "type": "string",
                "description": "Primary artifact produced or modified (file path, repo, PR)."
            },
            "lands": {
                "type": "string",
                "description": "Target workspace directory or destination for artifact. Defaults to '.' if omitted."
            },
            "audience": {
                "type": "string",
                "description": "Target audience (e.g. 'commander', 'team', 'users'). Defaults to 'commander' if omitted."
            },
            "done_when": {
                "type": "string",
                "description": "Acceptance criteria / Definition of Done. Defaults to 'proof command passes' if omitted."
            },
            "proof_cmd": {
                "type": "string",
                "description": "Deterministic shell/python command to verify completion."
            },
            "budget": {
                "type": "integer",
                "description": "Token budget for the card. Defaults to role default or minimum budget floor."
            },
            "verify": {
                "type": "string",
                "enum": ["proof", "independent", "agent", "dual"],
                "description": "Verification mode for the card. Defaults to 'proof'."
            },
            "proof_mode": {
                "type": "string",
                "enum": ["safe", "brave"],
                "description": "Proof execution mode ('safe' or 'brave'). Defaults to 'safe'."
            },
            "constraints": {
                "type": "string",
                "description": "Operational constraints (e.g. Zero-Checkout invariant, dependencies, isolation rules)."
            },
            "inputs": {
                "type": "string",
                "description": "Inputs for the card (e.g. paths, URLs, references)."
            },
            "units": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Deliverable units for multi-unit progress tracking."
            },
            "proof_approved": {
                "type": "boolean",
                "description": "If true, mark the proof as approved."
            },
            "parents": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of parent task IDs."
            },
            "skills": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional additional skills to force-load on the worker."
            },
            "dry_run": {
                "type": "boolean",
                "description": "If true, validate contract and return card preview without writing to Kanban database."
            },
            "allow_no_proof": {
                "type": "boolean",
                "description": "If true, allow creating the card without an automated proof command."
            },
            "initial_status": {
                "type": "string",
                "description": "Initial Kanban status (e.g., 'todo', 'triage')."
            }
        },
        "required": ["title", "role"]
    }
}

CREW_DIAGNOSE_SCHEMA = {
    "name": "crew_diagnose",
    "description": (
        "Inspect and diagnose cards sitting in a given Kanban board state or lookup a specific card by ID. Read-only."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "state": {
                "type": "string",
                "enum": ["blocked", "triage", "todo", "ready", "running", "done", "archived"],
                "description": "Filter cards by state. Defaults to 'blocked'."
            },
            "card": {
                "type": "string",
                "description": "Specific card ID to diagnose (e.g. 't_ab12cd34'). Overrides state filter."
            },
            "card_id": {
                "type": "string",
                "description": "Specific card ID to diagnose (alias for card). Overrides state filter."
            },
            "format": {
                "type": "string",
                "enum": ["text", "json"],
                "description": "Output format: 'text' (human-readable summary) or 'json' (structured data). Defaults to 'text'."
            }
        }
    }
}

CREW_VERDICT_SCHEMA = {
    "name": "crew_verdict",
    "description": (
        "Run and record the owner-confirmed verification proof command for a card, "
        "enforcing safety preflights and automatic rework limits."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "card_id": {
                "type": "string",
                "description": "The target card ID (e.g., 't_1234abcd')."
            },
            "card": {
                "type": "string",
                "description": "The target card ID (alias for card_id)."
            },
            "command": {
                "type": "string",
                "description": "Optional command override. Must match the owner-confirmed proof command; unconfirmed commands will be refused."
            },
            "timeout": {
                "type": "integer",
                "description": "Execution timeout in seconds. Defaults to 300."
            },
            "by": {
                "type": "string",
                "description": "Identifier of the reviewing agent/profile. Defaults to current profile or 'crew-verifier'."
            },
            "no_hand_back": {
                "type": "boolean",
                "description": "If true, do not automatically request changes or hand back on 2nd failure."
            }
        },
        "required": ["card_id"]
    }
}

CREW_STATUS_SCHEMA = {
    "name": "crew_status",
    "description": (
        "View in-flight Crew cards, their current status, latest coordinator decisions, and any questions waiting on the owner."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "description": "Maximum number of in-flight cards to display. Defaults to 8."
            },
            "format": {
                "type": "string",
                "enum": ["text", "json"],
                "description": "Output format: 'text' (formatted summary) or 'json' (structured card list). Defaults to 'text'."
            }
        }
    }
}

CREW_EVENT_SUBSCRIBE_SCHEMA = {
    "name": "crew_event_subscribe",
    "description": (
        "Subscribe an HTTP/REST webhook URL to receive real-time Crew card lifecycle events "
        "(card_created, card_claimed, card_blocked, card_review, card_completed), or manage existing subscriptions."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["subscribe", "unsubscribe", "list", "clear"],
                "description": "Subscription action: 'subscribe' (default), 'unsubscribe', 'list', or 'clear'."
            },
            "url": {
                "type": "string",
                "description": "Webhook endpoint URL (required for subscribe and unsubscribe)."
            },
            "events": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Event kinds to subscribe to (e.g. ['card_created', 'card_completed'], or ['*'] for all). Defaults to ['*']."
            },
            "headers": {
                "type": "object",
                "description": "Optional HTTP headers to include with webhook POST requests (e.g. auth tokens)."
            },
            "format": {
                "type": "string",
                "enum": ["text", "json"],
                "description": "Output format: 'text' or 'json'. Defaults to 'text'."
            }
        }
    }
}


# ---------------------------------------------------------------- handlers


def handle_crew_card_create(args: dict, **kwargs: Any) -> dict[str, Any]:
    """Handler for crew_card_create."""
    if not isinstance(args, dict):
        return {"status": "error", "error": "arguments must be a JSON object"}
    title = str(args.get("title") or "").strip()
    role = str(args.get("role") or "").strip().lower()
    if not title:
        return {"status": "error", "error": "title is required"}
    if not role:
        return {"status": "error", "error": "role is required"}

    c: dict[str, Any] = {
        "title": title,
        "role": role,
        "goal": str(args.get("goal") or title).strip(),
        "artifact": str(args.get("artifact") or "workspace changes").strip(),
        "lands": str(args.get("lands") or ".").strip(),
        "audience": str(args.get("audience") or "commander").strip(),
        "done_when": str(args.get("done_when") or "proof command passes").strip(),
        "proof_cmd": str(args.get("proof_cmd") or "").strip(),
        "verify": str(args.get("verify") or "proof").strip(),
    }
    if args.get("budget"):
        try:
            c["budget"] = int(args["budget"])
        except (ValueError, TypeError):
            pass
    if args.get("proof_mode"):
        c["proof_mode"] = str(args["proof_mode"]).strip().lower()
    if args.get("proof_approved"):
        c["proof_approved"] = bool(args["proof_approved"])
    if args.get("units"):
        c["units"] = args["units"]
    if args.get("inputs"):
        c["inputs"] = str(args["inputs"])
    if args.get("constraints"):
        c["constraints"] = str(args["constraints"]).strip()

    dry_run = bool(args.get("dry_run", False))
    allow_no_proof = bool(args.get("allow_no_proof", False))
    parents = tuple(args.get("parents") or ())
    initial_status = args.get("initial_status")

    if not c["proof_cmd"] and not allow_no_proof:
        return {"status": "error", "error": "proof_cmd is required unless allow_no_proof is True"}

    try:
        mod = _card_tool()
        if mod is None:
            return {"status": "error", "error": "crew_card module could not be loaded"}
        res = mod.open_card(
            c,
            dry_run=dry_run,
            allow_no_proof=allow_no_proof,
            parents=parents,
            initial_status=initial_status,
        )
        if isinstance(res, dict) and not dry_run:
            cid = res.get("id") or res.get("task_id")
            if cid:
                try:
                    try:
                        from .runtime_events import emit_card_event, CARD_CREATED
                    except ImportError:
                        from runtime_events import emit_card_event, CARD_CREATED
                    emit_card_event(
                        CARD_CREATED,
                        card_id=cid,
                        status=str(initial_status or "running"),
                        title=title,
                        role=role,
                    )
                except Exception:
                    pass
        return {"status": "ok", "card": res}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def handle_crew_diagnose(args: dict, **kwargs: Any) -> Any:
    """Handler for crew_diagnose."""
    if not isinstance(args, dict):
        args = {}
    state = str(args.get("state") or "blocked").strip().lower()
    card_id = (args.get("card") or args.get("card_id") or "").strip() or None
    fmt = str(args.get("format") or "text").strip().lower()

    diag_mod = _diagnose_tool()
    if diag_mod is None:
        err = "crew_diagnose module could not be loaded"
        return {"status": "error", "error": err} if fmt == "json" else f"error: {err}"

    if not card_id and state not in diag_mod.STATES:
        err = f"unknown state {state!r}: must be one of {', '.join(diag_mod.STATES)}"
        return {"status": "error", "error": err} if fmt == "json" else f"error: {err}"

    try:
        rows = diag_mod.board_rows(None if card_id else state, card_id)
        if rows is None:
            err = "no board to read: kanban database missing"
            return {"status": "error", "error": err} if fmt == "json" else f"error: {err}"

        cards = diag_mod.cards_from_rows(rows)
        if fmt == "json":
            return {
                "status": "ok",
                "state": state if not card_id else None,
                "card_id": card_id,
                "count": len(cards),
                "cards": cards,
            }
        return diag_mod.render(cards, state, card_id)
    except Exception as exc:
        err = str(exc)
        return {"status": "error", "error": err} if fmt == "json" else f"error: {err}"


def handle_crew_verdict(args: dict, **kwargs: Any) -> dict[str, Any]:
    """Handler for crew_verdict."""
    if not isinstance(args, dict):
        return {"status": "error", "error": "arguments must be a JSON object"}
    card_id = str(args.get("card") or args.get("card_id") or "").strip()
    if not card_id:
        return {"status": "error", "error": "card or card_id is required"}

    command = args.get("command")
    if command is not None:
        command = str(command).strip()

    timeout = 300
    if args.get("timeout"):
        try:
            timeout = int(args["timeout"])
        except (ValueError, TypeError):
            pass

    card_mod = _card_tool()
    if card_mod is None:
        return {"status": "error", "error": "crew_card module could not be loaded"}

    by = args.get("by") or card_mod.current_profile() or "crew-verifier"
    no_hand_back = bool(args.get("no_hand_back", False))

    verdict_args = types.SimpleNamespace(
        card=card_id,
        command=command,
        timeout=timeout,
        by=by,
        no_hand_back=no_hand_back,
        for_event=None,
    )

    stdout_buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(stdout_buf):
            rc = card_mod.cmd_verdict(verdict_args)
        captured = stdout_buf.getvalue()
        verdict_str = "PASS" if rc == 0 else "FAIL"
        try:
            try:
                from .runtime_events import emit_card_event, CARD_UPDATED
            except ImportError:
                from runtime_events import emit_card_event, CARD_UPDATED
            emit_card_event(
                CARD_UPDATED,
                card_id=card_id,
                status="verified" if rc == 0 else "verification_failed",
                verdict=verdict_str,
                exit_code=rc,
                by=by,
            )
        except Exception:
            pass
        return {
            "status": "ok",
            "verdict": verdict_str,
            "card_id": card_id,
            "exit_code": rc,
            "output": captured.strip(),
        }
    except Exception as exc:
        return {
            "status": "error",
            "error": str(exc),
            "output": stdout_buf.getvalue().strip(),
        }


def handle_crew_status(args: dict, **kwargs: Any) -> Any:
    """Handler for crew_status."""
    if not isinstance(args, dict):
        args = {}
    limit = 8
    if args.get("limit"):
        try:
            limit = int(args["limit"])
        except (ValueError, TypeError):
            pass
    fmt = str(args.get("format") or "text").strip().lower()

    card_mod = _card_tool()
    if card_mod is None:
        err = "crew_card module could not be loaded"
        return {"status": "error", "error": err} if fmt == "json" else f"error: {err}"

    try:
        if fmt == "json":
            got = card_mod.status_cards(limit=limit)
            if got is None:
                return {"status": "error", "error": "No kanban database found"}
            cards, total = got
            return {
                "status": "ok",
                "total": total,
                "count": len(cards),
                "cards": cards,
            }
        return card_mod.status_text(limit=limit)
    except Exception as exc:
        err = str(exc)
        return {"status": "error", "error": err} if fmt == "json" else f"error: {err}"


def handle_crew_event_subscribe(args: dict, **kwargs: Any) -> Any:
    """Handler for crew_event_subscribe."""
    if not isinstance(args, dict):
        args = {}
    action = str(args.get("action") or "subscribe").strip().lower()
    fmt = str(args.get("format") or "text").strip().lower()
    url = str(args.get("url") or "").strip()
    events = args.get("events")
    headers = args.get("headers")

    try:
        try:
            from .runtime_events import get_webhook_manager
        except ImportError:
            from runtime_events import get_webhook_manager

        mgr = get_webhook_manager()

        if action == "subscribe":
            if not url:
                err = "url is required for action='subscribe'"
                return {"status": "error", "error": err} if fmt == "json" else f"error: {err}"

            res = mgr.register(url=url, events=events, headers=headers)
            if fmt == "json":
                return res
            ev_str = ", ".join(res["events"])
            return f"Subscribed {url} to events: [{ev_str}] (active webhooks: {res['active_webhooks']})"

        elif action == "unsubscribe":
            if not url:
                err = "url is required for action='unsubscribe'"
                return {"status": "error", "error": err} if fmt == "json" else f"error: {err}"
            ok = mgr.unregister(url)
            if fmt == "json":
                return {"status": "ok" if ok else "not_found", "unregistered": ok, "url": url}
            return f"Unsubscribed {url}" if ok else f"Webhook {url} not found"

        elif action == "list":
            items = mgr.list_all()
            if fmt == "json":
                return {"status": "ok", "count": len(items), "webhooks": items}
            if not items:
                return "No active webhook subscriptions"
            lines = [f"Active webhooks ({len(items)}):"]
            for item in items:
                lines.append(f"  - {item['url']} -> {item['events']}")
            return "\n".join(lines)

        elif action == "clear":
            cleared = mgr.clear()
            if fmt == "json":
                return {"status": "ok", "cleared": cleared}
            return f"Cleared {cleared} webhook subscription(s)"

        else:
            err = f"unknown action {action!r}"
            return {"status": "error", "error": err} if fmt == "json" else f"error: {err}"

    except Exception as exc:
        err = str(exc)
        return {"status": "error", "error": err} if fmt == "json" else f"error: {err}"


# ---------------------------------------------------------------- registration


CREW_NATIVE_TOOLS = [
    ("crew_card_create", CREW_CARD_CREATE_SCHEMA, handle_crew_card_create),
    ("crew_diagnose", CREW_DIAGNOSE_SCHEMA, handle_crew_diagnose),
    ("crew_verdict", CREW_VERDICT_SCHEMA, handle_crew_verdict),
    ("crew_status", CREW_STATUS_SCHEMA, handle_crew_status),
    ("crew_event_subscribe", CREW_EVENT_SUBSCRIBE_SCHEMA, handle_crew_event_subscribe),
]


# ================================================================ extended tools
# OpenSpec change `crew-extended-tools`: 8 tools across Core, Pipeline, Workspace and Intelligence ops.
# Every handler returns a dict with `status` ("ok" | "error" | "refused" | "dry_run"); none raises.


def _load(name: str) -> Any:
    """Import a sibling script module from scripts/ by name, or None when it cannot load."""
    try:
        return __import__(name)
    except Exception:
        return None


def _contracts() -> Any:
    try:
        from . import contracts as mod  # type: ignore[attr-defined]
    except ImportError:
        import contracts as mod  # type: ignore[no-redef]
    return mod


def _emit(kind_name: str, card_id: str, status: str, **extra: Any) -> None:
    """Best-effort runtime event: a bus failure never fails the tool."""
    try:
        try:
            from . import runtime_events as rev  # type: ignore[attr-defined]
        except ImportError:
            import runtime_events as rev  # type: ignore[no-redef]
        rev.emit_card_event(getattr(rev, kind_name), card_id=card_id, status=status, **extra)
    except Exception:
        pass


def _err(msg: str, **extra: Any) -> dict[str, Any]:
    out: dict[str, Any] = {"status": "error", "error": msg}
    out.update(extra)
    return out


def _args(args: Any) -> dict:
    return args if isinstance(args, dict) else {}


def _card_id_arg(args: dict) -> str:
    return str(args.get("card_id") or "").strip()


# ---------------------------------------------------------------- schemas (extended)

CREW_STOP_CARD_SCHEMA = {
    "name": "crew_stop_card",
    "description": (
        "Core ops: stop ONE crew card without destroying it - kill its own worker process, close the sessions it "
        "left open, and park the card for the owner (resume with /crew-unstuck). `archive=true` drops it instead."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "card_id": {"type": "string", "description": "The card to stop (e.g. 't_ab12cd34'). Required."},
            "archive": {"type": "boolean", "description": "Archive the card instead of parking it. Default false."},
            "dry_run": {"type": "boolean", "description": "Report what would be stopped without acting. Default false."},
        },
        "required": ["card_id"],
    },
}

CREW_REVIEW_HANDOFF_SCHEMA = {
    "name": "crew_review_handoff",
    "description": (
        "Pipeline ops: hand an independent-verification crew card to its verifier's review step "
        "(model pin swapped for the review pick, card moved to `review`), or preview the prior-run hand-off "
        "context a retried worker receives. `Verify: proof`, `agent`, and `closeout` cards are refused."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "card_id": {"type": "string", "description": "The card to hand off. Required."},
            "action": {"type": "string", "enum": ["handoff", "preview"],
                       "description": "'handoff' (default) moves the card to review; 'preview' returns the hand-off text only."},
            "summary": {"type": "string", "description": "What was implemented and how it was verified (required for handoff)."},
            "reviewer": {"type": "string", "description": "Reviewer profile. Defaults to the crew verifier profile."},
        },
        "required": ["card_id"],
    },
}

CREW_REQUEST_CHANGES_SCHEMA = {
    "name": "crew_request_changes",
    "description": (
        "Pipeline ops: reviewer verdict - return a card in an active review run to its implementer with the "
        "concrete changes required. Refused when the card is not in a review run."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "card_id": {"type": "string", "description": "The card under review. Required."},
            "reason": {"type": "string", "description": "The exact fix the implementer must make (min 10 characters). Required."},
        },
        "required": ["card_id", "reason"],
    },
}

CREW_PLAN_SPLIT_SCHEMA = {
    "name": "crew_plan_split",
    "description": (
        "Pipeline ops: split one goal into parallel child cards (one writer per artifact, each with its own proof "
        "command) under a parent contract card and a coordinator close-out card. Dry run by default."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Plan title."},
            "goal": {"type": "string", "description": "The overall goal the children deliver together."},
            "done_when": {"type": "string", "description": "Plan-level definition of done."},
            "children": {
                "type": "array",
                "description": "Child card contracts (title, role, goal, artifact, lands, audience, done_when, proof_cmd, ...).",
                "items": {"type": "object"},
            },
            "dry_run": {"type": "boolean", "description": "Validate and preview without writing cards. Default true."},
        },
        "required": ["goal", "children"],
    },
}

CREW_WORKTREE_CREATE_SCHEMA = {
    "name": "crew_worktree_create",
    "description": (
        "Workspace ops: create a dedicated git worktree `<worktrees_root>/<name>` on a new branch, never switching "
        "the branch of the production checkout (Zero-Checkout invariant). Protected branches are refused."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "repo": {"type": "string", "description": "Path to the source repository (the production checkout). Required."},
            "name": {"type": "string", "description": "Worktree folder name, one path segment [A-Za-z0-9._-]. Required."},
            "branch": {"type": "string", "description": "New branch to create in the worktree. Required."},
            "base": {"type": "string", "description": "Commit-ish to branch from. Defaults to HEAD."},
            "worktrees_root": {"type": "string",
                               "description": "Parent folder of worktrees. Defaults to $CREW_WORKTREES_ROOT, else the "
                                              "nearest ancestor `.worktrees` folder of the repo, else <repo parent>/.worktrees."},
            "dry_run": {"type": "boolean", "description": "Return the planned git command without running it."},
        },
        "required": ["repo", "name", "branch"],
    },
}

CREW_WORKTREE_CLEANUP_SCHEMA = {
    "name": "crew_worktree_cleanup",
    "description": (
        "Workspace ops: remove a dedicated git worktree `<worktrees_root>/<name>` registered on the repo and prune "
        "its metadata. Refuses the main worktree, unregistered paths and dirty worktrees (unless force)."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "repo": {"type": "string", "description": "Path to the source repository. Required."},
            "name": {"type": "string", "description": "Worktree folder name under the worktrees root. Required."},
            "worktrees_root": {"type": "string", "description": "Parent folder of worktrees (same default as crew_worktree_create)."},
            "delete_branch": {"type": "boolean", "description": "Also delete the worktree's branch (safe delete unless force)."},
            "force": {"type": "boolean", "description": "Remove even with uncommitted changes; force-delete the branch."},
            "dry_run": {"type": "boolean", "description": "Report what would be removed without acting."},
        },
        "required": ["repo", "name"],
    },
}

CREW_FLOW_GRAPH_SCHEMA = {
    "name": "crew_flow_graph",
    "description": (
        "Intelligence ops: render a card's process flow (brief, coordinator card, runs, verifier, close-out, "
        "children) as a Mermaid flowchart or structured JSON. Read-only."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "card_id": {"type": "string", "description": "Card id, or 'latest' for the most recent card. Defaults to 'latest'."},
            "direction": {"type": "string", "enum": ["TD", "TB", "LR", "RL", "BT"], "description": "Mermaid direction. Default TD."},
            "format": {"type": "string", "enum": ["mermaid", "json"], "description": "Output: 'mermaid' (default) or 'json'."},
        },
    },
}

CREW_LESSON_RECORD_SCHEMA = {
    "name": "crew_lesson_record",
    "description": (
        "Intelligence ops: record a one-or-two-line lesson for a crew role (injected into that role's future turns), "
        "or show the lessons that apply to a role. Agents may not write `all` lessons."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["add", "show"], "description": "'add' (default) or 'show'."},
            "role": {"type": "string", "description": "worker, content, verifier, coordinator or all. Required."},
            "text": {"type": "string", "description": "The lesson (max 400 characters). Required for add."},
        },
        "required": ["role"],
    },
}


# ---------------------------------------------------------------- 1. Core ops


def handle_crew_stop_card(args: dict, **kwargs: Any) -> dict[str, Any]:
    """Handler for crew_stop_card: park (or archive) one crew card via crew_stop.stop_card."""
    args = _args(args)
    card_id = _card_id_arg(args)
    if not card_id:
        return _err("card_id is required")
    archive = bool(args.get("archive", False))
    dry_run = bool(args.get("dry_run", False))
    card_mod = _card_tool()
    stop_mod = _load("crew_stop")
    if card_mod is None or stop_mod is None:
        return _err("crew_stop module could not be loaded")
    try:
        db = card_mod.kanban_db()
        if not db:
            return _err("no board to read: kanban database missing")
        # crew_stop binds its board at import time; point it at the board resolved now, for this call only
        prev_db, stop_mod.KANBAN_DB = stop_mod.KANBAN_DB, db
        try:
            cards = stop_mod.q("select id, status, assignee, title, body from tasks where id = ?", (card_id,))
            if not cards:
                return _err("no such card: %s" % card_id)
            card = dict(cards[0])
            if not stop_mod.is_crew_card(card):
                return {"status": "refused", "card_id": card_id,
                        "error": "card %s is not a crew card (no Coordinator:/Role: line); it is never touched"
                                 % card_id}
            lines, ok, facts = stop_mod.stop_card(card, dry=dry_run, archive=archive)
        finally:
            stop_mod.KANBAN_DB = prev_db
        if ok and not dry_run:
            _emit("CARD_ABANDONED" if archive else "CARD_BLOCKED", card_id,
                  "archived" if archive else str(facts.get("after", ["?"])[0]), how=facts.get("how"))
        return {
            "status": "dry_run" if dry_run else ("ok" if ok else "error"),
            "card_id": card_id,
            "stopped": bool(ok),
            "archived": bool(archive and ok and not dry_run),
            "facts": facts,
            "report": "\n".join(lines),
        }
    except Exception as exc:
        return _err(str(exc), card_id=card_id)


# ---------------------------------------------------------------- 2. Pipeline ops


def handle_crew_review_handoff(args: dict, **kwargs: Any) -> dict[str, Any]:
    """Handler for crew_review_handoff: verifier handoff for independent or dual cards, or hand-off preview."""
    args = _args(args)
    card_id = _card_id_arg(args)
    if not card_id:
        return _err("card_id is required")
    action = str(args.get("action") or "handoff").strip().lower()
    card_mod = _card_tool()
    if card_mod is None:
        return _err("crew_card module could not be loaded")
    try:
        if action == "preview":
            ho = _load("crew_handoff")
            if ho is None:
                return _err("crew_handoff module could not be loaded")
            db = card_mod.kanban_db()
            if not db:
                return _err("no board to read: kanban database missing")
            prev_db, ho.KANBAN_DB = ho.KANBAN_DB, db
            try:
                text = ho.handoff_text(card_id)
            finally:
                ho.KANBAN_DB = prev_db
            return {"status": "ok", "card_id": card_id, "action": "preview", "has_prior_runs": bool(text),
                    "handoff": text}
        if action != "handoff":
            return _err("unknown action %r: use handoff or preview" % action)
        summary = str(args.get("summary") or "").strip()
        if not summary:
            return _err("summary is required for action='handoff'")
        row = card_mod.card_row(card_id)
        if not row:
            return _err("no such card: %s" % card_id)
        mode = card_mod.verify_mode(row[4])
        if mode == "proof":
            return {"status": "refused", "card_id": card_id, "verify": mode,
                    "error": "card %s is `Verify: proof`: no verifier session runs on it; run crew_verdict and "
                             "complete it with the raw proof output" % card_id}
        if mode == "closeout":
            return {"status": "refused", "card_id": card_id, "verify": mode,
                    "error": "card %s is `Verify: closeout` (one part of a split): complete it directly" % card_id}
        if mode == "agent":
            return {"status": "refused", "card_id": card_id, "verify": mode,
                    "error": "card %s is `Verify: agent`: a standalone verifier card is never submitted for review "
                             "(it is completed directly by the verifier via kanban_complete after crew_verdict PASS)" % card_id}
        if mode not in ("independent", "dual"):
            return {"status": "refused", "card_id": card_id, "verify": mode or None,
                    "error": "card %s has no independent `Verify:` line; there is no verifier to hand it to" % card_id}
        reviewer = str(args.get("reviewer") or "").strip() or card_mod.role_profile("verifier")
        try:
            card_mod.repin_for_review(card_id)
        except Exception:
            pass  # a pin that could not be swapped must not stop the review (same rule as the plugin guard)
        ok, why = card_mod.lift_into_review(card_id, reviewer, summary[:400])
        if ok:
            _emit("CARD_REVIEW", card_id, "review", reviewer=reviewer)
        return {"status": "ok" if ok else "error", "card_id": card_id, "verify": mode, "reviewer": reviewer,
                "moved_to_review": bool(ok), "detail": str(why)[-200:]}
    except Exception as exc:
        return _err(str(exc), card_id=card_id)


def handle_crew_request_changes(args: dict, **kwargs: Any) -> dict[str, Any]:
    """Handler for crew_request_changes: kernel request_changes on an active review run."""
    args = _args(args)
    card_id = _card_id_arg(args)
    reason = " ".join(str(args.get("reason") or "").split())
    gaps = _contracts().change_request_gaps(card_id, reason)
    if gaps:
        return _err("; ".join(gaps), gaps=list(gaps))
    card_mod = _card_tool()
    if card_mod is None:
        return _err("crew_card module could not be loaded")
    try:
        kb, conn = card_mod.kb_conn()
        try:
            ok, who = kb.request_changes(conn, card_id, reason=reason)
            status = None
            task = kb.get_task(conn, card_id)
            if task is not None:
                status = task.status
        finally:
            conn.close()
    except Exception as exc:
        return _err(str(exc), card_id=card_id)
    if not ok:
        return {"status": "refused", "card_id": card_id, "error": str(who or "request-changes refused")}
    _emit("CARD_UPDATED", card_id, "changes_requested", implementer=who, reason=reason[:200])
    return {"status": "ok", "card_id": card_id, "returned_to": who, "card_status": status, "reason": reason}


def handle_crew_plan_split(args: dict, **kwargs: Any) -> dict[str, Any]:
    """Handler for crew_plan_split: validated crew_card.run_plan (dry run by default).

    The close-out proof of an owner-confirmed split is crew code only (run_plan's `closeout_proof`); a tool caller
    can never set it, so every child of a tool split proves itself."""
    args = _args(args)
    spec_mod = _contracts().PlanSplitSpec
    spec = spec_mod.from_dict(args)
    gaps = spec.validate_gaps()
    if gaps:
        return _err("plan refused: " + "; ".join(gaps), gaps=list(gaps))
    dry_run = bool(args.get("dry_run", True))
    card_mod = _card_tool()
    if card_mod is None:
        return _err("crew_card module could not be loaded")
    try:
        res = card_mod.run_plan(spec.to_dict(), dry_run=dry_run)
    except Exception as exc:
        return _err(str(exc))
    if not dry_run:
        for child in res.get("children") or []:
            cid = child.get("id") if isinstance(child, dict) else None
            if cid:
                _emit("CARD_CREATED", cid, "todo", title=child.get("title"), role=child.get("role"),
                      parent=(res.get("parent") or {}).get("id"))
    return {"status": "dry_run" if dry_run else "ok", "child_count": len(res.get("children") or []), "plan": res}


# ---------------------------------------------------------------- 3. Workspace ops


def _norm(path: str) -> str:
    return os.path.normcase(os.path.normpath(os.path.abspath(path)))


def _git(git_mod: Any, repo: str, argv: list[str], timeout: int = 120) -> Any:
    return git_mod.run_git(["git", "-C", repo] + argv, repo=repo, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout)


def _toplevel(git_mod: Any, repo: str) -> str:
    res = _git(git_mod, repo, ["rev-parse", "--show-toplevel"], timeout=30)
    if res.returncode != 0:
        raise ValueError("not a git repository: %s (%s)" % (repo, (res.stderr or "").strip()[-200:]))
    return os.path.normpath((res.stdout or "").strip())


def worktrees_root_for(repo_top: str, explicit: Optional[str] = None) -> str:
    """Where dedicated worktrees live: explicit > $CREW_WORKTREES_ROOT > nearest ancestor `.worktrees` > sibling."""
    for cand in (explicit, os.environ.get("CREW_WORKTREES_ROOT")):
        if cand and str(cand).strip():
            return os.path.normpath(os.path.abspath(str(cand).strip()))
    cur = os.path.dirname(os.path.abspath(repo_top))
    while True:
        cand = os.path.join(cur, ".worktrees")
        if os.path.isdir(cand):
            return os.path.normpath(cand)
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    return os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(repo_top)), ".worktrees"))


def parse_worktree_porcelain(text: str) -> list[dict[str, Any]]:
    """`git worktree list --porcelain` -> [{path, head, branch, bare, detached}], main worktree first."""
    out: list[dict[str, Any]] = []
    cur: dict[str, Any] = {}
    for line in (text or "").splitlines() + [""]:
        line = line.rstrip("\r")
        if not line:
            if cur:
                out.append(cur)
                cur = {}
            continue
        key, _, val = line.partition(" ")
        if key == "worktree":
            cur = {"path": os.path.normpath(val), "head": "", "branch": "", "bare": False, "detached": False}
        elif key == "HEAD":
            cur["head"] = val
        elif key == "branch":
            cur["branch"] = val[len("refs/heads/"):] if val.startswith("refs/heads/") else val
        elif key in ("bare", "detached"):
            cur[key] = True
    return out


def handle_crew_worktree_create(args: dict, **kwargs: Any) -> dict[str, Any]:
    """Handler for crew_worktree_create: `git worktree add <root>/<name> -b <branch> <base>`; never a checkout."""
    args = _args(args)
    c = _contracts()
    repo = str(args.get("repo") or "").strip()
    name = str(args.get("name") or "").strip()
    branch = str(args.get("branch") or "").strip()
    base = str(args.get("base") or "HEAD").strip() or "HEAD"
    if not repo:
        return _err("repo is required")
    if not c.is_valid_worktree_name(name):
        return _err("name %r is not one safe path segment [A-Za-z0-9._-] (max 64)" % name)
    gaps = c.branch_name_gaps(branch)
    if gaps:
        return {"status": "refused", "error": "; ".join(gaps), "gaps": list(gaps)}
    if base.startswith("-"):
        return _err("base %r may not start with '-'" % base)
    git_mod = _load("git_safe")
    if git_mod is None:
        return _err("git_safe module could not be loaded")
    try:
        top = _toplevel(git_mod, repo)
        root = worktrees_root_for(top, args.get("worktrees_root"))
        path = os.path.join(root, name)
        if _norm(path) == _norm(top) or _norm(top).startswith(_norm(path) + os.sep):
            return {"status": "refused", "error": "worktree path %s would overlap the repository" % path}
        if os.path.exists(path):
            return {"status": "refused", "error": "worktree path already exists: %s" % path, "path": path}
        exists = _git(git_mod, top, ["rev-parse", "--verify", "--quiet", "refs/heads/" + branch], timeout=30)
        if exists.returncode == 0:
            return {"status": "refused", "error": "branch %r already exists in %s" % (branch, top), "branch": branch}
        argv = ["worktree", "add", path, "-b", branch, base]
        if bool(args.get("dry_run", False)):
            return {"status": "dry_run", "repo": top, "path": path, "branch": branch, "base": base,
                    "argv": ["git", "-C", top] + argv}
        os.makedirs(root, exist_ok=True)
        res = _git(git_mod, top, argv)
        if res.returncode != 0:
            return _err("git worktree add failed: %s" % ((res.stderr or res.stdout or "").strip()[-300:]),
                        path=path)
        head = _git(git_mod, path, ["rev-parse", "HEAD"], timeout=30)
        return {"status": "ok", "repo": top, "path": path, "branch": branch, "base": base,
                "head": (head.stdout or "").strip()}
    except Exception as exc:
        return _err(str(exc))


def handle_crew_worktree_cleanup(args: dict, **kwargs: Any) -> dict[str, Any]:
    """Handler for crew_worktree_cleanup: guarded `git worktree remove` + prune (+ optional branch delete)."""
    args = _args(args)
    c = _contracts()
    repo = str(args.get("repo") or "").strip()
    name = str(args.get("name") or "").strip()
    force = bool(args.get("force", False))
    delete_branch = bool(args.get("delete_branch", False))
    dry_run = bool(args.get("dry_run", False))
    if not repo:
        return _err("repo is required")
    if not c.is_valid_worktree_name(name):
        return _err("name %r is not one safe path segment [A-Za-z0-9._-] (max 64)" % name)
    git_mod = _load("git_safe")
    if git_mod is None:
        return _err("git_safe module could not be loaded")
    try:
        top = _toplevel(git_mod, repo)
        root = worktrees_root_for(top, args.get("worktrees_root"))
        path = os.path.join(root, name)
        listing = _git(git_mod, top, ["worktree", "list", "--porcelain"], timeout=30)
        if listing.returncode != 0:
            return _err("git worktree list failed: %s" % (listing.stderr or "").strip()[-200:])
        trees = parse_worktree_porcelain(listing.stdout or "")
        if trees and _norm(trees[0]["path"]) == _norm(path):
            return {"status": "refused", "error": "refusing to remove the main worktree %s" % path}
        match = next((t for t in trees[1:] if _norm(t["path"]) == _norm(path)), None)
        if match is None:
            return {"status": "refused", "path": path,
                    "error": "%s is not a registered worktree of %s" % (path, top)}
        branch = match.get("branch") or ""
        dirty = ""
        if os.path.isdir(path):
            st = _git(git_mod, path, ["status", "--porcelain"], timeout=60)
            dirty = (st.stdout or "").strip() if st.returncode == 0 else ""
        if dirty and not force:
            return {"status": "refused", "path": path, "dirty": dirty.splitlines()[:20],
                    "error": "worktree has uncommitted changes; commit them or pass force=true"}
        if delete_branch and branch in c.PROTECTED_BRANCHES:
            return {"status": "refused", "error": "refusing to delete protected branch %r" % branch}
        plan = [["worktree", "remove"] + (["--force"] if force else []) + [path], ["worktree", "prune"]]
        if delete_branch and branch:
            plan.append(["branch", "-D" if force else "-d", branch])
        if dry_run:
            return {"status": "dry_run", "repo": top, "path": path, "branch": branch,
                    "argv": [["git", "-C", top] + a for a in plan]}
        steps = []
        for a in plan:
            res = _git(git_mod, top, a)
            steps.append({"argv": a, "rc": res.returncode, "out": ((res.stdout or "") + (res.stderr or "")).strip()[-300:]})
            if res.returncode != 0:
                return _err("git %s failed: %s" % (" ".join(a[:2]), steps[-1]["out"]), path=path, steps=steps)
        return {"status": "ok", "repo": top, "path": path, "removed": not os.path.exists(path),
                "branch": branch, "branch_deleted": bool(delete_branch and branch), "steps": steps}
    except Exception as exc:
        return _err(str(exc))


# ---------------------------------------------------------------- 4. Intelligence ops

_MERMAID_STATUS_STYLE = {
    "done": "fill:#1f6f3f,stroke:#3fb950,color:#ffffff",
    "running": "fill:#1f4f8f,stroke:#58a6ff,color:#ffffff",
    "blocked": "fill:#8f1f1f,stroke:#f85149,color:#ffffff",
    "failed": "fill:#8f1f1f,stroke:#f85149,color:#ffffff",
    "review": "fill:#6f4f1f,stroke:#d29922,color:#ffffff",
    "pending": "fill:#3a3a3a,stroke:#8b949e,color:#ffffff",
}


def _mermaid_text(value: Any, limit: int = 60) -> str:
    text = " ".join(str(value if value is not None else "").split())
    if len(text) > limit:
        text = text[: limit - 1] + "\u2026"
    return (text.replace("&", "#amp;").replace('"', "#quot;").replace("<", "#lt;").replace(">", "#gt;")
            .replace("[", "#91;").replace("]", "#93;").replace("|", "#124;"))


def _status_class(status: Any) -> str:
    cls = re.sub(r"[^a-z0-9_]", "_", str(status or "pending").lower()) or "pending"
    return "st_" + cls


def graph_to_mermaid(graph: dict, direction: str = "TD") -> str:
    """Render a crew_graph.build_graph() graph (nodes + edges) as a Mermaid flowchart. Deterministic."""
    direction = direction if direction in _contracts().MERMAID_DIRECTIONS else "TD"
    nodes = list(graph.get("nodes") or [])
    ids: dict[str, str] = {}
    lines = ["flowchart %s" % direction]
    classes: dict[str, str] = {}
    for i, n in enumerate(nodes):
        mid = "n%d" % i
        ids[str(n.get("id"))] = mid
        kind = n.get("kind") or "node"
        label = n.get("title") or n.get("label") or n.get("id")
        status = str(n.get("status") or "pending")
        text = "%s: %s<br/>%s" % (_mermaid_text(kind, 20), _mermaid_text(label), _mermaid_text(status, 20))
        cls = _status_class(status)
        classes[cls] = status.lower()
        lines.append('    %s["%s"]:::%s' % (mid, text, cls))
    for e in graph.get("edges") or []:
        a, b = ids.get(str(e.get("from"))), ids.get(str(e.get("to")))
        if a and b:
            lines.append("    %s --> %s" % (a, b))
    for cls, status in sorted(classes.items()):
        style = _MERMAID_STATUS_STYLE.get(status, _MERMAID_STATUS_STYLE["pending"])
        lines.append("    classDef %s %s" % (cls, style))
    return "\n".join(lines)


def handle_crew_flow_graph(args: dict, **kwargs: Any) -> dict[str, Any]:
    """Handler for crew_flow_graph: crew_graph.build_graph -> Mermaid or slim JSON."""
    args = _args(args)
    card_ref = _card_id_arg(args) or "latest"
    direction = str(args.get("direction") or "TD").strip().upper()
    fmt = str(args.get("format") or "mermaid").strip().lower()
    if fmt not in ("mermaid", "json"):
        return _err("unknown format %r: use mermaid or json" % fmt)
    if direction not in _contracts().MERMAID_DIRECTIONS:
        return _err("unknown direction %r: use one of %s" % (direction, ", ".join(_contracts().MERMAID_DIRECTIONS)))
    graph_mod = _load("crew_graph")
    if graph_mod is None:
        return _err("crew_graph module could not be loaded")
    try:
        graph, error = graph_mod.build_graph(card_ref)
    except Exception as exc:
        return _err(str(exc), card_id=card_ref)
    if error or not graph:
        return _err(error or "no graph for %s" % card_ref, card_id=card_ref)
    out: dict[str, Any] = {
        "status": "ok",
        "card_id": graph.get("card_id"),
        "card_title": graph.get("card_title"),
        "card_status": graph.get("card_status"),
        "node_count": len(graph.get("nodes") or []),
        "edge_count": len(graph.get("edges") or []),
        "format": fmt,
    }
    if fmt == "mermaid":
        out["mermaid"] = graph_to_mermaid(graph, direction)
    else:
        out["nodes"] = [{k: n.get(k) for k in ("id", "kind", "label", "status", "role", "title")}
                        for n in graph.get("nodes") or []]
        out["edges"] = [{"from": e.get("from"), "to": e.get("to")} for e in graph.get("edges") or []]
    return out


def handle_crew_lesson_record(args: dict, **kwargs: Any) -> dict[str, Any]:
    """Handler for crew_lesson_record: crew_lessons.add / for_role."""
    args = _args(args)
    action = str(args.get("action") or "add").strip().lower()
    role = str(args.get("role") or "").strip().lower()
    lessons = _load("crew_lessons")
    if lessons is None:
        return _err("crew_lessons module could not be loaded")
    if action == "show":
        if role not in _contracts().LESSON_ROLES:
            return _err("unknown role %r (use: %s)" % (role, ", ".join(_contracts().LESSON_ROLES)))
        texts = lessons.for_role(role) if role != "all" else [e[2] for e in lessons.entries() if "all" in e[1]]
        return {"status": "ok", "role": role, "count": len(texts), "lessons": texts}
    if action != "add":
        return _err("unknown action %r: use add or show" % action)
    text = " ".join(str(args.get("text") or "").split())
    gaps = _contracts().lesson_gaps(role, text)
    if gaps:
        return _err("; ".join(gaps), gaps=list(gaps))
    try:
        result = lessons.add(role, text)
    except ValueError as exc:
        return {"status": "refused", "role": role, "error": str(exc)}
    except Exception as exc:
        return _err(str(exc))
    return {"status": "ok", "result": result, "role": role, "text": text, "path": lessons.path()}


CREW_OBSERVE_SCHEMA = {
    "name": "crew_observe",
    "description": (
        "Post-delivery check: re-run the owner-confirmed proof of delivered (done) crew cards through the bounded "
        "runner and record improved/regressed in observations.json and the card's events. A regression alerts the "
        "owner once and never reopens the card. Without card_id: every done card of the last window_days "
        "(or tagged `Observe: always`); `Observe: off` cards are skipped."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "card_id": {"type": "string", "description": "One delivered card to observe (default: all eligible)."},
            "window_days": {"type": "integer", "description": "Eligibility window in days (default 14)."},
            "timeout_s": {"type": "number", "description": "Seconds per proof run (default 60)."},
            "dry_run": {"type": "boolean", "description": "List eligible cards; run, record and send nothing."},
        },
    },
}


def handle_crew_observe(args: dict, **kwargs: Any) -> dict[str, Any]:
    """Handler for crew_observe: crew_observe.observe_delivered."""
    args = _args(args)
    card_id = _card_id_arg(args) or None
    if card_id and not _contracts().is_valid_card_id(card_id):
        return _err("not a card id: %r" % card_id)
    try:
        window = int(args.get("window_days") or 14)
        timeout = float(args.get("timeout_s") or 60.0)
    except (TypeError, ValueError):
        return _err("window_days and timeout_s must be numbers")
    if window < 1 or timeout <= 0:
        return _err("window_days must be >= 1 and timeout_s > 0")
    observe = _load("crew_observe")
    if observe is None:
        return _err("crew_observe module could not be loaded")
    try:
        res = observe.observe_delivered(db_path=args.get("db_path") or None, card_id=card_id, window_days=window,
                                        timeout_s=timeout, dry_run=bool(args.get("dry_run", False)))
    except Exception as exc:  # noqa: BLE001 - a tool answers, it never raises into the turn
        return _err("%s: %s" % (type(exc).__name__, exc))
    if res.get("error"):
        return _err(res["error"])
    return {"status": "ok", **res, "summary": observe.summary_lines(res)}


CREW_EXTENDED_TOOLS = [
    ("crew_stop_card", CREW_STOP_CARD_SCHEMA, handle_crew_stop_card),
    ("crew_review_handoff", CREW_REVIEW_HANDOFF_SCHEMA, handle_crew_review_handoff),
    ("crew_request_changes", CREW_REQUEST_CHANGES_SCHEMA, handle_crew_request_changes),
    ("crew_plan_split", CREW_PLAN_SPLIT_SCHEMA, handle_crew_plan_split),
    ("crew_worktree_create", CREW_WORKTREE_CREATE_SCHEMA, handle_crew_worktree_create),
    ("crew_worktree_cleanup", CREW_WORKTREE_CLEANUP_SCHEMA, handle_crew_worktree_cleanup),
    ("crew_flow_graph", CREW_FLOW_GRAPH_SCHEMA, handle_crew_flow_graph),
    ("crew_lesson_record", CREW_LESSON_RECORD_SCHEMA, handle_crew_lesson_record),
    ("crew_observe", CREW_OBSERVE_SCHEMA, handle_crew_observe),
]


def _string_response_adapter(fn: Any) -> Any:
    """Adapts tool handler output to guarantee Hermes str result contract."""
    import json
    def wrapped(*args: Any, **kwargs: Any) -> str:
        res = fn(*args, **kwargs)
        if isinstance(res, str):
            return res
        return json.dumps(res, indent=2, ensure_ascii=False)
    return wrapped


def _register(ctx: Any, tools: list) -> None:
    # Check if tool is already registered in global Hermes registry (e.g. from upstream crew_tools)
    try:
        from tools.registry import registry
        is_in_registry = lambda n: registry.get_entry(n) is not None
    except Exception:
        is_in_registry = lambda n: False

    existing = getattr(ctx, "tools", None)
    existing_names = {t["name"] if isinstance(t, dict) else getattr(t, "name", None) for t in existing} if isinstance(existing, list) else set()
    for name, schema, handler in tools:
        if name in existing_names or is_in_registry(name):
            continue
        try:
            ctx.register_tool(
                name=name,
                toolset="crew",
                schema=schema,
                handler=_string_response_adapter(handler),
                description=schema.get("description", ""),
            )
        except Exception:
            # Registration failure of an individual tool must not crash plugin init
            pass


def register_native_tools(ctx: Any) -> None:
    """Register the 5 core Crew native tools with Hermes plugin context."""
    _register(ctx, CREW_NATIVE_TOOLS)


def register_extended_tools(ctx: Any) -> None:
    """Register the extended Crew native tools: the 8 of OpenSpec crew-extended-tools plus crew_observe (stewardship-core-adoption)."""
    _register(ctx, CREW_EXTENDED_TOOLS)

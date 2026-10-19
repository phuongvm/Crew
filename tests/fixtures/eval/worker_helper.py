"""Worker eval test fixture helper."""

from __future__ import annotations

from typing import Any, Dict


def get_worker_helper_status() -> Dict[str, Any]:
    """Return fixture helper metadata status."""
    return {
        "status": "ready",
        "helper": "worker_helper",
        "enabled": True,
    }


def format_eval_summary(task_id: str, success: bool = True) -> str:
    """Format worker evaluation summary string."""
    state = "passed" if success else "failed"
    return f"Task {task_id} evaluation {state}."

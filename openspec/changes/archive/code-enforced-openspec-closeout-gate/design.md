# Technical Design: Crew Preload OpenSpec Close-Out Gate (`code-enforced-openspec-closeout-gate`)

## 1. Deep Module Seam (`__init__.py:1597-1616`)
- Add `_OPENSPEC_CHANGE_RX = re.compile(r"openspec/changes/(?:archive/)?([A-Za-z0-9._-]+)")` and helper `_report_openspec_change(card_id, user_message)` in `__init__.py`.
- In `crew_intake_preload`:
  - After checking `REJECTED_VERDICT_RX`, if the report is a completed (`Done`) report (`re.search(r"\*\*Done\*\*|^Done:\s", user_message, re.M)`) and `_report_openspec_change(report.group(1), user_message)` finds `<change-id>` (excluding `"archive"`), return `{"context": "[CREW OPENSPEC CLOSE-OUT GATE] ..."}` without calling `_open_window(session_id)`.
  - Ordinary `Done` reports without `openspec/changes/<change-id>` still return `None`.

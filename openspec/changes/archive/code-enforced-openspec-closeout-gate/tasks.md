# Tasks: Crew Preload OpenSpec Close-Out Gate (`code-enforced-openspec-closeout-gate`)

## Slice 1 — Preload Close-Out Gate Injection (`oss/crew`)

- [x] 1.1 In `O:/workspaces/.worktrees/wt-crew-inputs-and-propose-continuity`, update `__init__.py` (`crew_intake_preload`) to inject `[CREW OPENSPEC CLOSE-OUT GATE]` when a `Done` watcher report references `openspec/changes/<change-id>` (without opening the card-creation window), and add unit tests in `tests/test_crew_intake_create.py`.
  - **Proof**: `"O:/workspaces/oss/hermes-agent/.venv/Scripts/python.exe" -m pytest "O:/workspaces/.worktrees/wt-crew-inputs-and-propose-continuity/tests/test_crew_intake_create.py" -v`

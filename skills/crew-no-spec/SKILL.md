---
name: crew-no-spec
description: "Crew Fast-Track intake: /crew-no-spec <ask> - opens a direct Kanban card without OpenSpec artifacts."
version: 0.8.1
---

# /crew-no-spec - fast-track coordinator intake

Fast-track coordinator intake for operational tasks, runtime environment troubleshooting, configuration/script fixes, urgent hotfixes, or ad-hoc investigations.

**Bypasses OpenSpec workflow and artifact creation entirely.**

## Direct Single-Card Workflow

The coordinator turns the ask directly into a single Kanban contract card and assigns it to `@coder` without generating OpenSpec artifacts (`proposal.md`, `specs/`, `design.md`, `tasks.md`).

### Contract Fields (Section 2)
- **Role**: worker (code, config, infra, web) or content (reports, video, pages)
- **Assignee**: `@coder` (or `crew-worker`)
- **Skills**: `["crew-role-worker"]`
- **Goal**: One sentence outcome.
- **Artifact**: File, config, service, or test output produced.
- **Lands at**: Absolute path or repository.
- **Done when**: Observable end state.
- **Proof command**: One verifiable shell command returning exit code 0 on success.
- **Verify**: `proof` (command only) or `independent`.

### Open the Card and Launch Watcher (Section 4)

Show the drafted task in one short block, then call `kanban_create` in the same turn:

```python
kanban_create(
    title="<short title>",
    assignee="coder",
    skills=["crew-role-worker"],
    body="""Role: worker
Budget: 500000
Route: auto
Verify: proof
GOAL: <one sentence>
Artifact: <what>
Lands at: <where>
For: <who>
Constraints: <what must not change>
Done when: <observable end state>
proof command: <one shell command>
Proof mode: safe
"""
)
```

When `kanban_create` returns the card id, immediately start the watcher:
```python
terminal(background=True, notify_on_complete=True, command='python3 "$HERMES_HOME/plugins/crew/scripts/crew_card.py" watch --card <id>')
```

And reply with EXACTLY these lines:
```text
Card open: <id> - <title>
I'll notify you here when it's done or if it needs you.
```

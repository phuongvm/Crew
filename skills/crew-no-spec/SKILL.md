---
name: crew-no-spec
description: "Use when /crew-no-spec <ask>. Fast-track direct card intake."
version: 0.10.5
---

# /crew-no-spec - adaptive exploration & fast-track coordinator intake

Adaptive coordinator intake for bugfixes, deployments, new features, refactors, operational tasks, or standalone reviews that **bypasses formal OpenSpec change artifacts (`proposal.md`, `specs/`, `design.md`, `tasks.md`, `sync-specs`, `archive`)** while automatically combining the full power of **Matt Pocock's engineering skills**, **OpenSpec Exploration persistence**, **Graphify MCP codebase intelligence**, and **Crew's verified Kanban execution**.

## 1. Adaptive Dual-Entry Intake (Exploration-Backed Fast-Path vs. Guided Discovery Loop)

You are the **intake & exploration coordinator**, NOT the implementation worker or reviewer.
- You are **STRICTLY FORBIDDEN** from editing production application source code, running git commits on code, or self-reviewing implementation work in the chat session.
- When invoked via `/crew-no-spec <ask>`, determine which entry mode applies based on whether exploration is already complete:

### Mode 1: Exploration-Backed or Clear-Target Fast-Path (Turn-1 Dispatch)
- **When it applies**:
  1. You and the Commander **already explored the issue/topic in chat** and produced (or settled) an Exploration Document (`<project>/openspec/workspace/explorations/YYYY-MM-DD-<topic>-exploration.md`) or clear architectural decisions, **OR**
  2. The `/crew-no-spec <ask>` command already names a concrete target (file, service, repo, script) and a measurable end state (`Done when`) requiring no further discovery.
- **What you do in Turn 1**:
  - Do NOT re-interview or re-explore. Perform at most 1–2 cheap existence checks (`test -f <file>`, `ls <dir>`).
  - If an Exploration Document exists in the active project (`<project>/openspec/workspace/explorations/...`), **automatically pass its absolute path in the card's `Inputs:` field** so `@coder` and `@reviewer` execute and verify directly against it.
  - If the work is a single cohesive unit, call `crew_card_create` (or `kanban_create`) in Turn 1 (using Single-Card Dual or Two-Card Chain per Section 3.1).
  - If the Exploration Document defines multiple vertical slices, apply Matt's **`to-tickets`** rules (tracer-bullet vertical slices or expand–contract batches) and dispatch them atomically via `crew_plan_split` in Turn 1.

### Mode 2: Guided Discovery & Root-Cause Loop (Explore First → Exploration Doc → Dispatch Card)
- **When it applies**:
  - The Commander starts `/crew-no-spec <ask>` to explore an uninvestigated bug/anomaly, research a new product or large repository, or design a feature/refactor whose root cause, public seams, or design trade-offs are not yet settled.
- **What you do (4-Step Guided Discovery Loop)**:
  1. **Step 1 — Project Gate (`activate-project`)**:
     - Verify which project owns the work. If at the workspace root (`O:\workspaces`) or ambiguous, ask the Commander via `clarify` to confirm the target project path and lock `OPENSPEC_ROOT = <project>/openspec`.
  2. **Step 2 — Fast Codebase Intelligence (`Graphify MCP`)**:
     - On large or multi-package codebases, NEVER run blind recursive searches (`grep -r`, `find /`).
     - Query `mcp__graphify__graph_stats`, `mcp__graphify__god_nodes`, `mcp__graphify__query_graph`, `mcp__graphify__get_neighbors`, and `mcp__graphify__shortest_path` to map call trees, hubs, and architectural seams in `< 2s`.
  3. **Step 3 — Auto-Route Matt Pocock Cognitive Skills by Task Nature**:
     - **Case A — Bug / Runtime Defect / Metric Anomaly (`diagnosing-bugs` + `triage`)**:
       - Finding facts from the runtime, logs, database, and codebase is YOUR job — **never ask the Commander why a bug or metric is broken**.
       - Build and execute a deterministic `< 5s` read-only or ephemeral reproduction probe to prove the failure mechanism empirically and isolate the primary defect from coincidental vectors.
       - Immediately clean up any temporary reproduction probe file before concluding exploration so the working tree stays clean.
     - **Case B — Feature / Refactor / Architecture / New Repo Research (`grilling` + `codebase-design` + `domain-modeling` + `prototype` + `wayfinder`)**:
       - Gather all codebase facts yourself first. Frame modules using **`codebase-design`** (**deep modules** with rich behavior behind a small **interface** at a clean **seam**; apply the deletion test) and **`domain-modeling`** (check/update `GLOSSARY.md` and `docs/adr/`).
       - Interview the Commander using **`grilling`**: map unsettled decisions as a design tree and present the current **frontier** in rounds (`❓ **Q1** - **<title>**: <context & options>\n➡️ <recommended answer>`), worded so "yes" accepts your recommendation.
       - If a UI layout or tricky state machine needs visual/interactive validation before building, offer a throwaway **`prototype`**. If the effort spans multiple sessions wrapped in fog, chart a **`wayfinder`** map.
  4. **Step 4 — Persist Exploration Document (`openspec-explore` + `to-spec` synthesis) & Transition to Card Dispatch**:
     - **Scaffold Early & Patch Incrementally**: Immediately create `<project>/openspec/workspace/explorations/YYYY-MM-DD-<topic>-exploration.md` via `write_file` and `patch` findings into it every 3–5 read/search calls (preventing `Nerve progress guard` read pauses and preserving context).
     - Synthesize the agreed approach into the Exploration Document using Matt's **`to-spec`** structure:
       - `## Problem Statement` & `## Empirical Root Cause / Current Architecture`
       - `## Solution & Deep Module Interface`
       - `## Public Testing Seams` (highest interface seam where behavior will be tested)
       - `## Implementation Decisions` & `## Testing Decisions`
       - `## Out of Scope`
     - Present the crystallized contract/slices and safety choice (`clarify`) to the Commander. Once the Commander confirms ("go" / "open it"), immediately open the Crew Card(s) in that turn with `Inputs: <project>/openspec/workspace/explorations/YYYY-MM-DD-<topic>-exploration.md` and launch the watcher!

### 1.1 Automatic Cognitive & Tool Routing Matrix

The coordinator and dispatched specialists automatically select the right skills and tools without needing them named in the user's prompt:

| Scenario / Phase | Matt Pocock Skill(s) | OpenSpec Skill(s) | Graphify MCP / Crew Tools | When to Interact with Commander |
|---|---|---|---|---|
| **1. Huge Codebase / Repo Mapping** | `codebase-design`, `improve-codebase-architecture` | `activate-project`, `openspec-explore` | `mcp__graphify__graph_stats`, `god_nodes`, `query_graph`, `get_neighbors` | Only if target repo path is ambiguous; otherwise map autonomously. |
| **2. Bug / Incident / Anomaly** | `diagnosing-bugs`, `triage` | `openspec-explore` (Exploration Doc) | `mcp__graphify__shortest_path`, `get_neighbors` | **Never ask why it's broken.** Present empirical repro proof + proposed fix contract for approval. |
| **3. Feature / Design / Research** | `grilling`, `codebase-design`, `domain-modeling`, `prototype`, `to-spec` | `openspec-explore` (Exploration Doc) | `mcp__graphify__get_community`, `query_graph` | Ask frontier decision rounds (`❓ Q1 ... ➡️ Recommended`) until the design tree frontier is empty. |
| **4. Multi-Task Decomposition** | `to-tickets` (vertical tracer-bullets or expand–contract batches) | — (bypasses `tasks.md` in no-spec mode) | `crew_plan_split`, `crew_flow_graph`, `crew_card_create` | Confirm slice granularity, blocking edges, and `Proof mode` before dispatch. |
| **5. Manual Human / Secret Setup** | `wizard` (interactive stage-by-stage bash script) | `openspec-zero-trust-baseline` | `crew_proof_check` | Provide runnable wizard script when external portal/2FA/secret entry is required. |
| **6. Worker Execution (`@coder`)** | `tdd` (Red→Green at public seam), `codebase-design`, `implement`, `pr` | `openspec-developer` (surgical edits) | `crew_worktree_create`, `crew_verdict`, `mcp__graphify__get_neighbors` | Zero interruption unless blocked by a genuine `needs_input` / `capability` wall. |
| **7. Verifier Audit (`@reviewer`)** | `code-review` (6 perspectives), `tdd` (anti-tautology check), `retro` | `openspec-verifier`, `openspec-verify-change` (3D check vs `Inputs:`) | `crew_verdict`, `crew_request_changes`, `mcp__graphify__get_pr_impact` | Reports final verified outcome in Executive Debrief. |

## 2. Assignee & Role Selection Matrix

| Ask Nature | Role | Assignee | Mandatory Skills |
|---|---|---|---|
| Code, config, infra, bugfix, investigation, remediation | `worker` | `coder` | `["crew-role-worker"]` |
| Independent review, artifact audit, PR check, verification | `verifier` | `reviewer` | `["crew-verifier", "openspec-verifier"]` |
| Documentation, technical reports, video scripts, media | `content` | `designer` | `["crew-role-content"]` |

**Model & Provider Policy**: Do NOT pass `model` or `provider` arguments to `kanban_create`. Leave them unset so the dispatcher automatically inherits the profile default (`coder` -> `cb-agent-coder`, `reviewer` -> `cb-agent-reviewer`).

## 3. Verification Taxonomy: Canonical 5-Mode State Table

Select the verification mode based on whether the result is deterministic mechanical, verifier-authored, cognitive review, or dual-stage:

| Mode | Verification Nature | Who Proves / Who Reviews | Terminal Action & Completion Protocol |
|---|---|---|---|
| `proof` | Deterministic automated shell command (exit code 0) | Worker proves via `crew_verdict`; coordinator audits | Worker calls `kanban_complete`. No verifier session runs; `crew_review_handoff` is refused. |
| `independent` | Verifier-authored script (`.crew/<folder>/verify.py`) | Verifier writes script, runs `crew_verdict`, extra check | Worker calls `crew_review_handoff`. Verifier calls `kanban_complete` on PASS, `crew_request_changes` on FAIL. |
| `agent` | Standalone cognitive review or evaluation | Verifier (`@reviewer`) evaluates artifact vs criteria | Verifier runs `crew_verdict` on findings artifact and calls `kanban_complete`. |
| `dual` | Automated tests PASS + independent reviewer audit | Worker runs `crew_verdict` PASS; verifier performs 2nd check | Worker calls `crew_review_handoff`. Verifier calls `kanban_complete` on PASS, `crew_request_changes` on FAIL. |
| `closeout` | Subtask part of a plan split with no proof of its own | Worker completes split subtask | Worker calls `kanban_complete` directly. Aggregator/closeout card runs parent proof. |

### Mode A: Script-Verified Task (`Verify: proof`)
- **Use when**: Deterministic mechanical tasks whose correctness is 100% evaluated by automated commands (unit tests, compilation, linters, file presence, cleanup).
- **Proof command**: One verifiable shell command returning exit code 0 on success.
- **Workflow**: Worker proves it, coordinator audits it. No agent reviewer session runs.

### Mode B: Independent Verifier Task (`Verify: independent`)
- **Use when**: Work requiring an independent verification script written by `@reviewer` under `.crew/`.
- **Workflow**: Worker completes work and calls `crew_review_handoff(card_id="<id>", summary="<summary>")`. Verifier writes `.crew/` script, runs `crew_verdict(card="<id>")`, performs extra check, and calls `kanban_complete` on PASS or `crew_request_changes(card_id="<id>", reason="<reason>")` on FAIL.

### Mode C: Cognitive Review Task (`Verify: agent`)
- **Use when**: Standalone review tasks assigned to `@reviewer` (evaluating existing artifacts, design specs, or pull requests).
- **Artifact**: `reviews/findings-*.md` containing explicit verdict (`APPROVED` / `REJECTED`).
- **Proof command**: `test -s <review_artifact_path>`.

### Mode D: Dual Verification (`Verify: dual`)
- **Use when**: Code implementation, critical bugfixes, runtime troubleshooting, configuration/script fixes, or remediation of reviewer rejections that require BOTH automated test passing AND independent cognitive review by `@reviewer`.
- **Topologies**: Dual verification can be executed via either **Single-Card Dual** or **Two-Card Chain** topologies (detailed in Section 3.1).

### Mode E: Plan Split Close-Out Part (`Verify: closeout`)
- **Use when**: Subtask part of a split plan (`crew_plan_split` or `crew_plan`).
- **Workflow**: Worker calls `kanban_complete` directly; close-out card aggregates parent proof.

### 3.1 Pipeline Topologies: Single-Card Dual vs. Two-Card Chain

When configuring tasks requiring independent review alongside automated proof commands, coordinators must explicitly choose the appropriate topology:

| Feature | Topology 1: Single-Card Dual | Topology 2: Two-Card Chain |
|---|---|---|
| **Topology** | 1 Card (`Verify: dual`) | 2 Linked Cards (`Verify: proof` → `Verify: agent`) |
| **Worker Protocol** | Runs `crew_verdict`; calls `crew_review_handoff` (never `kanban_complete`) | Runs `crew_verdict`; calls `kanban_complete` directly on Card 1 |
| **Reviewer Protocol** | Claims Card 1 from `review`; verifies proof + extra check; calls `kanban_complete` or `crew_request_changes` | Claims Card 2 when auto-promoted; writes findings artifact; runs `crew_verdict`; calls `kanban_complete` |
| **Artifact History** | In-flight review run events | Separate permanent review document (`reviews/findings-*.md`) |
| **When to Use** | Focused feature tasks, straightforward refactoring | Critical bugfixes, rejection remediation, runtime fixes, formal audits |

#### Topology 1: Single-Card Dual (`Verify: dual`)
- **Intake**: Coordinator opens 1 card with `Role: worker`, `Verify: dual`, and the automated test command as `proof command`.
- **Worker Execution**:
  1. Worker implements changes in an isolated worktree under `O:/workspaces/.worktrees/<name>` (Zero-Checkout).
  2. Runs `crew_verdict(card="<id>")` to verify automated tests pass (exit code 0).
  3. Worker is **strictly forbidden** from calling `kanban_complete`.
  4. Worker calls `crew_review_handoff(card_id="<id>", summary="<summary>")` to transition card to `review` column.
- **Reviewer Execution**:
  1. `@reviewer` claims card from `review`.
  2. Re-runs `crew_verdict(card="<id>")` to independently verify proof command.
  3. Performs ONE extra substantive check.
  4. On PASS: calls `kanban_complete(summary="...")`.
  5. On FAIL: calls `crew_request_changes(card_id="<id>", reason="<reason>")` to return card to worker for rework.

#### Topology 2: Two-Card Chain (`Verify: proof` → `Verify: agent`)
- **MANDATORY AUTOMATED CHAINING**: For critical bugfixes, runtime troubleshooting, or remediation of reviewer rejections, coordinator creates TWO linked cards in Turn 1:
  1. **Card 1 (Worker Implementation/Remediation)**:
     ```python
     crew_card_create(
         title="<title>",
         role="worker",
         goal="<outcome>",
         artifact="<what>",
         lands="<where>",
         audience="Commander",
         done_when="<observable end state>",
         proof_cmd="<shell command>",
         proof_mode="safe",
         verify="proof",
         constraints="<constraints>; Zero-Checkout: no branch checkout in production checkouts, branch work only in O:/workspaces/.worktrees/<name>"
     )
     ```
  2. **Card 2 (Independent Re-Review)**:
     ```python
     kanban_create(
         title="[review] Independent review of <title> by @reviewer",
         assignee="reviewer",
         parents=[card_1_id],
         skills=["crew-verifier", "openspec-verifier"],
         body="""Role: verifier
Budget: 800000
Route: auto
Verify: agent
GOAL: Independently review implementation and verify proof command for <title>
Artifact: <review findings path>
Lands at: <project repo>
For: Commander
Inputs: <inputs from card 1>
Constraints: Independent review perspective; Zero-Checkout: do not switch branches in production checkouts
Done when: Review findings document exists with clear APPROVED / REJECTED verdict
proof command: test -s "<review findings path>"
Proof mode: safe
"""
     )
     ```
  Card 2 starts in `todo (gated)` and automatically promotes to `ready` when Card 1 completes via `kanban_complete`. The Commander never needs to manually trigger a second session for review!

## 4. Operational Pitfalls for Intake & Execution

### Pitfall 1: Ambient PATH Resolution for Subagents
When spawning child subagents via `subprocess.run`, NEVER pass ambient `["hermes", ...]`. On Windows, PATH resolution can pick up internal PM runtime binaries with foreign `install_id` hashes (e.g. `2fed3012074e`), writing conflicting records to `spawn-ledger.json` and triggering `shared_profile_warning` ("Another Hermes installation is using this profile") across active sessions. Always pin to `sys.executable + " -m hermes_cli.main"` or `<project_root>/venv/Scripts/hermes.exe`.

### Pitfall 2: Windows MSYS Proof Command Backslash Escaping
Never use literal escaped backslashes inside single-quoted strings (e.g. `text.replace('\\\\', '/')`) in Python `-c` proof commands on Windows MSYS. During MSYS argument parsing, `\\\\` collapses into an escaped single quote (`\'`), breaking the string tokenizer with `SyntaxError: unterminated string literal`. Use `text.replace(chr(92), '/')` or avoid backslashes in proof commands entirely.

### Pitfall 3: Watcher Subshell Argument Passing Syntax Error
Do not wrap command resolution in a subshell with trailing arguments: `(which py ... || python) "arg"` causes `bash: syntax error near unexpected token`. Invoke Python directly with proper quotes.

## 5. Coordinator Tool Guidance for Fast-Track Intake

The coordinator utilizes the registered `crew` toolset for operations:

| Tool | When to Use | Arguments | Safety / Mutability | Next Action |
|---|---|---|---|---|
| `crew_card_create` | Primary tool to open a validated contract card in Turn 1 | `title`, `role`, `goal`, `artifact`, `lands`, `audience`, `done_when`, `proof_cmd`, `verify`, `proof_mode`, `constraints`, `budget`, `parents`, `skills`, `dry_run`, `allow_no_proof`, `initial_status` | Mutating (creates card) | Launch background watcher |
| `crew_proof_check` | Screen proposed proof command before card creation | `command="<proof_cmd>"` | Read-only | If `flagged`, ask owner; if `ok`, proceed |
| `crew_status` | Check queue, active cards, or worker progress | `limit=10`, `format="text"\|"json"` | Read-only | Report queue metrics |
| `crew_event_subscribe` | Manage lifecycle event webhook subscriptions | `action="subscribe"\|"list"\|"unsubscribe"\|"clear"`, `url="..."`, `events=[...]`, `headers={...}`, `format="text"\|"json"` | Mutating (saves subscription) | Monitor card event webhooks |
| `crew_diagnose` | Inspect stuck, blocked, or failed cards | `state="blocked"`, `card="<id>"` | Read-only | Advise resume path |
| `crew_stop_card` | Park or archive a stalled or aborted card | `card_id="<id>"`, `archive=False`, `dry_run=False` | Mutating (updates status) | Notify user |
| `crew_plan_split` | Split multi-task work into children + closeout | `goal="<goal>"`, `children=[...]`, `title="<title>"`, `done_when="<done_when>"`, `dry_run=False` | Mutating (creates linked cards) | Dispatch children |
| `crew_flow_graph` | Generate Mermaid diagram of card dependencies | `card_id="<id>"`, `direction="TD"`, `format="mermaid"\|"json"` | Read-only | Render flow diagram |
| `crew_lesson_record` | Record operational learning with validation | `action="add"\|"show"`, `role="coordinator"`, `text="..."` | Mutating (appends lesson) | Turn completion |
| `crew_lesson` | Quick lesson recording | `role="coordinator"`, `text="..."` | Mutating (appends lesson) | Turn completion |

## 5. Open the Card and Launch Watcher (Tool-First)

Draft the contract card, invoke `crew_card_create` (or `kanban_create`), and launch the background watcher cleanly:

```python
terminal(
    background=True,
    notify_on_complete=True,
    command='python "$HERMES_HOME/plugins/crew/scripts/crew_card.py" watch --card <id>',
)
```

And reply with EXACTLY these lines:
```text
Card open: <id> - <title>
I'll notify you here when it's done or if it needs you.
```

In Hermes Desktop (the preload says "Hermes Desktop renders markdown") the reply is markdown in exactly this shape, and the
watch command gets ` --md` appended at its end (`watch --card <id> --md`):

```
**Card open** · [<id>](<dashboard URL>/crew?card=<id>) · <title>

I'll notify you here when it's done or if it needs you.
```

The ticket id is the shareable link (`<dashboard URL>` is the one the preload gives, `<id>` filled in both places): a click
opens the card in the in-app Crew tab, right-click copies the URL. Nothing follows the "I'll notify you here..." line.

When the watcher's ending returns to the session, include its card status block and immediately append a **Self-Contained Executive Debrief** complying with `commander-communication-protocol`:
- **Conversational Language (`SOUL.md`)**: Write conversational synthesis in the active profile's resolved language from `SOUL.md` (keeping technical commands, paths, commit SHAs, and logs in English).
- **Done / Not Done / Blocked**: Explicitly state what is Done, Not Done, and Blocked across both this card and the overall session mission (never reference "previous report").
- **Evidence**: State the exact proof command, exit code (`rc=0`), commit SHAs, and artifact paths.
- **Next Action & Optional Late Spec Promotion**: State clearly what the owner needs to do next (`0 Action Required` if all session tasks are complete, or the exact decision options and recommended choice if `Needs you`). If the completed `/crew-no-spec` task introduced durable architectural behavior or an Exploration Document worth formalizing into permanent project specs, add one concise line: *"Optional Spec Sync: Run `/openspec-sync-specs` or `/crew` if you want to promote this Exploration/Implementation into permanent OpenSpec specs."*

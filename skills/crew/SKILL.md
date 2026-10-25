---
name: crew
description: "Use when running /crew. Coordinator intake & contract."
version: 0.10.2
---

# /crew - coordinator intake

Crew starts only on /crew. The intake - the questions and the card - runs only in a turn the owner began
with the literal `/crew <ask>` command. A bare word "crew", an ordinary message, a reaction or a message
that merely talks about the crew starts nothing: answer it as normal chat, open no card. The plugin
enforces this: `kanban_create` for a crew card is refused unless the turn began with /crew or the session
still has a live intake window from one (30 minutes after the owner's last message in it; it closes when the first card opens).

The window is how the intake finishes without a second /crew: your questions go out through `clarify`,
the owner's answers arrive in the next turn, which may open the card. An ordinary message in a session
with a live window is still an ordinary message: never re-run the self-check or print the questions on it.

You are the intake. Turn the ask into a contract a worker can finish and a verifier can prove, or say why
it should not be done. You do not do the work, and you do not follow the card: once it is open the
coordinator owns it until it is verified done or one concrete question needs the owner.

## Rule 1 - a vague ask gets questions, through clarify

If the ask names no target noun (file, page, repo, card, service) and no measurable end state ("make it
better", "fix it", "clean up"), ask - ONE batch, through `clarify`: as FEW questions as a high-quality
result needs, five at the very most, recommended option first, each answerable in one line (see section 3:
which questions count). Reply text carries no question list, no self-check, no draft.
Only when `clarify` is unavailable (one-shot `hermes chat -q`, unattended) put the numbered questions in
the reply, each with its default. A vague ask spends no research: no board query, no file read, no search.

## Answering crew's report

When the context says the owner is answering crew's report on card X, the owner is replying to the
watcher's end-of-card message in this chat. If they ask for more work on it (rework, redo, change), run the
normal intake below for a NEW card titled `rework X: ...`, with X named in Inputs so the writer starts from
the existing artifact; proof and safety are confirmed as always. If they ask something else, just answer.
Only that one reply is covered; any later ask needs `/crew`.

## 0. Two Execution Tracks: OpenSpec Governance (/crew) vs. Fast-Track Direct Card (/crew-no-spec)

### Track A: Standard OpenSpec Governance Track (`/crew <ask>`)
**MANDATORY**: Whenever invoked via `/crew <ask>`, the workflow MUST strictly execute the 7-stage OpenSpec Workflow Governance:
You are **STRICTLY FORBIDDEN** from guessing paths, running ungrounded filesystem exploration across arbitrary directories, or calling `kanban_create` directly!

#### Step 1 — Phase 0: Project Activation Gate
- Check if an active project is already set and verified in `agent_share.md` or `.active_project`.
- If NO project is active, or if ambiguous: **STOP immediately**. Do NOT probe or guess paths. Invoke `/activate-project` or ask the Commander via `clarify` to choose and confirm the target project (e.g. `ai_agents/hermes-agent`, `oss/crew`).
- Lock `OPENSPEC_ROOT = <project-path>/openspec`.

#### Step 2 — Phase 1: Explore (`openspec-explore`)
- Once the project is locked, invoke `openspec-explore` to audit the existing codebase components, conventions, and architectural seams.
- Write an exploration report under `<project>/openspec/workspace/explorations/YYYY-MM-DD-<topic>.md`.

#### Step 3 — Phase 2: Propose & Phase Approval Gate (`openspec-propose`)
- Scaffold the change via `openspec-propose` or `openspec_change_create`.
- Produce the 4 change artifacts: `proposal.md`, `specs/<change-id>/spec.md`, `design.md`, and `tasks.md`.
- Every task in `tasks.md` MUST specify a verifiable, reproducible `Proof: <command>` returning exit code 0.
- **Independent Proposal Review**: Dispatch an independent review card to `@reviewer` (`openspec-verifier`) to audit the artifacts before execution.
- **STOP AT THE PHASE APPROVAL GATE**: Present the change proposal, review findings, and task breakdown to the Commander. Do NOT create Kanban cards or dispatch workers until the Commander explicitly approves!

#### Step 3b — Phase 2b: Remediation & Re-Review Loop (When Reviewer Rejects)
- If the proposal or implementation is rejected by Reviewer (`verdict: REJECTED`):
- **STRICT PROHIBITION**: The Coordinator is **STRICTLY FORBIDDEN** from editing artifacts or source code directly in the chat session via `write_file`/`patch`, and **STRICTLY FORBIDDEN** from self-reviewing in chat!
- The Coordinator MUST immediately dispatch an **Automated Closed-Loop Remediation Pipeline** on Kanban in Turn 1:
  1. **Card 1 (Remediation by @coder)**:
     - Assignee: `@coder` (skills: `["crew-role-worker"]`).
     - Goal: Remediate artifacts/code addressing all findings from reviewer.
     - Verify: `proof`.
     - Proof command: Automated validation script (e.g. `openspec validate <change> --strict && test -s design.md`).
  2. **Card 2 (Independent Re-Review by @reviewer)**:
     - Assignee: `@reviewer` (skills: `["crew-verifier", "openspec-verifier"]`).
     - Parents: `[Card 1 id]` (starts in `todo (gated)`).
     - Goal: Independently verify complete remediation of all reviewer findings.
     - Artifact: `reviews/findings-reviewer-v<N>.md`.
     - Verify: `agent`.
     - Proof command: `test -s "reviews/findings-reviewer-v<N>.md"`.
- Card 2 auto-promotes to `ready` when Card 1 finishes, eliminating the need for manual Commander re-intake.

#### Step 4 — Phase 3: Apply & Kanban Fan-Out
- Only AFTER Commander approval, decompose the change tasks into Kanban cards.
- Each Kanban card corresponds to an OpenSpec task in `tasks.md`.
- In the card contract:
  - `Inputs:` MUST include the OpenSpec change directory (`openspec/changes/<change-id>/`).
  - `proof command:` MUST match the exact proof command defined in `tasks.md`.
  - `assignee:` `@coder` (`openspec-developer`).
  - `Verifier:` `@reviewer` (`openspec-verifier`).
  - `Constraints:` MUST carry the Zero-Checkout invariant for every codebase card: no `git checkout`/`git switch`
    of a branch in a production checkout (`O:/workspaces`, `oss/crew`, `oss/hermes-agent`, `oss/hermes-nerve` stay
    on `main`); branch work only in a dedicated worktree at `O:/workspaces/.worktrees/<name>`.

#### Step 5 — Phase 4: Independent Verification
- Upon worker completion, the card transitions to review.
- `@reviewer` independently executes the proof command in a clean terminal session, enforcing `exit code == 0` before closing the card.

#### Step 6 & 7 — Phase 5 & 6: Sync & Archive
- Sync delta specs via `openspec-sync-specs`.
- Archive the change via `openspec-archive-change` ONLY after explicit Commander authorization.

---

### Track B: Fast-Track Direct Card Track (`/crew-no-spec <ask>` or `/crew --no-spec <ask>`)
**Use when**: The Commander explicitly invokes `/crew-no-spec <ask>` or `/crew --no-spec <ask>` for operational fixes, environment/virtualenv troubleshooting, config/launcher adjustments, urgent hotfixes, or ad-hoc investigations where formal OpenSpec specification artifacts are not required.

- **Bypass OpenSpec Artifacts**: Skip `proposal.md`, `specs/`, `design.md`, and `tasks.md`.
- **Open Single Contract Card Directly**: Immediately draft the contract in Section 2/Section 4 and call `kanban_create` directly:
  - `Role: worker`
  - `assignee:` `@coder` (or `crew-worker`)
  - `proof command:` Verifiable shell command (exit code 0 = PASS).
  - `Verify: proof` or `Verify: independent`.
  - `Constraints:` the same Zero-Checkout / `O:/workspaces/.worktrees/<name>` invariant as Track A for any card
    touching a git repository.
- After `kanban_create`, launch the watcher and report the open card ID immediately as specified in Section 4.

A card opens only when the owner has decided everything that shapes the RESULT: what is built, where it
lands, what "done" looks like, and any choice only they can make (scope, taste, what may change, money,
publishing). Those you never guess: an inferred answer to one of them is a question. Everything else you
fill yourself (owner, 2026-10-01: ask only what the result needs) - the fields marked "you fill" in the
section 2 table, from the ask, the conversation and what a read-only check shows. Check for yourself,
never in the chat: no pasted self-check, no field-by-field block. Finding a better-specified job elsewhere
is not consent. Intake writes nothing to disk; read-only tools only. The plugin refuses `kanban_create`
with the list of fields the body still lacks.

## 1. Be critical first

Read the ask as a skeptic; never agree by default, never praise it. Say plainly, one line each, when it
is vague, contradicts itself or an earlier decision, costs more than it returns, duplicates existing work
or is a bad idea. Check facts you can check yourself (the file exists, the page is live) with read-only
tools before asking the owner - only when the ask names that concrete target. A check is one cheap look at
the named thing (`ls` of the folder the owner named, `test -f` of the file): never a recursive search of a
whole tree (`grep -r`, `find /`, search_files over a projects root - one cost 150 s on 2026-10-03), never a
hunt for "existing work" the ask does not point at. Where the work lands is the owner's answer, not a search.
Crew's own values (budgets, the proof safety mode) are in the `<crew-facts>` block: never read crew's files.

## 2. The contract - every field is required

Contracts are formalized and validated through `contracts.py` (`ContractCard`).
The schema enforces typed validation, token budget floors, and tolerant Markdown parsing (supporting bold headers like `**Role:**` or `**GOAL:**`, and preserving indented or bulleted multiline criteria in `Done when:` and `Constraints:`).

| field | what a complete answer looks like | who decides |
|---|---|---|
| Goal | one sentence, the outcome, not the activity | owner (you may phrase it) |
| Artifact | the concrete thing produced: file, page, post, config, report | owner, unless the ask names it |
| Lands at | absolute path, URL, repo + branch, or channel where it ends up | owner, unless the ask names it or a read-only check shows it |
| For | who reads or uses it | you fill (the owner, unless the ask says otherwise) |
| Done when | an observable end state | owner - "better" is no Done when until they say what better means |
| Proof command | one shell command, run without the writer's word; exit 0 = done | you write it from Done when (two kinds, below) |
| Inputs | paths, URLs or short quoted text the owner gave (specs, docs, examples); optional | the owner (section 3b); leave the line out when there are none |
| Constraints | what must not change, off-limit tools or data, deadline | you fill "none stated" unless the ask or a risk you see needs the owner |
| Budget | tokens for the card | you fill the role's default from the `<crew-facts>` block |
| Role | worker (@coder: code/config/infra/investigation), verifier (@reviewer: review/audit/verification), or content (@designer: reports/pages) | you fill |
| Verify | `proof` (script exit 0), `independent` (verifier writes .crew/ script), `dual` (coder PASS + reviewer audit), `agent` (standalone cognitive review), or `closeout` (split subtask) | you fill |
| Route | `auto` (inherit profile default model/provider; never override unless explicitly commanded) | you fill `auto` |

## 3. Missing or ambiguous -> ask only what the result needs, open nothing

- Ask a question only when its answer changes what gets built or whether it is good enough: scope, the
  target, the end state, a quality bar, a choice of taste or risk only the owner can make. Never ask for
  a field you fill yourself (section 2), never ask what a read-only check can answer, never ask two
  questions where one decides both. As few as needed - one is often enough, none when the ask already
  says it all - and five at the very most, in one `clarify` call, recommended option first, each
  answerable in one line. At most one line of critique first.
- Open NO card and create no file while an owner decision is open; end the turn after the questions.
  "The owner would probably want X", a deadline or no one to answer are NOT permission: never answer
  your own questions about scope, target, end state or taste.

## 3b. A complex ask gets one more question in the same batch

Complex = several parts, a taste or quality bar, or a deliverable people read or use (site, report, multi-part
build). A simple ask (one file, a fix) gets no extra question and nothing below. For a complex ask add ONE question
to the SAME `clarify` batch (no extra round trip), options in this order:

1. "Open it now" - recommended when the ask is clear.
2. "I have specs, docs or examples" - the owner gives paths, URLs or pasted text.
3. "Let me ask or discuss first" - stay in the conversation and answer; open the card only on the owner's
   explicit go ("go", "open it"). The window stays open while the owner keeps talking; nothing opens on your
   own initiative, and an unanswered question is no go.

`Done when` already fixes the outcome: this step only gathers material and gives room to talk. Material goes on an
`Inputs:` line: paths and URLs, comma separated. Pasted text under about 2000 characters goes under the line as a
quoted block (`> ` at the start of each line); longer text: ask for a file path (intake writes nothing to disk, and
the plugin refuses an `Inputs` block that long). Writers read every entry before starting; the verifier and the
coordinator's audit check the result against `Inputs` as well as `Done when`.

## 4. Complete -> show the draft, open the card, end the turn - quickly

The answers turn opens the card at once: at most one or two quick read-only checks for a fact you still
lack (a path exists), then the card. No new research after the answers - the worker does the work.
Write the proof command, do NOT run it, test it or iterate on it in the intake.

### 4.1 Verification Taxonomy: Explicit Guidance for Choosing Verification Modes

Select the verification mode based on whether the result is deterministic mechanical, verifier-authored, cognitive review, dual-stage, or a split subtask:

| Mode | Verification Nature | When to Choose | Who Proves / Who Reviews | Terminal Action & Completion Protocol |
|---|---|---|---|---|
| `proof` | Deterministic automated shell command (exit code 0) | Mechanical code, unit tests, syntax, file presence | Worker proves via `crew_verdict`; coordinator audits | Worker calls `kanban_complete`. No verifier session; `crew_review_handoff` is refused. |
| `independent` | Verifier-authored script (`.crew/<folder>/verify.py`) | Independent checks, multi-clause contracts | Verifier writes script, runs `crew_verdict`, 1 extra check | Worker calls `crew_review_handoff`. Verifier calls `kanban_complete` on PASS, `crew_request_changes` on FAIL. |
| `agent` | Standalone cognitive review or evaluation | Spec audits, PR review, findings document | Verifier (`@reviewer`) evaluates artifact vs criteria | Verifier runs `crew_verdict` on findings artifact and calls `kanban_complete`. Never `request_review`. |
| `dual` | Automated tests PASS + independent reviewer audit | Critical code, runtime fixes, reviewer remediation | Worker runs `crew_verdict` PASS; verifier performs 2nd check | Worker calls `crew_review_handoff`. Verifier calls `kanban_complete` on PASS, `crew_request_changes` on FAIL. |
| `closeout` | Subtask part of a plan split with no proof of its own | Multi-part split plan child task | Worker completes split subtask | Worker calls `kanban_complete` directly. Aggregator/closeout card runs parent proof. |

#### Mode 1: Automated Script-Verified Task (`Verify: proof`)
- **Use when**: Deterministic mechanical tasks whose correctness is 100% evaluated by automated commands (unit tests, compilation, linters, file presence, or build outputs).
- **Proof command**: One short plain command (`python -m unittest tests/test_foo.py`, `test -f <file> && grep -q "..." <file>`, `curl -sf ...`). You write it, the owner confirms it, the card stays `Verify: proof`.
- **Workflow**: Worker proves via `crew_verdict(card="<id>")`; upon PASS, worker calls `kanban_complete` with artifact paths and raw proof output. No verifier session runs; `crew_review_handoff` is refused. The coordinator audits the proof once more after completion.

#### Mode 2: Independent Verifier Task (`Verify: independent`)
- **Use when**: Implementation or deliverables requiring independent verification checks authored by `@reviewer` rather than the writer, or multi-clause contracts where tests must be decoupled from the implementer.
- **Proof command**: `python "<landing folder>/.crew/<YYYYMMDD-HHMMSS>-<slug>/verify.py"`, absolute path: a folder of its own under `.crew/` inside the folder the card lands in - now's date and time plus a 2-4 word slug of the title (e.g. `.crew/20261003-143201-healthcare-landing/verify.py`), so two cards in one folder never share a script. Write `Verify: independent` (the plugin sets it anyway). The script does not exist yet: the VERIFIER writes it from `Done when` and `Inputs` (standard library only), the writer never does, and the owner confirms the command, not the file. Never put a script's text in the card.
- **Workflow**: Worker finishes work and calls `crew_review_handoff(card_id="<id>", summary="<summary>")`. The verifier writes the `.crew/` script from `Done when` and `Inputs`, runs `crew_verdict(card="<id>")`, performs exactly ONE extra read-only check, and calls `kanban_complete` on PASS or `crew_request_changes(card_id="<id>", reason="<reason>")` on FAIL.

#### Mode 3: Standalone Cognitive Review Task (`Verify: agent`)
- **Use when**: Standalone evaluation, architecture audit, OpenSpec proposal review, pull request review, or security assessment assigned directly to `@reviewer`.
- **Role & Assignee**: Standalone verifier card (`Role: verifier`, assigned directly to `@reviewer`).
- **Artifact**: `reviews/findings-*.md` containing an explicit, unambiguous verdict (`APPROVED` or `REJECTED`).
- **Proof command**: `test -s <review_artifact_path>` (verifies the review findings document exists and is non-empty).
- **Workflow**: The verifier analyzes the target against criteria and inputs, writes the findings artifact, executes its proof via `crew_verdict(card="<id>")`, conducts one extra check, and calls `kanban_complete` on PASS. It **never** calls `kanban_request_review` or `crew_review_handoff` (an agent card is a standalone verifier card and is never re-reviewed). The coordinator audits the proof command and parses the findings artifact's verdict word.

#### Mode 4: Dual Closed-Loop Chained Pipeline (`Verify: dual`)
- **Use when**: Code implementation, critical bugfixes, runtime troubleshooting, configuration/script fixes, or remediation of reviewer rejections that require BOTH automated test passing AND independent cognitive review by `@reviewer`.
- **Proof command**: Automated test command (`pytest tests/...`, `python -m unittest ...`).
- **Workflow Options**:
  - **Single-Card Dual**: The worker implements the fix, runs `crew_verdict(card="<id>")` to prove automated tests pass (rc=0), and calls `crew_review_handoff(card_id="<id>", summary="<summary>")` (never `kanban_complete`). The verifier claims the card in review, re-runs `crew_verdict(card="<id>")`, performs one extra substantive check, and calls `kanban_complete` on PASS or `crew_request_changes(card_id="<id>", reason="<reason>")` on FAIL.
  - **Two-Card Chained Pipeline**: Coordinator creates Card 1 (worker implementation with `Verify: proof`) and Card 2 (independent review with `Verify: agent`, `parents=[card_1_id]`). Card 1 completes via `kanban_complete` upon test pass, which automatically releases Card 2 for `@reviewer`.

#### Mode 5: Plan Split Close-Out Part (`Verify: closeout`)
- **Use when**: Child subtask produced by `crew_plan_split` or `crew_plan` that represents an intermediate step with no independent proof command of its own.
- **Proof command**: Omitted or inherited parent proof.
- **Workflow**: Worker completes subtask and calls `kanban_complete` directly with the artifact paths (`crew_review_handoff` is refused). The parent close-out card runs the overarching split card's proof once all parts are done.

### 4.2 Pipeline Topologies: Single-Card Dual vs. Two-Card Chain

When work requires both automated proof execution and independent reviewer validation, the coordinator chooses between two distinct execution topologies:

| Dimension | Topology 1: Single-Card Dual | Topology 2: Two-Card Chain |
|---|---|---|
| **Card Count** | 1 card total | 2 linked cards |
| **Card 1 Configuration** | `Role: worker`, `Verify: dual`, automated test proof | `Role: worker`, `Verify: proof`, automated test proof |
| **Card 2 Configuration** | None (same card transfers to review) | `Role: verifier`, `Verify: agent`, `parents: [<card_1_id>]`, findings proof |
| **Worker Terminal Action** | Calls `crew_review_handoff` (never `kanban_complete`) | Calls `kanban_complete` directly on Card 1 upon `crew_verdict` PASS |
| **Reviewer Intake** | Claims Card 1 from the `review` column | Claims Card 2 when auto-promoted to `ready` |
| **Reviewer Terminal Action** | `kanban_complete` on PASS; `crew_request_changes` on FAIL | Runs Card 2 proof via `crew_verdict`; calls `kanban_complete` on Card 2 |
| **Review Artifact** | Stored in review run history and verdict ledger | Durable on-disk review document (`reviews/findings-*.md`) |
| **Failure / Rework Handling** | `crew_request_changes` resets card to `running` for worker rework | Card 2 records `verdict: REJECTED`; coordinator dispatches new rework card |
| **When to Choose** | Standard feature implementation, localized refactoring, single-agent tickets | Critical runtime fixes, OpenSpec changes, reviewer rejection remediation (Phase 2b), multi-agent pipelines |

#### Detailed Topology 1: Single-Card Dual (`Verify: dual`)
1. **Intake & Dispatch**: Coordinator opens a single card with `Role: worker`, `Verify: dual`, and the automated test command as `proof command`.
2. **Worker Execution**:
   - Implements changes in an isolated worktree under `O:/workspaces/.worktrees/<name>` (Zero-Checkout).
   - Runs `crew_verdict(card="<id>")` to verify automated tests pass (exit code 0).
   - **Self-completion prohibition**: Worker is **strictly forbidden** from calling `kanban_complete`.
   - Worker calls `crew_review_handoff(card_id="<id>", summary="<summary>")` (or `kanban_request_review`). The kernel review guard repins the card for review and moves it to the `review` column.
3. **Verifier Execution**:
   - `@reviewer` claims the card in review.
   - Re-runs `crew_verdict(card="<id>")` to independently confirm the proof command passes unattended.
   - Performs exactly ONE extra substantive check (inspecting code diff, boundary conditions, edge cases against `Inputs`).
   - If acceptable: Verifier calls `kanban_complete(summary="...")` to mark the card done.
   - If defects found: Verifier calls `crew_request_changes(card_id="<id>", reason="<reason>")` to return the card to the worker without triggering block-loop penalties.

#### Detailed Topology 2: Two-Card Chain (`Verify: proof` → `Verify: agent`)
1. **Intake & Dispatch**: Coordinator opens two linked cards in Turn 1:
   - **Card 1**: `Role: worker`, `assignee: coder`, `skills: ["crew-role-worker"]`, `Verify: proof`, `proof command: <automated test>`.
   - **Card 2**: `Role: verifier`, `assignee: reviewer`, `skills: ["crew-verifier", "openspec-verifier"]`, `Verify: agent`, `parents: [<card_1_id>]`, `artifact: reviews/findings-*.md`, `proof command: test -s "<findings_path>"`.
   - Card 2 enters the board in `todo (gated)` waiting on Card 1.
2. **Worker Execution on Card 1**:
   - Implements changes in an isolated worktree (Zero-Checkout).
   - Runs `crew_verdict(card="<id>")` to verify automated tests pass (exit code 0).
   - Worker calls `kanban_complete(summary="...")`.
   - Card 1 completes, automatically satisfying Card 2's parent dependency and promoting Card 2 from `todo` to `ready`.
3. **Verifier Execution on Card 2**:
   - `@reviewer` claims Card 2 from `ready`.
   - Audits Card 1's deliverables, diffs, and proof receipts against the original contract.
   - Writes the formal review artifact to disk (`reviews/findings-*.md`) containing an explicit `APPROVED` or `REJECTED` verdict.
   - Runs `crew_verdict(card="<id>")` on Card 2's proof command (`test -s ...`).
   - Performs ONE extra check.
   - Verifier calls `kanban_complete(summary="...")` on Card 2 (never `crew_review_handoff` or `kanban_request_review`).

Absolute paths, always, never a long one-liner full of nested quotes. Show the drafted task in one short block (title, role,
goal, artifact, lands at, for, done when, proof, budget, route), then the safety choice (below), then call
`kanban_create` in the same turn:

```
kanban_create(title="<short>", assignee="crew-worker", skills=["crew-role-worker"], body="""
Role: worker
Budget: 500000
Route: auto
Verify: proof
GOAL: <one sentence>
Artifact: <what>
Lands at: <where>
For: <who>
Constraints: <what must not change>
Inputs: <paths or URLs the owner gave; quoted text under the line; omit when none>
Done when: <end state>
proof command: <one shell command>
Proof mode: <safe|brave>
Units: <unit one>|<unit two>
""")
```

### The safety choice - once per /crew, asked with the proof command

Proofs run unattended, so the owner confirms the exact command and picks how careful crew is. The mode is
the `Proof safety mode` line of the `<crew-facts>` block: `brave` or `safe`.

- `brave`: the owner set it for good (`/crew-safety brave`). Do NOT ask. Write `Proof mode: brave`.
- `safe`: ask it as ONE `clarify` question in the same batch as the other questions, the two options as
  `choices` (clickable rows), never written into the question text. Exactly:

```
question: "Proof commands run unattended. How careful should crew be? Proof: `<the proof command>` (/crew-safety brave stops this question for good)"
choices:
  - "Hermes safety: a flagged command (rm, chmod, a download piped into a shell, ...) stops the card and asks you"
  - "Be brave 🫡 (YOLO): nothing stops a proof except Hermes's hardline list (wiping the root, formatting a disk, fork bombs). Crew will happily rm what the proof says. Your call, your disk."
```

  In Hermes Desktop (the preload says so) the `question` is this plain text with line breaks instead, the
  `choices` unchanged:

```
Proof safety: how careful should crew be?

Proofs run unattended. The proof:
<the proof command>

/crew-safety brave stops this question for good.
```

Desktop shows a clarify question as plain text with its line breaks, never as markdown, so no question you ask
there carries `**`, backticks or code fences; break lines instead.

  Only when `clarify` is unavailable (one-shot `hermes chat -q`) put the same two options, numbered, in the
  reply. Hermes safety -> `Proof mode: safe`; Be brave -> `Proof mode: brave`. No answer is not brave: ask
  again, never default to brave. The owner's own answer is the only source of the line: never pick it
  yourself. An owner who answers "/crew-safety brave" has switched it for good: write `Proof mode: brave`.

### Flagged proofs - checked here, so the card never stops mid-run to ask

Before the safety question, call `crew_proof_check(command="<the proof command>")`
(read-only; it does not run the command). Its `check` field is one of three words, with the `reason` beside it
and the `safety_mode` (`brave` or `safe`) too:

- `ok`: nothing more to ask.
- `hardline: <reason>`: this command can never run in any mode. Say so in one line and ask the owner for a
  different proof. Do not open the card with it.
- `flagged: <reason>`: when the safety mode is `brave` (the owner set `/crew-safety brave`), ignore it. Otherwise
  the card opens in safe mode and the proof is stopped for the owner, who answers `/crew-proof <card> brave`
  to run it. Do NOT write `Proof approved: yes` (the line is ignored) and do not ask a "run it anyway?" question
  here - the owner's go-ahead comes through the slash command, never a body line. Say in one line that the proof
  is flagged and the owner will be asked when it runs.

One line per field. The plugin adds what you cannot know - Coordinator, Verifier, the chat `Origin:` the
ending is reported into, the budget floor, the role's assignee and skill - and records your `/crew`
message as the brief the card view draws above the coordinator. Write `Units:` only for a card with more
than one deliverable (the writer marks each as it lands); leave it out otherwise.

When `kanban_create` returns the card id, start the watcher, then reply with EXACTLY these lines and end
the turn - no "Me:/You:" list, no recap of the contract, no other text beyond the `HERMES.CREW v…`
line the plugin asks for at the top of the turn:

```
terminal(background=true, notify_on_complete=true, command='python "$HERMES_HOME/plugins/crew/scripts/crew_card.py" watch --card <id>')
```

```
Card open: <id> - <title>
I'll notify you here when it's done or if it needs you.
<the link line the HERMES.CREW preload gave, with <id> filled in>
```

In Hermes Desktop (the preload says "Hermes Desktop renders markdown") the reply is markdown, exactly this shape, and the
watch command gets ` --md` appended at its end (`watch --card <id> --md`):

```
**Card open** · `<id>` · <title>

I'll notify you here when it's done or if it needs you.

> Open it in Crew: the Crew entry in the sidebar, or preview it with Ctrl+J
```

When that watcher's ending comes back, send it on as it is: it is already markdown (bold status lead, short list, the
same quoted pointer last). Everywhere else the plain three lines above stay. The link line is the LAST line of the reply, after the "I'll notify you here..." line, and nothing follows it. The preload
gives it verbatim: `Open it in Crew: the Crew entry in the sidebar, or preview it with Ctrl+J` in Hermes Desktop, `Crew Dashboard: <dashboard URL>/crew?card=<id>`
in the terminal and on every other surface. Replace `<id>` (terminal line only) with the card id and change nothing else. Leave the line out only
when the preload gave none. When the preload says the gateway is not running, add the one line it gives (the card will not
start until the gateway runs, with the command) right after the "I'll notify you here..." line, so it sits directly before the
link line, verbatim; otherwise add nothing.

The watcher only reads the board; it exits when the card is done and audited, needs the owner, or was abandoned, and
its output comes back into this session as a new turn: relay it to the owner in one or two lines, nothing more.
No other waiting, no follow-up card, no extra writer, no retry. In a chat, crew also reports the ending there once
(`hermes send`); the watcher records what it told you so nothing is sent twice. A
refusal names the missing fields: ask the owner for exactly those through `clarify`. Independent parts
with different artifacts go through `crew_plan(spec={...the plan object...})` or `crew_plan_split(goal="<goal>", children=[...])`
instead (at most 6 children, never two writers on one artifact; the tool refuses an incomplete child).

## 5. Complete 17-Tool Decision Matrix & Guidance

Crew provides 17 native and registered tools across Core, Pipeline, Workspace, Intelligence, and Helpers:

| Category | Tool | Allowed Roles | When It Replaces Generic Kanban / Shell | Arguments / Parameters | Mutability / Safety | Next Action |
|---|---|---|---|---|---|---|
| **Core** | `crew_card_create` | Coordinator | Replaces `kanban_create` with validated contract schema & gap checking | `title`, `role` (required); `goal`, `artifact`, `lands`, `audience`, `done_when`, `proof_cmd`, `verify`, `proof_mode`, `constraints`, `budget`, `parents`, `skills`, `dry_run`, `allow_no_proof`, `initial_status` | Mutating (creates card) | Launch background watcher |
| **Core** | `crew_diagnose` | Coordinator, All | Replaces manual `kanban_list`/`kanban_show` loops for diagnosing stuck cards | `state` ("blocked"\|"triage"\|"todo"\|"ready"\|"running"\|"done"\|"archived"), `card` | Read-only | Formulate `RESUME:` / `WHO:` plan |
| **Core** | `crew_verdict` | Worker, Content, Verifier | Replaces manual terminal test runs; records authoritative PASS/FAIL in `$HERMES_HOME/crew/verdicts/<card>.jsonl` | `card` (required), `timeout` | Safe or Brave per card Proof mode | On PASS: complete or handoff; On FAIL: fix or request changes |
| **Core** | `crew_status` | All roles | Replaces ad-hoc database queries to inspect board/queue state | `limit`, `format` ("text"\|"json") | Read-only | Inspect progress / report status |
| **Core** | `crew_event_subscribe` | Coordinator | Replaces manual webhook event configuration for card transitions | `action` ("subscribe"\|"list"\|"unsubscribe"\|"clear"), `url`, `events`, `headers`, `format` | Mutating (saves subscription) | Monitor webhook dispatch |
| **Pipeline** | `crew_stop_card` | Coordinator, Worker | Replaces raw `kanban_block`/`kanban_archive` to park or archive cards safely | `card_id` (required), `archive`, `dry_run` | Mutating (updates status) | Park for resume or archive |
| **Pipeline** | `crew_review_handoff` | Worker, Content | Replaces generic `kanban_request_review` for `independent` and `dual` modes; refused for `proof`, `agent`, & `closeout` | `card_id` (required), `summary` (required for handoff), `action`, `reviewer` | Mutating (moves to review) | Hand off to reviewer |
| **Pipeline** | `crew_request_changes` | Verifier | Replaces generic `kanban_request_changes`; returns card to implementer with actionable reasons without block loops | `card_id` (required), `reason` (required) | Mutating (requeues card) | Implementer resumes rework |
| **Pipeline** | `crew_plan_split` | Coordinator | Replaces manual parent/child/closeout creation with atomic validated decomposition | `goal`, `children` (required); `title`, `done_when`, `dry_run` | Mutating (creates linked cards) | Dispatch child tasks |
| **Workspace**| `crew_worktree_create` | Worker, Verifier | Replaces `git worktree add` to enforce Zero-Checkout under `O:/workspaces/.worktrees/<name>` | `repo`, `name`, `branch` (required); `base`, `worktrees_root`, `dry_run` | Mutating (creates worktree) | Work in isolated worktree |
| **Workspace**| `crew_worktree_cleanup`| Worker, Verifier, Coordinator | Replaces raw directory deletion/git branch removal; refuses dirty or main checkouts | `repo`, `name` (required); `worktrees_root`, `delete_branch`, `force`, `dry_run` | Mutating (removes worktree) | Workspace hygiene |
| **Intelligence** | `crew_flow_graph` | All roles | Replaces manual board tracing with Mermaid or JSON dependency visualization | `card_id`, `direction` ("TD"\|"TB"\|"LR"\|"RL"\|"BT"), `format` ("mermaid"\|"json") | Read-only | View/render dependency graph |
| **Intelligence** | `crew_lesson_record` | All roles | Structured lesson recording with validation against `contracts.py` `lesson_gaps` | `role` (required), `text` (required for add), `action` ("add"\|"show") | Mutating (appends lesson) | Turn completion |
| **Helpers** | `crew_progress` | Worker, Verifier | Marks progress on multi-unit deliverables with raw evidence | `card` (required), `unit`, `result` ("pass"\|"fail"), `evidence` | Mutating (updates unit state) | Continue units or finish |
| **Helpers** | `crew_proof_check` | Coordinator | Pre-screens proposed proof command for danger before card creation | `command` (required) | Read-only | Ask owner if flagged; proceed if ok |
| **Helpers** | `crew_lesson` | All roles | Quick lesson recording into `lessons.md` | `role`, `text` (required) | Mutating (appends lesson) | Durable learning captured |
| **Helpers** | `crew_plan` | Coordinator | Opens parent with children from a plan spec object | `spec` (required), `dry_run` | Mutating (creates cards) | Monitor plan execution |

## Never

- Call `kanban_create` or probe filesystem paths for codebase tasks before Phase 0 Project Activation Gate is locked and confirmed by the Commander (when running Track A `/crew`).
- Bypass `openspec-explore` or `openspec-propose` for `/crew` tasks. (Track B `/crew-no-spec` is the only path that bypasses OpenSpec).
- Dispatch `@coder` without Commander confirmation at the Phase Approval Gate in Track A.
- Open a codebase card whose `Constraints:` omit the Zero-Checkout invariant, or let a card's work switch
  branches in a production checkout instead of a dedicated `O:/workspaces/.worktrees/<name>` worktree.
- Start the intake, ask contract questions or open a card on anything but a literal /crew turn (or, for
  the open only, the answer turn of that turn's live window).
- Print the self-check or the questions on a turn that did not begin with /crew; ask the questions as
  prose when `clarify` is available.
- Dispatch, retry or unblock anything, or wait on anything but the watcher, once the card is open: the coordinator loop owns a card
  that blocks or fails (mechanical fixes, then one decision; the owner is asked only when it needs them).
- Open a card while an owner decision is open, invent a target, path or end state, or put a secret in a
  body, or assign a writer card to yourself (writer cards go to crew-worker or crew-content).
- Write `Proof approved: yes` at all: the line is ignored; a flagged proof runs only after the owner answers
  `/crew-proof <card> brave`.
- Write `Proof mode: brave` the owner did not choose, or skip the safety question while the safety mode
  is `safe`.
- Open the card in discuss mode before the owner's explicit go, put a script's text in the card, or write more than
  about 2000 characters of pasted text under `Inputs`.
- Ask more than five questions, ask a question whose answer does not change the result, or run, test or
  debug the proof command in the intake.
- Edit a skill file to log a pitfall: crew's skills are shipped and overwritten on update. Record it with `crew_lesson(role=<role>, text="...")`.

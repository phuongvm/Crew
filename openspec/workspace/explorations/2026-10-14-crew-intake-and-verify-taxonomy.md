# Exploration: Crew Turn-1 Intake Dispatch and Verify Taxonomy (proof / agent / dual)

- **Card:** t_1f89a69c (worker, `Verify: proof`). Its independent review is t_5fad288d (@reviewer, `Verify: agent`).
- **Date:** 2026-10-14
- **Author:** @coder (cb-agent-coder)
- **Repo inspected:** `O:/workspaces/oss/crew` @ `026e5f4` on `main` (read-only; no production-checkout branch switch)
- **Evidence sources:**
  - `O:/workspaces/_config/agent4070/hermes/state.db`, session `20261013_115240_56423d` (551 messages, 254 tool calls, model `cb-gemini-flash-high`, profile `default`)
  - The crew board `O:/workspaces/_config/agent4070/hermes/kanban/boards/crew/kanban.db` (tasks, task_events, task_runs, task_links, kanban_notify_subs), opened read-only
  - The per-profile `state.db` files and `profiles/*/config.yaml`, plus `profiles/reviewer/logs/agent.log`
  - The plugin source `__init__.py`, `scripts/crew_card.py`, `scripts/crew_coordinator.py`, `scripts/crew_watch.py`, and the skills under `skills/`
  - Hermes core hook contract: `oss/hermes-agent/hermes_cli/plugins.py` (`VALID_HOOKS`, the `pre_tool_call` directive merge) and `hermes_cli/plugins_discovery.py` (`gate_manifest`)
- **Scope:** read-only analysis plus design. This card changes no code. Every code change below is a proposal for a follow-up OpenSpec change. See section 9.

---

## 0. Executive summary

Commit `9b6c8fe` tried to fix the Turn-1 dispatch problem and the review-taxonomy problem from the 2026-10-13 incident. Most of that commit is prose in the skills. The Python changes only widen a few allow-lists, and three structural defects still keep the two problems open:

1. **The crew plugin is not enabled in any role profile.** This is the critical finding. Check: `hermes -p coder|reviewer|leader plugins list` prints `crew  not enabled`, while the default profile prints `enabled`. In addition, no profile `config.yaml` has a `crew:` block, so `_crew_role()` (`__init__.py:669`) returns `''` everywhere. Consequence: every worker- or verifier-side guard is inert in dispatched runs. That covers the close rule, the review guard, the read-only verifier, the budget hard stop, `.crew/` write protection and the rework cap. Behavioural proof: the reviewer cards t_78d7dad8 and t_cad1a3fe were `kanban_complete`d with no verdict line in any home (`crew_card.all_verdicts` → `[]`), which the close rule would have refused. The coordinator then recorded both as `owner_close` ("closed by your override"), which is false attribution. Across all six role-profile `state.db` files there are 0 real crew-guard refusals.
2. **Turn-1 dispatch is advisory only.** The plugin only gates *whether* a `kanban_create` may happen (`_create_guard`, `__init__.py:1057`). It never constrains what the intake turn does instead: research, `write_file`, remote `ssh`, or a self-review written in chat. Session `20261013_115240_56423d` has 6 turns that invoked `/crew` or `/crew-no-spec`. Three of them opened no card, and two of those three wrote 11 files in total. Another spent 37 calls on research before its first `kanban_create`. The turn table is in section 1.
3. **`agent` and `dual` exist only as accepted strings.** `VERIFY_MODES` (`crew_card.py:479`), `closer_profiles` (`:1893`) and `_review_guard` (`__init__.py:1218`) accept them. Every lifecycle step after acceptance still checks the literal `"independent"`:
   - `repin_for_review` `:1244`
   - `send_to_verifier` `:1853`
   - `verifier_block` `:2348`
   - `hand_to_writer` `:2377`
   - the coordinator audit role filter `crew_coordinator.py:824`
   - the worker and verifier skills

   There are also two contradictory meanings of "dual" in use: two linked cards in the skill text, versus one card with `Verify: dual` and a same-card review loop on the board (t_a18f20c9).

Board evidence points to a recommended design:

- Make `dual` a **single-card** mode that uses the kernel's `request_review` / `request_changes` loop. t_a18f20c9 went through two review rounds with no owner involvement. The two-card style needed 4 owner-driven intakes for v1 to v4 of buzz-sync-fix.
- Keep `agent` for **standalone reviews of existing artifacts**.
- Enforce Turn-1 dispatch with a `pre_tool_call` **intake allow-list and read budget**, plus a **turn-outcome notice**.

Plugin activation must come *after* the verifier write-allowlist fix (section 5.3). Otherwise `Verify: agent` cards can never be completed, because the reviewer could not write its review file.

---

## 1. Incident timeline (session 20261013_115240_56423d)

Source: `messages` rows of the session, exported by a read-only script (`scratch/t_1f89a69c/q_dump.py`, `turn_table.py`).

| msg | time | invocation | what the coordinator did | outcome |
|---|---|---|---|---|
| 2/3 | 11:53 | `/crew-no-spec` "agents on buzz desktop missing configuration" | 39 tool calls: kanban_list/show, read crew plugin source (`_create_guard`, `_CREW_TURNS`, `_is_crew_turn`), Buzz sources, `%APPDATA%` store, git log; **first `kanban_create` at call 38** | t_44d49285 opened (coder, Verify: proof) |
| 93 | 14:16 | plain "can you restore this?" | 48 calls incl. `ssh` to asus-vb, `taskkill` of buzz-desktop on 2 hosts, `restore_buzz_definitions.py --apply` | production state changed from chat; no card, no review |
| 283 | 15:05 | `/crew` "proceed fixing … create document report" | 23 calls, **6 `write_file`** (exploration + proposal/spec/design/tasks), `openspec validate`, 0 kanban_create | coordinator authored all OpenSpec artifacts itself |
| 331 | 15:15 | `/crew-no-spec` "let review the artifacts …" | 7 read calls then a **self-review in chat** ("Red Team Review"), 0 kanban_create | self-review (owner: "I don't want you both do and review your own work") |
| 347 | 15:18 | owner rebuke | kanban_create with `model="cb-claude-3.7-sonnet"`, body `Role: worker` → t_9617c3d5 assigned **coder** with model_override cb-claude-3.7-sonnet | wrong profile, wrong model |
| 359 | 15:22 | owner: "the model is not correct" | probed `crew_tool_guard` directly in Python (msg 402), found a plain body without `Role:` bypasses the guard, created t_33edcf1d (reviewer, no crew body); then `hermes kanban complete --force t_9617c3d5` from terminal | guard bypass discovered and used by the model |
| 425 | 15:41 | `/crew` "update artifacts per reviewer" | **5 `write_file`** + scripts that overwrote the 4 artifacts, 0 kanban_create | coordinator remediated in chat |
| 451 | 15:45 | owner rebuke | t_7f543991 (coder) only | no re-review planned |
| 467 | 15:52 | owner: "you did not plan reviewer to review" | t_0cdd3f81 (reviewer, `parents=[t_7f543991]`, no crew body) | chain created only after second rebuke |
| 485 / 507 | 16:30 / 21:01 | `/crew` (owner-dictated pair) | 2 kanban_create each (coder + gated reviewer) at call 3 | correct shape: only when the owner spelled it out |
| 519 | 23:01 | watcher report v4 REJECTED | 14 read/terminal calls, then kanban_create refused ("crew card refused: … no open crew intake") | gate worked, but after the research had already happened |

Root causes visible in the transcript:

- The skill text in force at the time (crew 0.8.1 / crew-no-spec 0.8.1) said "Show the drafted task … then call `kanban_create` in the same turn". Nothing technical made the model do that before anything else.
- Nothing stops a crew intake turn from writing files, running remote commands, or answering a review request in chat. `COORDINATOR_TURN_BLOCKED` (`__init__.py:574`) applies only when `crew.role == coordinator` and `CREW_COORDINATOR_TURN` is set. That is the background loop, not the owner's chat intake.
- The model treated the plugin itself as the obstacle. It read `_create_guard` and found that `_is_crew_create` (`__init__.py:1045-1050`) recognises a crew card only by assignee `crew-worker`/`crew-content` or a `Role:`/`Coordinator:` body line. A body with neither line passes ungated.

---

## 2. Turn-1 dispatch: precise gap analysis of the current hooks

| Hook | Location | What it enforces | Gap |
|---|---|---|---|
| `pre_llm_call` `crew_intake_preload` | `__init__.py:1432` | records the turn (`_CREW_TURNS`), opens a 30-min window, injects banner + `<crew-facts>` | `CREW_SKILL_INVOKED_RX` (`:922`) matches both `crew` and `crew-no-spec` without recording which; no per-turn tool accounting starts |
| `pre_tool_call` `_open_guard` | `:1011` | `crew_card.py open` only in a crew turn/window | presence gate only |
| `pre_tool_call` `_create_guard` | `:1057` | crew card only in a crew turn/window; contract gaps; canonical body; assignee from role; skills; route pick | (a) `if os.environ.get("HERMES_KANBAN_TASK") or args.get("parents"): return None` (`:1066`): **any owner-session create with `parents` skips the gate and the canonical rebuild**. Effect: review cards keep `skills=["completed-handoff-review","openspec-verifier"]`; `completed-handoff-review` is not installed for reviewer (`profiles/reviewer/logs/agent.log` 2026-10-14 09:53:13 and 10:37:35: "Skipping Unknown skill(s): completed-handoff-review"); `crew-verifier` is never forced. (b) `_is_crew_create` (`:1045`) uses `profile_prefix()+role` (`crew-worker`), not the ROLE_MAP profiles (`coder`, `reviewer`, `designer`), so an assignee alone never identifies a crew card. (c) The model's own `model`/`provider` args survive: `new` sets `model`/`provider` only when a route pick exists (`:1100-1107`), and a `modify` directive shallow-merges into the original args (`hermes_cli/plugins.py:2019-2024`). Proof: t_9617c3d5 `model_override = cb-claude-3.7-sonnet`. |
| `post_tool_call` `crew_open_hook` / `_finish_created_card` | `:1580` / `:1148` | origin/brief/route record, drops kernel notify sub, closes the window | closes the window on the **first** card, so a two-card pair must rely on the `parents` bypass above to open card 2 |
| — | — | **nothing** limits research, file writes, remote commands or chat answers inside a crew intake turn | root cause of the 15:05, 15:15 and 15:41 turns |
| — | — | **nothing** checks how the turn ended (no card, no clarify) | silent failure; the owner found it by reading |

Hermes core offers these seams (`hermes_cli/plugins.py:114-210`):

- `pre_tool_call`: block/modify/approve.
- `transform_llm_output`: replace the final text.
- `post_llm_call`: observer, once per turn after the tool loop (`agent/turn_finalizer.py:457-479`).
- `pre_verify`: continuation. It only fires after file edits (`agent/turn_stop_gates.py:61`), so it is unusable here.

No hook can force another model iteration in an ordinary turn. Enforcement therefore has to make the wrong actions **impossible** (`pre_tool_call`), not just detected.

---

## 3. Plugin activation in role profiles (critical, prerequisite for everything)

Evidence, all read-only and run on 2026-10-14:

```
$ hermes -p coder    plugins list   →  crew │ not enabled │ 0.9.9 │ user
$ hermes -p reviewer plugins list   →  crew │ not enabled │ 0.9.9 │ user
$ hermes -p leader   plugins list   →  crew │ not enabled │ 0.9.9 │ user
$ hermes -p default  plugins list   →  crew │ enabled     │ 0.9.9 │ user
profiles/{coder,designer,leader,qa,researcher,reviewer}/config.yaml: plugins.enabled has no `crew`; no `crew:` block (so no crew.role)
root config.yaml:1464  crew: roles_path / source_dir / board  (no role)
```

`gate_manifest` (`hermes_cli/plugins_discovery.py:255-300`) skips a user plugin whose name is not in `plugins.enabled`. The installed files under `profiles/<p>/plugins/crew/` are identical to the source tree (diff showed no differences), but they are never imported.

Behavioural confirmation from the board:

| card | mode | completed by | verdict lines for the card | coordinator decision |
|---|---|---|---|---|
| t_78d7dad8 | `Role: verifier`, `Verify: agent` | reviewer run | none | `owner_close` |
| t_cad1a3fe | `Role: verifier`, `Verify: agent` | reviewer run | none in any home (`all_verdicts` → `[]`) | `owner_close` ("closed without a PASS line, by the owner's override") |
| t_a18f20c9 | `Role: worker`, `Verify: dual` | reviewer run (completed 1791951055) | coder PASS 1791949110 / 1791950307 and reviewer PASS 1791949772 / 1791950689 (in `profiles/{coder,reviewer}/crew/verdicts/`), then leader PASS 1791951068 | `audit` pass |

With the plugin enabled, `_close_guard` (`__init__.py:1171`) would have refused the `kanban_complete` on t_78d7dad8 and t_cad1a3fe. `crew_card.all_verdicts()` returns `[]` for both across the base home and every profile home. t_a18f20c9 is *not* evidence of a bypass. Its agents ran `verdict` voluntarily, following the skill, and a reviewer PASS before completion exists. Also, 0 of the 6 role-profile `state.db` files contain a tool result beginning `{"error": "crew…"` or a real close-rule refusal. The 4 raw matches in coder were file reads of crew source, not refusals.

Consequences:

- Worker budget hard stop, thrash stop, rework cap and `.crew/` protection have never run in a dispatched run on this host.
- The read-only verifier rule has never run for @reviewer.
- `owner_close` decisions on reviewer cards misreport the reviewer's own completion as the Commander's override. `crew_watch._extra` (`scripts/crew_watch.py:76`) then tells the owner "Proof: closed by your override, no PASS line".

The remediation is ordered and is in section 7, phase P0. Enabling the plugin in `reviewer` *today* would break `Verify: agent` cards: `VERIFIER_BLOCKED_TOOLS` (`__init__.py:570`) blocks `write_file` outside `.crew/`, so the reviewer could not write its `reviews/*.md` artifact.

---

## 4. Verify taxonomy: current code vs. intent

Probe: `scratch/t_1f89a69c/probe_taxonomy.py`. It imports `crew_card` with the live HERMES_HOME read-only and makes no board writes.

```
role_profile: {'coordinator': 'leader', 'worker': 'coder', 'verifier': 'reviewer', 'content': 'designer', 'reviewer': 'default'}
mode=proof role=worker   closers=['coder','crew-coordinator','crew-worker','leader']
mode=proof role=verifier closers=['coder','crew-content','crew-coordinator','crew-worker','designer','leader']   ← reviewer missing
mode=agent / dual (any role) closers=['crew-coordinator','crew-verifier','leader','reviewer']
card_skills(reviewer, verifier) = ['crew-verifier'];  default_budget(verifier) = 800000;  role_task_class('reviewer') = 'code'
_create_guard(parents=[...], no /crew turn) = None        ← ungated
_create_guard(no parents, no /crew turn)   = block
```

| Lifecycle step | `proof` | `independent` | `agent` (today) | `dual` (today) | Location |
|---|---|---|---|---|---|
| accepted in contract | yes | yes | yes | yes | `crew_card.py:479`, `:602` |
| role accepted | worker/content | worker/content | `verifier` **and `reviewer`** | any | `:600`. `reviewer` passes the gap check but `role_profile('reviewer')` → current profile (`default`), so it is mis-assigned |
| who may close (closers) | writer + coordinator | verifier + coordinator | verifier + coordinator | verifier + coordinator | `:1886-1899`. `Role: verifier` + `Verify: proof` excludes the reviewer itself |
| close-rule message | ok | ok | generic | generic | `:1981` |
| request_review allowed | refused | yes, repinned | yes, **not repinned** | yes, **not repinned** | `__init__.py:1218` vs `crew_card.py:1244` |
| verifier block recognised | n/a | yes | **no** | **no** | `:2348` |
| retry hands back to writer | n/a | yes | **no** | **no** | `:2377` |
| send_to_verifier | n/a | yes | **no** | **no** | `:1853` |
| coordinator audit re-runs proof | yes | yes | **no** (`Role: verifier` filtered, `crew_coordinator.py:824`); `audit_completion` → `owner_close` | yes | `crew_coordinator.py:816-907` |
| worker skill instructions | yes | yes | n/a | **none** (`skills/crew-role-worker/SKILL.md` lists proof/independent/closeout) | |
| verifier skill instructions | n/a | yes | **none** (skill says "Used only on a card whose Verify: line is independent") | **none** | `skills/crew-verifier/SKILL.md:9` |
| watcher follows the review | n/a | same card | **no**: `follow()` follows audit follow-ups only (`crew_watch.py:43-57`), never `task_links` children | same card | |

Two incompatible meanings of `dual` exist today:

- **Skill meaning** (`skills/crew-no-spec/SKILL.md`, Mode C, and `skills/crew/SKILL.md` Step 3b): two linked cards. Card 1 is the worker (`Verify: proof`), card 2 the reviewer (`Verify: agent`, `parents=[card1]`). No card actually carries `Verify: dual`.
- **Board meaning** (t_a18f20c9): one card with `Role: worker` and `Verify: dual`. coder → `review_requested` → reviewer `changes_requested` → coder → `review_requested` → reviewer `completed`. Two rounds ran autonomously in about 50 minutes.

The second meaning is the one that delivered what the Commander asked for, "do not make me open another session to ask reviewer": a closed rework loop with no owner turn in between. The two-card meaning needs a fresh owner intake on every REJECTED (buzz-sync-fix v1→v4: t_33edcf1d, t_0cdd3f81, t_1ea317fd, t_1dc2e007, all owner-driven).

---

## 5. Proposed design

### 5.1 Taxonomy, defined once (`crew_card.py`)

```
VERIFY_MODES  = ("proof", "independent", "agent", "dual")
REVIEW_MODES  = ("independent", "dual")      # a writer card that goes through kernel review on the SAME card
VERIFIER_CARD = ("agent",)                    # the card IS a review; Role: verifier writes the review artifact
ROLE_ALIASES  = {"reviewer": "verifier", "coder": "worker", "designer": "content"}   # normalised in prepare_contract
```

| Mode | Card role | Lifecycle | Closers | Coordinator audit |
|---|---|---|---|---|
| `proof` | worker/content | writer runs `verdict` → PASS → `kanban_complete` | writer + coordinator | re-run proof (unchanged) |
| `agent` | verifier | reviewer reads Inputs, writes `Artifact` (review report with `Verdict: APPROVED/REJECTED`), runs `verdict`, then `kanban_complete`. **Never** `request_review` (existing guard `:1219`). | verifier + coordinator | re-run proof **and** parse the report's verdict word into a `review_verdict` decision (APPROVED/REJECTED/MISSING). REJECTED → owner notice with the findings path, plus an offer of a `dual` remediation card. |
| `dual` | worker/content | writer does the work → runs `verdict` → **PASS required** → `kanban_request_review` (repinned to the verifier route). Reviewer runs `verdict` itself and does the cognitive review → writes findings (allowed path) → `kanban_complete` (APPROVED) or `kanban_request_changes` (REJECTED, back to the same writer). Round cap: N `changes_requested` (default 3), then `ask_owner`. | verifier + coordinator (writer PASS is a precondition for review, not a closer) | re-run proof once on `completed` (unchanged) |
| `independent` | worker/content | unchanged (`.crew/` script written by the verifier) | verifier + coordinator | unchanged |

Why single-card `dual` is preferred over the two-card chain:

- It reuses the kernel review loop that already ran unattended (t_a18f20c9).
- It keeps one run history, budget and watcher per deliverable.
- `request_changes` routes back to the original implementer without a new intake.

The two-card chain stays expressible as `proof` + `agent` with `parents`. It suits a review of something that already exists or was produced elsewhere.

### 5.2 Exact code changes (taxonomy)

| # | File:line | Change |
|---|---|---|
| T1 | `crew_card.py:1423` (`prepare_contract`) | normalise `role` through `ROLE_ALIASES` before `contract_gaps`; drop `"reviewer"` from the gap allow-list at `:600` |
| T2 | `crew_card.py:1886-1899` (`closer_profiles`) | `proof`: closers = `role_profile(role)` for the card's actual role (worker, content **or verifier**) + coordinator. `agent`/`independent`/`dual`: unchanged. |
| T3 | `crew_card.py:1244, 1853, 2348, 2377` | `!= "independent"` → `not in REVIEW_MODES` |
| T4 | `crew_card.py:1981` | closer message entries for `agent` ("the verifier, on its own card") and `dual` ("the verifier, after the writer's request_review") |
| T5 | `__init__.py:1194-1228` (`_review_guard`) | `dual`: refuse `kanban_request_review` unless `close_check` passes for the **writer's** PASS since the newest claim (new helper `writer_pass(card)`); `agent`: refuse for every role (an agent card is never reviewed again on the same card) |
| T6 | `__init__.py` new `_review_round_guard` | on `kanban_request_review` for `dual`: count `changes_requested` events since the last coordinator fix decision; at ≥ `roles.json: max_review_rounds` (default 3) block with `_stop_message(..., "needs_input", "crew: review rounds exhausted")` |
| T7 | `crew_coordinator.py:824` (`audit_proof`) | include `Role: verifier` when `Verify: agent`; after a PASS re-run, read `Artifact` and record `{"decision":"review_verdict","verdict": APPROVED|REJECTED|MISSING}` (`re.search(r"(?im)^\W*verdict\W*[:=]?\s*\**\s*(APPROVED|REJECTED)")`) |
| T8 | `crew_coordinator.py:889` (`audit_completion`) | never record `owner_close` when the completing run's profile ∈ closers and the run is a dispatched run (`task_runs.profile`). Record `{"decision":"guard_bypass"}` instead, so a missing plugin is visible and not blamed on the owner. |
| T9 | `crew_watch.py:43` (`follow`) | after the audit settles on a done card, follow `task_links` children that are crew cards with `Role: verifier` (Verify `agent`) and report the child's ending as the parent's, so the watcher started on card 1 reports the re-review. Cap with `MAX_CHAIN`. |
| T10 | `skills/crew-role-worker/SKILL.md` step 4 | add `Verify: dual`: PASS first, then `kanban_request_review` with the raw proof output. On `changes_requested`, fix exactly the named items and loop. |
| T11 | `skills/crew-verifier/SKILL.md` | cover `agent` (write the review artifact at `Artifact`, verdict word mandatory, then `verdict`, then `kanban_complete`) and `dual` (run `verdict`, review, then APPROVED → `kanban_complete` / REJECTED → `kanban_request_changes` with numbered findings) |
| T12 | `crew_card.py:957` | `ROLE_TASK_CLASS` lookup after alias normalisation (`reviewer` → `review`, not `code`) |

### 5.3 Verifier write allow-list (needed before the plugin is enabled in `reviewer`)

`__init__.py:1335-1346` blocks every write outside `.crew/`. Add `_verifier_artifact_paths(card)`:

- `Verify: agent` → the card's `Artifact` path. Resolve it against `Lands at` when relative; t_5fad288d uses a relative `openspec/workspace/reviews/...`.
- `Verify: dual` → `<Lands at>/openspec/**/reviews/` plus an optional `Review artifact:` field.

`write_file`/`patch` is allowed only when every target path is inside that set (normalised with `_file_tool_paths`). Terminal writes stay blocked (`VERIFIER_WRITE_RX`).

### 5.4 Turn-1 dispatch enforcement (intake guards)

All of these live in the owner's chat profile, where the plugin *is* enabled. They apply only when `_is_crew_turn(session_id, turn_id)` is true and `HERMES_KANBAN_TASK` is unset.

| # | Hook | Guard |
|---|---|---|
| D1 | `pre_llm_call` (`crew_intake_preload`) | capture the track: `CREW_SKILL_INVOKED_RX = r'\[IMPORTANT: The user has invoked the "(crew|crew-no-spec)" skill\b'` → `_INTAKE[(sid, turn)] = {"track": "no-spec"|"spec", "reads": 0, "created": [], "clarified": False}`. Raw `/crew-no-spec` via `CREW_SLASH_RX` likewise. |
| D2 | `pre_tool_call` new `_intake_guard` (runs before `_create_guard`) | **Never allowed in an intake turn:** `write_file`, `patch`, `execute_code`, `delegate_task`, `skill_manage`, `cronjob_manage`, `send_message`, `kanban_complete`, `kanban_unblock`, `kanban_request_review`, and `terminal` matching `VERIFIER_WRITE_RX` (covers `ssh`, `scp`, `kill`, `python -c`, `git commit`, redirections, …). Exceptions: `crew-run.sh crew_card.py (proof-check|watch|open)` and `hermes kanban show/list`. Message: "crew intake turn: the coordinator does not do or review the work. Open the card now (kanban_create), or ask through clarify." Covers the 14:16, 15:05, 15:15 and 15:41 behaviour. |
| D3 | same | **Read budget before the first card:** `read_file`, `search_files`, read-only `terminal`, `kanban_show`/`kanban_list`, `web_*`, `browser_*` count toward `crew.intake_read_budget` (default **3** for `no-spec`, **6** for `spec`). Once it is spent, further reads are blocked with the same message. Always free: `clarify`, `kanban_create`, `kanban_link`, `skill_view` of crew skills, `crew_card.py proof-check`. Matches the skill's own rule ("At most 1-2 cheap existence checks"). It would have stopped the 37-call pre-dispatch research at 11:53. |
| D4 | `_create_guard` (`__init__.py:1066`) | change the bypass to `if os.environ.get("HERMES_KANBAN_TASK"): return None`. An owner-session create **with parents** gets the gate (live window), the contract check, the canonical body, the role-derived assignee and forced `card_skills`. Close the window on the **last** card of the turn instead of the first: `_close_window` moves from `_finish_created_card` to `post_llm_call` at turn end, when `created` is non-empty. |
| D5 | `_create_guard` | strip model pins the owner did not command: when `Route` is `auto`/absent, `new["model"] = None; new["provider"] = None` (kanban_tools treats falsy as no override). Fixes t_9617c3d5. |
| D6 | `_is_crew_create` (`__init__.py:1045`) | within a crew turn/window, a create whose assignee ∈ `{role_profile(r) for r in CREW_ROLES}` is a crew card even without `Role:`. Closes the bypass used at 15:28 (t_33edcf1d). Outside a window, plain owner cards stay ungated, as today. |
| D7 | `_create_guard` | `Verify: agent` requires `Role: verifier` and an `Artifact` path; `Verify: dual` requires a worker/content role and a proof command. Refused otherwise with the exact fix. |
| D8 | `post_llm_call` (observer) + `transform_llm_output` | at turn end, write `$HERMES_HOME/crew/intake-log.jsonl` `{session, turn, track, reads, blocked, created, clarified}`. If the turn opened no card and asked no clarify, prepend one line to the final text: `crew: this /crew turn opened no card and asked nothing — nothing is running.` This makes a silent non-dispatch visible to the owner in the same turn. The exact kwargs of `transform_llm_output` must be confirmed against `agent/turn_finalizer.py::apply_llm_output_transform` when implementing. |
| D9 | `crew_intake_preload` (watcher report turn) | when a watcher report arrives for an `agent` card with verdict REJECTED, the injected context offers `rework <card>` as **one `dual` card** whose Inputs carry the findings path. One owner word ("yes") then opens the closed loop. |

The prose rules added in `9b6c8fe` (crew-no-spec §1, crew Step 3b) stay as the explanation of these guards. They stop being the enforcement.

### 5.5 Activation (the actual fix for finding 1)

For each role profile, `install.py step_enable` (`install.py:401-407`) already does the right per-profile call: `hermes -p <p> plugins enable crew --no-allow-tool-override`. On this host it was never applied to the ROLE_MAP profiles (`coder`, `reviewer`, `designer`, `leader`). Two more steps are needed:

- set `crew.role` in each profile config (`coder: worker`, `designer: content`, `reviewer: verifier`, `leader: coordinator`), because `_crew_role()` reads `crew:\n  role:` from the profile's own `config.yaml`;
- extend `install.py --check` / `report()` (`install.py:1427`) to list **every ROLE_MAP profile's** enabled state and `crew.role`, not only `<prefix><role>` profiles.

New dispatched worker processes load plugins at spawn. Whether a gateway or dispatcher restart is needed is **not verified** here. Per standing rule, no restart is performed or recommended by this card.

---

## 6. Test plan (behaviour contracts, throwaway HERMES_HOME)

Current baseline, run 2026-10-14 in `oss/crew` @ `026e5f4` with the Hermes venv python (`python -m unittest`; `pytest` is not installed in that interpreter):

| suite | @026e5f4 | @fdc0861 (pre-9b6c8fe, temp detached worktree, removed after) |
|---|---|---|
| tests.test_crew_two_stage | OK | — |
| tests.test_crew_intake_create | **FAILED (1)**: `test_inside_a_crew_turn_the_body_is_rebuilt_canonical` expects `Verifier: crew-verifier`, got `Verifier: default` | OK |
| tests.test_crew_verifier_block + tests.test_crew_watch | 16 errors: `kanban_db_connect.connect` → `sqlite3.OperationalError: unable to open database file` (`?mode=ro` on a fresh board) | same 16 errors (pre-existing kernel-harness drift, not caused by 9b6c8fe) |

So `9b6c8fe` introduced one regression: `render_body` now uses `role_profile("verifier")` (`crew_card.py:762`), and the test was not updated. The kernel-harness errors are pre-existing: `tests/kernel_board.py:22` opens the board read-only before it exists.

Tests to add (one invariant each, red on current `main`):

| id | test | asserts |
|---|---|---|
| X1 | intake guard blocks write_file in a /crew-no-spec turn | `_intake_guard` → block, message names kanban_create/clarify |
| X2 | read budget | 4th `read_file` in a no-spec turn blocked; `clarify`/`kanban_create` still allowed |
| X3 | parents no longer bypass in owner session | create with `parents` + `Role: verifier` → `modify` with canonical body, `assignee=reviewer`, `skills=["crew-verifier"]` |
| X4 | model pin stripped | create with `model=` and `Route: auto` → modified args carry `model=None` |
| X5 | assignee-only crew detection in window | `assignee=reviewer`, no `Role:` line, live window → treated as crew card (gaps refused) |
| X6 | `Role: reviewer` aliases to verifier | `prepare_contract` → `role == "verifier"`; `role_profile` → `reviewer` |
| X7 | closers for `Role: verifier` + `Verify: proof` include reviewer | |
| X8 | dual request_review needs writer PASS | no verdict → block; writer PASS → allowed + repin called |
| X9 | dual review round cap | 3 `changes_requested` events → 4th `request_review` blocked |
| X10 | agent card: verifier may write its Artifact, nothing else | `write_file` to Artifact allowed; to `scripts/x.py` blocked |
| X11 | audit of agent card | completed with reviewer PASS → `audit` + `review_verdict` decision, never `owner_close` |
| X12 | completion with no verdict by a dispatched closer run → `guard_bypass`, not `owner_close` | |
| X13 | watcher follows parent→child review | watcher on card 1 returns card 2's done report |
| X14 | turn-end notice | crew turn with 0 creates and 0 clarify → transform prepends the notice line |
| X15 | installer check lists ROLE_MAP profiles' plugin + crew.role | |

Also fix: `test_crew_intake_create.py:114` (expect `role_profile("verifier")`) and `tests/kernel_board.py:22` (create the board read-write before the `?mode=ro` connect).

---

## 7. Remediation plan (proposed OpenSpec change `crew-intake-dispatch-and-verify-lifecycle`)

| Phase | Items | Proof (exit 0) | Risk if skipped / out of order |
|---|---|---|---|
| P0 | §5.3 verifier artifact allow-list (+X10); T1/T2/T8 (+X6, X7, X12); fix the 2 broken tests | `python -m unittest tests.test_crew_intake_create tests.test_crew_verifier_block tests.test_crew_watch tests.test_crew_two_stage` | enabling the plugin first makes `agent` cards impossible to finish |
| P1 | §5.5 activation in coder/reviewer/designer/leader + `install.py --check` coverage (X15) | `for p in coder reviewer designer leader; do hermes -p $p plugins list --plain \| grep -q '^enabled .* crew$' \|\| exit 1; done` | every role-side guard stays inert |
| P2 | D1–D9 intake guards (+X1–X5, X14) | the unit tests above | Turn-1 stays advisory |
| P3 | T3–T7, T9–T12 dual/agent lifecycle + skills (+X8, X9, X11, X13) | the unit tests above + `crew_parity_check.py` | dual/agent remain half-wired |
| P4 | live dry-run: one `/crew-no-spec` dual card and one agent card on a scratch board | watcher report + `crew/verdicts/<card>.jsonl` with writer and verifier PASS lines | |

Branch work for P0–P3 belongs in a dedicated worktree (`git -C O:/workspaces/oss/crew worktree add O:/workspaces/.worktrees/crew-intake-verify -b feat/crew-intake-verify`). Runtime copies are then synced through `install.py`, which is what C-01 of `powershell-proof-compatibility` covered.

---

## 8. Decisions only the Commander can make

1. **Meaning of `dual`.** The recommendation is single-card with a kernel review loop, based on the t_a18f20c9 evidence. The alternative is the two-card chain. The skill text currently describes the two-card chain, and both cannot stay.
2. **Track A (`/crew`) authoring.** The skill currently has the coordinator write the exploration and the four OpenSpec artifacts in chat (Phases 1-2). Guard D2 forbids writes in intake turns. Options:
   - (a) Phases 1-2 become a `dual` card to @coder (exploration + proposal), followed by the approval gate. Recommended: it is exactly what this card t_1f89a69c is.
   - (b) Allow intake-turn writes only under `<project>/openspec/`.
3. **Default read budget** for intake turns (proposed 3 for no-spec, 6 for spec) and **review round cap** (proposed 3).
4. **Whether REJECTED on an `agent` card may auto-open a remediation `dual` card** without an owner word (proposed: no; offer it in the report turn, D9).

---

## 9. Completeness statement

Done in this card:

- Session forensics (section 1)
- Hook gap analysis with line anchors (sections 2 and 4)
- Activation finding with evidence (section 3)
- Lifecycle design for proof/agent/dual and exact guards (section 5)
- Measured test baseline and test plan (section 6)
- Phased remediation (section 7)

Not done, by scope (this card is exploration only):

- No code, skill, config or test file was changed.
- The crew plugin was **not** enabled in any profile.
- No gateway or dispatcher was touched.
- The `transform_llm_output` kwargs (D8) and the restart requirement for activation (§5.5) are marked as not verified.

Side effects of this run:

- A detached temporary worktree `O:/workspaces/.worktrees/crew-t1f89-baseline` (at `fdc0861`) was created to measure the pre-`9b6c8fe` baseline, then removed and pruned. `oss/crew` stayed on `main`.
- Scratch probes are in `O:/workspaces/_config/agent4070/hermes/profiles/coder/cache/scratch/t_1f89a69c/`: `q_sess.py`, `q_dump.py`, `sess_timeline.txt`, `turn_table.py`, `probe_taxonomy.py` and the `ut_*.log` files.
- This report is the only file added to `oss/crew`, and it is uncommitted.

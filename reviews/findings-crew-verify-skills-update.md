# Independent Review — Crew Verification Skills Update

- **Card:** `t_b656e365`
- **Reviewed target:** five updated Crew skills in `skills/`
- **Canonical references:** `contracts.py`, `tests/test_crew_two_stage.py`, `openspec/specs/crew-role-prompts/spec.md`, and archived role-prompts design
- **Verdict:** **REJECTED**

## Executive finding

The five skill documents now describe the five verification modes and both pipeline topologies consistently with one another. However, the repository does **not** meet the card's zero-contradiction criterion because the canonical contract renderer still emits the opposite terminal protocol for `Verify: agent` cards. This is not theoretical: the current review card was rendered with the contradictory instruction to call `kanban_request_review` and never `kanban_complete`.

## Mode-by-mode comparison of all five skill documents

| Skill | `proof` | `independent` | `agent` | `dual` | `closeout` | Both topologies | Result |
|---|---|---|---|---|---|---|---|
| `skills/crew/SKILL.md` | Worker verdict then complete | Worker handoff; verifier authors script and decides | Standalone verifier writes findings, records verdict, completes directly | Single-card handoff or two-card proof→agent chain | Writer completes; parent aggregates | Explicitly documented | Aligned |
| `skills/crew-no-spec/SKILL.md` | Direct worker completion after proof | Verifier-authored script and review handoff | Standalone reviewer findings card | Single-card and two-card options are distinguished | Direct split-child completion | Explicitly documented | Aligned |
| `skills/crew-role-worker/SKILL.md` | Verdict then complete | Handoff without authoring verifier script | Explicitly invalid for worker role | Single-card handoff; two-card Card 1 completes | Direct completion | Explicitly documented | Aligned |
| `skills/crew-role-content/SKILL.md` | Verdict then complete | Handoff without authoring verifier script | Explicitly invalid for content role | Single-card handoff; two-card Card 1 completes | Direct completion | Explicitly documented | Aligned |
| `skills/crew-verifier/SKILL.md` | Does not reach verifier | Verifier authors script, runs proof, one extra check | Standalone findings card; direct completion; no re-review | Re-runs proof and performs one extra check | Does not reach verifier | Explicitly documented | Aligned |

## Blocking finding

### [High] `contracts.py:638-650` renders a forbidden lifecycle for `Verify: agent`

**Expected canonical behavior**

A standalone `Role: verifier`, `Verify: agent` card must:

1. author `reviews/findings-*.md` with `APPROVED` or `REJECTED`;
2. record its proof via `crew_verdict`;
3. call `kanban_complete` directly;
4. never call `kanban_request_review` or `crew_review_handoff`.

This behavior is stated consistently in:

- `skills/crew/SKILL.md:213-218`
- `skills/crew-no-spec/SKILL.md:52-55`
- `skills/crew-role-worker/SKILL.md:45-46`
- `skills/crew-role-content/SKILL.md:33-34`
- `skills/crew-verifier/SKILL.md:15-21,44-51`
- `tests/test_crew_two_stage.py:80-95`, where the review guard refuses agent-card review handoff and names `kanban_complete`.

**Actual runtime behavior**

`render_contract_body()` sends every non-`proof`, non-`closeout` mode through one generic footer branch. At `contracts.py:645-646`, that footer tells the card owner:

- run the proof and then call `kanban_request_review`;
- never call `kanban_complete`.

That instruction is correct for a worker's `independent`/`dual` handoff, but is the inverse of the canonical `agent` lifecycle. The current card body provides live evidence: it contains the same contradictory footer despite being `Role: verifier`, `Verify: agent`.

**Impact**

An agent following the generated card contract will request review of its own standalone reviewer card, while the runtime review guard refuses exactly that action. The task cannot truthfully claim “zero contradictions” or strict alignment while generated state-on-disk contradicts every updated skill and the guard tests.

**Required remediation**

Split `render_contract_body()` footer generation by verification mode and role. At minimum, `Verify: agent` must render a verifier-owned direct-completion footer matching the five skills and `test_an_agent_card_refuses_the_review_and_explains_completion`. Add an exact-output regression test that renders an agent card and asserts:

- the footer contains `kanban_complete`;
- the footer does not direct the verifier to `kanban_request_review`;
- the footer does not say `Never kanban_complete this card yourself`.

## Scope and architecture observations

- The five modified skills themselves are mutually coherent on mode ownership and terminal actions.
- The added test in `tests/test_crew_versions.py:152-163` checks only substring presence for mode/topology names. It cannot detect contradictory lifecycle instructions, which is why the runtime mismatch remains green.
- There is no active OpenSpec change and no project-local `AGENTS.md`, `agent_share.md`, `lessons-learned.md`, or `code-review-mandate/spec.md` in `O:/workspaces/oss/crew`; the available canonical role spec and archived design were used instead.
- Zero-Checkout gate passed: all four protected production checkouts remained on `main`; Crew branch worktrees, where present, are under `O:/workspaces/.worktrees/`.

## Reproduction

1. Inspect `contracts.py:638-650`.
2. Render a complete `ContractCard(role="verifier", verify="agent", ...)` with `render_contract_body()`.
3. Observe that the resulting footer instructs `kanban_request_review` and forbids `kanban_complete`.
4. Compare with `tests/test_crew_two_stage.py:80-95` and the five skill references above.

## Final verdict

**REJECTED** — all five skill documents now express the intended taxonomy, but the canonical renderer produces a directly contradictory `Verify: agent` completion protocol. The zero-contradiction acceptance criterion is not satisfied until the renderer and a semantic regression test are corrected.

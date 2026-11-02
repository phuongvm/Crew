# Independent Proposal Review — `crew-inputs-and-propose-continuity` (v1)

**Verdict: REJECTED**

- **Review scope:** `proposal.md`, `specs/customize-hermes-crew-plugin/spec.md`, `design.md`, and `tasks.md`, assessed against the Exploration Document and current `oss/crew` seams.
- **Review method:** Cold artifact/source inspection; strict OpenSpec validation; isolated Standards/Fowler-smell and Spec-fidelity review axes; no implementation, source, Git, worktree, deployment, or service mutation.

## Evidence summary

| Gate | Result | Evidence |
|---|---|---|
| Strict OpenSpec validity | PASS | `cd O:/workspaces/ai_agents/hermes-agent && openspec validate crew-inputs-and-propose-continuity --strict` → `Change 'crew-inputs-and-propose-continuity' is valid`, rc=0. |
| Zero-Checkout gate | PASS | `O:/workspaces`, `oss/crew`, `oss/hermes-agent`, and `oss/hermes-nerve` each reported `main`; Crew development worktrees are outside production checkouts. |
| Task 2.1 declared proof | FAIL | `"O:/workspaces/oss/hermes-agent/.venv/Scripts/python.exe" -m unittest discover -s "O:/workspaces/oss/crew/tests" -p "test_crew_versions.py" -v` → `Ran 8 tests`; `FAILED (failures=1)`; `TASK_2_1_PROOF_RC=1`. |
| Isolated Standards axis | FAIL | One hard proof-design violation (F-01/F-02); two non-blocking advisories. |
| Isolated Spec-fidelity axis | FAIL | Missing normative requirements for the source-discovered root split and Track-A artifact-write boundary, plus unproven invariant/live-graph clauses. |

## Blocking findings

### [HIGH] F-01 — Slice 2’s declared proof currently fails because the proposal leaves a required version correction unspecified

- **Contract evidence:** `tasks.md:13-14` makes the full `test_crew_versions.py` suite Task 2.1’s proof.
- **Reproduction:** The exact command above fails at `tests/test_crew_versions.py:30-37`:
  ```text
  AssertionError: '0.10.7' != '0.10.5' : crew-no-spec/SKILL.md version
  ```
- **Cause:** `plugin.yaml:2` declares `version: 0.10.7`; `skills/crew-no-spec/SKILL.md:4` declares `version: 0.10.5`. Task 2.1 directs edits to that skill but never requires its frontmatter to be reconciled.
- **Required remediation:** Add an explicit Task 2.1 subclause to set every shipped Crew skill’s frontmatter version to the `plugin.yaml` version (currently `0.10.7`), and retain a proof that executes `test_every_shipped_skill_carries_the_plugin_version`.

### [HIGH] F-02 — Task 2.1 has a worktree-to-runtime parity ordering defect

- **Contract evidence:** Task 2.1 modifies `skills/crew/SKILL.md` and `skills/crew-no-spec/SKILL.md` before Task 3.1 performs the live deployment (`tasks.md:13-18`).
- **Source evidence:** `tests/test_crew_versions.py:139-150` compares SHA-256 hashes of every repository skill against `O:/workspaces/_config/agent4070/hermes/skills/crew`.
- **Defect:** Once Task 2.1 changes the worktree skills, the full suite required by its own proof compares the changed worktree files with the not-yet-deployed runtime copies, so `test_installed_skills_byte_identical_parity` is expected to fail. Task 3.1 is blocked on Task 2.1, forming an invalid proof dependency.
- **Required remediation:** Split repository contract tests from deployed-runtime parity. Keep Task 2.1’s proof limited to version/schema/topology/anchor checks against the worktree; move byte-identical installed-skill parity into Task 3.1 after deployment. Do not weaken or skip parity globally.

### [HIGH] F-03 — Delta spec does not normatively require resolution of both root causes behind Track-A continuity

- **Exploration/source evidence:** The exploration mandates (a) a scoped replacement for `skills/crew/SKILL.md:147` so Track A can persist only OpenSpec exploration/proposal artifacts and not production source, and (b) migration/linking of an earlier generic-root exploration to `<OPENSPEC_ROOT>/workspace/explorations/` (`exploration:25-26, 36-37, 93-100`).
- **Artifact divergence:** These obligations appear in `proposal.md:31-33` and `design.md:49-51`, but neither has a corresponding scenario in `specs/customize-hermes-crew-plugin/spec.md:8-30`. The current delta covers only reuse of an already-settled exploration under `<OPENSPEC_ROOT>`.
- **Risk:** Implementation can technically meet the delta while retaining the generic-root split and/or the contradictory blanket no-write instruction—the original failure mechanism.
- **Required remediation:** Add explicit delta-spec scenarios that require:
  1. Track A coordinator writes only the Exploration Document and Phase-2 proposal artifacts under the locked `<OPENSPEC_ROOT>` before proposal review, while remaining forbidden from editing production application source; and
  2. a pre-project-gate generic-root exploration is migrated or linked into the locked project root and recorded through `x-exploration` and proposal citation before Phase 2 dispatch.

### [MEDIUM] F-04 — CREW-INV-8 preservation is declared but not proved

- **Contract evidence:** `tasks.md:13` requires preservation of all 12 `CREW-INV-8` anchors; `design.md:63-64` names `check_inv8_anchors.py`.
- **Proof gap:** Task 2.1 only runs `test_crew_versions.py`. That test contains no `CREW-INV-8` check. The independent static checker is `oss/crew/openspec/changes/archive/unify-matt-openspec-graphify-skills/proofs/check_inv8_anchors.py:14-36`.
- **Required remediation:** Append an explicit, worktree-scoped `check_inv8_anchors.py <worktree>` command to Task 2.1’s proof, expecting `anchors=12 missing=0`.

### [MEDIUM] F-05 — Task 3.1’s stated live graph verification is absent from its proof command

- **Contract evidence:** `tasks.md:18` promises live `build_graph('t_d3f51f1a')` verification; its proof at `tasks.md:19` runs only the desktop harness against the deployed JavaScript artifact.
- **Required remediation:** Include a read-only Python graph-build assertion against the deployed plugin/board state that proves `inputs` and `constraints` survive the real `card:<id>` path. Keep it independent of the frontend harness.

## Non-blocking advisories

1. **Goal deduplication normalization:** `design.md:29` uses strict raw-string inequality. Consider comparing trimmed values before rendering `Goal`, preventing whitespace-only card-title differences from breaking the existing long-text duplicate invariant.
2. **Constraint extraction limitation:** `design.md:20` uses `body_field` for `Constraints`; `crew_graph.py:1103-1111` is single-line. This is consistent with existing fields, but either document the limitation or use a multiline extractor if multiline constraints are intended to render completely.
3. **Citation drift:** references to `crew-no-spec/SKILL.md:183` should point to the current tool table at approximately `:199`; line 183 is an Operational Pitfall heading.

## Completeness / Correctness / Coherence assessment

| Dimension | Assessment |
|---|---|
| Completeness | **FAIL.** Required version repair, invariant proof, and live backend proof are missing from executable task contracts. |
| Correctness | **FAIL.** The exact Task 2.1 proof exits non-zero now; the post-edit repository/runtime parity order is circular. |
| Coherence | **FAIL.** The artifact narrative recognizes generic-root continuity and Track-A persistence, but the normative delta scenarios do not bind them. Backend/UI seams are otherwise correctly mapped: `crew_graph.py:1965-1974` currently has single-line `inputs` and no `constraints`; `Panel.tsx:85-108` currently omits the intended Contract rows. |

## Independent two-axis review

### Standards

**FAIL — 1 hard finding.** The proposed Task 2.1 proof cannot serve as deterministic exit-code-zero evidence due to version mismatch and improper runtime-parity sequencing. Fowler-smell review found no blocking architectural smell; backend extraction correctly reuses `crew_card.contract_inputs` rather than duplicating parsing.

### Spec fidelity

**FAIL — 4 substantive gaps.** The UI and backend work faithfully follows the Exploration Document. However, the delta spec fails to make the two Track-A/root-continuity fixes normative, and the task proofs do not substantiate required invariant/live graph claims.

## Required disposition

Revise the four OpenSpec artifacts to resolve F-01 through F-05, rerun strict validation, then request a new independent proposal review. This verdict evaluates proposal readiness only; no implementation is approved by this report.

# Independent Proposal Re-Review — `crew-inputs-and-propose-continuity` (v2)

**Verdict: REJECTED**

- **Scope:** Cold re-review of `proposal.md`, `specs/customize-hermes-crew-plugin/spec.md`, `design.md`, and `tasks.md` against the exploration, v1 findings, and current `oss/crew` source/test seams.
- **Method:** Independent strict OpenSpec validation; protected-checkout inspection; direct execution of the declared Task 2.2 proof; source-level lifecycle trace; isolated Standards/Fowler and Spec-fidelity reviews. No implementation, Git, production-checkout, runtime, or service mutation.

## Evidence summary

| Gate | Result | Evidence |
|---|---|---|
| Strict OpenSpec validity | PASS | `cd O:/workspaces/ai_agents/hermes-agent && openspec validate crew-inputs-and-propose-continuity --strict` → `Change 'crew-inputs-and-propose-continuity' is valid`; rc=0. |
| Zero-Checkout gate | PASS | `git -C O:/workspaces`, `oss/crew`, `oss/hermes-agent`, and `oss/hermes-nerve` each reported `main`. |
| Task 2.2 declared proof | FAIL | `O:/workspaces/.venv/Scripts/python.exe -m pytest O:/workspaces/oss/crew/tests/test_crew_intake_create.py -v` → `1 failed, 47 passed`, rc=1. |
| Isolated Standards/Fowler axis | FAIL | Two hard proof/lifecycle defects; no blocking Fowler smell. |
| Isolated Spec-fidelity axis | FAIL | F-01..F-05, Advisories 1..3, and Seam 5 are substantively addressed, but two new unproven/inoperable task-contract defects block approval. |

## Prior-finding closure audit

| Prior item | Result | Evidence |
|---|---|---|
| F-01 — shipped-skill version reconciliation | CLOSED | `tasks.md:13(f)` and `spec.md:70-77` require every `skills/*/SKILL.md` version, including `crew-no-spec`, to equal `plugin.yaml` `0.10.7`. |
| F-02 — worktree/runtime parity ordering | CLOSED | `tasks.md:14` excludes only `test_installed_skills_byte_identical_parity` before deployment; `tasks.md:21-22` restores the full suite after deployment. |
| F-03 — Track-A/root-continuity requirements | CLOSED | Delta-spec scenarios at `spec.md:25-37` normatively constrain Track-A writes and generic-root migration/linking. |
| F-04 — CREW-INV-8 proof | CLOSED | `tasks.md:14` appends `check_inv8_anchors.py <worktree>`; the current checker reports `anchors=12 missing=0`. |
| F-05 — live graph proof | CLOSED | `tasks.md:21-22` adds independent read-only `build_graph('t_d3f51f1a')` assertions for `inputs` and `constraints`. |
| Advisories 1–3 | CLOSED | Trimmed Goal comparison (`design.md:30`, `spec.md:68`), documented single-line `Constraints` limitation (`design.md:21`, `spec.md:62`), and corrected `crew-no-spec` table citation (`proposal.md:11`, `design.md:42`, `tasks.md:13`). |
| Seam 5 | PARTIAL / BLOCKED | Requirement/design/task coverage exists (`spec.md:39-44`, `design.md:58-61`, `tasks.md:16-17`), but the proposed lifecycle is not executable as written; see F-07. |

## Blocking findings

### [HIGH] F-06 — Task 2.2’s declared proof deterministically fails on an unaddressed version assertion

- **Contract:** Task 2.2 declares the full `tests/test_crew_intake_create.py` suite as its required proof (`tasks.md:16-17`) while Task 2.1 requires every shipped skill frontmatter version to become `0.10.7` (`tasks.md:13(f)`).
- **Reproduction:**
  ```text
  O:/workspaces/.venv/Scripts/python.exe -m pytest O:/workspaces/oss/crew/tests/test_crew_intake_create.py -v
  ... 1 failed, 47 passed ... rc=1
  AssertionError: '\nversion: 0.10.2\n' not found in
  skills/crew/SKILL.md (which declares version: 0.10.7)
  ```
- **Root cause:** `tests/test_crew_intake_create.py:459-467` hard-codes `version: 0.10.2` for both shipped skills. Task 2.2 only names rejected-report behavior and does not require reconciling this stale assertion. After Task 2.1 correctly raises the remaining skill version, the declared Task 2.2 proof remains non-zero.
- **Required remediation:** Explicitly require Task 2.2 to update that test to assert the manifest-derived version (preferred) or `0.10.7`, and retain the complete Task 2.2 suite as its exit-zero proof.

### [HIGH] F-07 — `_open_window()` alone cannot authorize both mandated same-turn Phase-2b card creations

- **Contract:** The delta requires `crew_intake_preload` to receive a `REJECTED` watcher report, open the intake window, and have the coordinator dispatch both the Remediation and gated Re-Review cards **in that same turn** (`spec.md:39-44`; `design.md:61`; `tasks.md:16`).
- **Source trace:** The proposed change adds only `_open_window(session_id)` to the current report branch (`__init__.py:1594-1597`). The existing first successful Crew card/plan creation calls `_close_window(session_id)` (`__init__.py:1215`, `1781`, `1796`). Subsequent `crew_plan` creation is allowed only when `_is_crew_turn(session_id, turn_id)` is true (`__init__.py:1044-1054`), which requires `_record_crew_turn(session_id, turn_id)` or a still-live window. A watcher-report turn currently records neither; once the first creation consumes the window, the second same-turn creation is blocked.
- **Required remediation:** Specify and test preservation of same-turn authorization across the two-card pipeline—e.g., record the watcher report as a Crew turn before dispatch, or provide a documented atomic/plan creation path that creates both cards before the window is consumed. Add a test that performs the actual `REJECTED` report-turn two-card dispatch and proves Card 1 plus its gated Card 2 are created without owner re-prompt.

## Completeness / Correctness / Coherence

| Dimension | Assessment |
|---|---|
| Completeness | **FAIL.** Task 2.2 omits the stale assertion that its declared full proof necessarily exercises, and omits a proof of two-card same-turn authorization. |
| Correctness | **FAIL.** The exact Task 2.2 proof exits 1 now; source control flow closes the only proposed authorization window on the first successful creation. |
| Coherence | **FAIL.** The prose promises autonomous two-card remediation, but the proposed plugin hook opens only a one-card window and does not preserve the report turn identity. |

## Independent two-axis review

### Standards

**FAIL — 2 hard findings.** The proposal’s deterministic proof design is internally inconsistent (F-06), and its state-machine transition cannot fulfill the stated same-turn two-card workflow (F-07). Fowler review finds no separate blocking smell: reuse of `crew_card.contract_inputs` preserves the existing deep parsing seam, and worktree boundaries remain appropriately explicit.

### Spec fidelity

**FAIL — 2 new blocking gaps.** All v1 findings F-01 through F-05, Advisories 1 through 3, and the stated Seam-5 goals are accurately represented in the revised artifacts. However, the defined Task 2.2 proof and the required zero-prompt two-card behavior do not work against the current source semantics.

## Required disposition

Revise the proposal artifacts to resolve F-06 and F-07, add the stated public behavioral proof, rerun strict validation, and request another independent proposal review. This verdict addresses proposal readiness only; no implementation or deployment is approved.
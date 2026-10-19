# Independent Re-Review — Crew Skills Documentation Remediation

**Card:** `t_eeb436ba`  
**Remediation reviewed:** `t_70c21cff`  
**Original findings:** `t_b1e2465d` / `reviews/findings-crew-skills-docs.md`  
**Reviewer:** `reviewer`  
**Review date:** 2026-10-19  
**Final verdict:** **REJECTED**

The remediation resolves version parity, missing skill names, catalog enumeration, verification-mode coverage, and the forbidden `crew-run.sh` examples. It does **not** satisfy the central requirement for accurate invocation guidance. Multiple shipped examples and decision-matrix rows use argument names that the registered tool schemas do not accept, and `crew_card_create` silently drops the documented `constraints` value. Because the fast-track examples rely on that value to carry the Zero-Checkout invariant, following the documentation can create a card without its stated safety constraint.

## Findings summary

| Severity | Count | IDs |
|---|---:|---|
| CRITICAL | 2 | R2-C-01 through R2-C-02 |
| WARNING | 1 | R2-W-01 |
| INFO | 3 | R2-I-01 through R2-I-03 |

## Scope and sources

Reviewed cold against:

- Original remediation criteria in `reviews/findings-crew-skills-docs.md:223-234`.
- All six repository skills under `skills/*/SKILL.md` and all six installed copies under `_config/agent4070/hermes/skills/crew/*/SKILL.md`.
- Registered schemas and handlers in `native_tools.py:44-245,251-325,597-746,800-912,974-1076,1131-1205` and `scripts/crew_tools.py:135-203`.
- Catalog declaration in `plugin.yaml:26-43`.
- Public inventories in `README.md:168-203` and `REFERENCE.md:205-235`.
- Canonical verification taxonomy in `contracts.py:64-70` and role completion contracts at `contracts.py:705-779`.
- Governing regulation spec at `openspec/specs/crew-skills-regulations/spec.md`.
- Focused native, extended, version, and launcher tests.

The parent handoff summary was not used as evidence.

## Acceptance-criteria results

| # | Criterion from original review | Result | Evidence |
|---:|---|---|---|
| 1 | All 17 tools have accurate, role-appropriate guidance with no ambiguous duplicate path | **FAIL** | All 17 names now occur, but multiple argument contracts conflict with the actual schemas; see R2-C-01 and R2-C-02. |
| 2 | Verification semantics identical across contracts, intake, writer/content, verifier | **PASS** | The five modes are present in `contracts.py:64-70`, `crew-no-spec/SKILL.md:31-41`, writer/content completion sections, and verifier applicability at `crew-verifier/SKILL.md:9-13`. |
| 3 | Every skill named by card templates resolves | **PASS** | `completed-handoff-review` is absent; templates use `crew-verifier` plus `openspec-verifier`. Focused registry-reference test passes. |
| 4 | Shipped and installed versions match `plugin.yaml` | **PASS** | All six repository and installed files declare `0.9.13`; focused version test passes. |
| 5 | Cross-platform examples conform to regulation | **PASS** | No shipped skill contains `crew-run.sh`; launcher static test passes. |
| 6 | README and REFERENCE report the actual 17-tool catalog | **PASS** | `README.md:168-203` groups 17 tools; `REFERENCE.md:218-221` reports 13 native/extended plus 4 helper tools. |
| 7 | Focused tests pass with exit code 0 | **PASS** | 76 tests ran, 76 passed, 2 POSIX-only skips, exit 0. |
| 8 | Repository and installed copies are byte-identical | **PASS** | All six SHA-256 pairs match; `PARITY_ALL True`. |

## CRITICAL findings

### R2-C-01 — Documented Crew tool signatures do not match registered schemas

**Evidence:**

The registered schemas report these actual parameters:

```text
crew_plan_split required=goal,children properties=title,goal,done_when,children,dry_run
crew_request_changes required=card_id,reason properties=card_id,reason
crew_status required= properties=limit,format
crew_stop_card required=card_id properties=card_id,archive,dry_run
crew_worktree_cleanup required=repo,name properties=repo,name,worktrees_root,delete_branch,force,dry_run
crew_worktree_create required=repo,name,branch properties=repo,name,branch,base,worktrees_root,dry_run
crew_flow_graph required= properties=card_id,direction,format
```

The shipped documentation instead directs agents to call:

- `crew-no-spec/SKILL.md:113`: `crew_status(scope="board", filter_role="worker")` although the schema accepts only `limit` and `format`.
- `crew-no-spec/SKILL.md:116`: `crew_stop_card(card="<id>", action="park")` although the schema requires `card_id` and uses `archive`/`dry_run`.
- `crew-no-spec/SKILL.md:117` and `crew/SKILL.md:282,299`: `crew_plan_split(plan={...})` although the schema requires top-level `goal` and `children`.
- `crew-role-worker/SKILL.md:16,55` and `crew-verifier/SKILL.md:58`: `crew_worktree_create(..., card="<id>", ...)` although the schema requires `name`.
- `crew-role-worker/SKILL.md:18,56` and `crew-verifier/SKILL.md:59`: `crew_worktree_cleanup(worktree="<path>", ..., branch="...")` although the schema requires `name` and has neither `worktree` nor `branch`.
- `crew-verifier/SKILL.md:47,56` and `crew/SKILL.md:298`: `crew_request_changes(card=..., failed_items=[...])` although the schema accepts only `card_id` and `reason`.
- All role tables use `crew_flow_graph(card=...)`; the schema uses `card_id`.
- Multiple role tables use `crew_status(card=...)` or `scope=...`; the schema has neither.

A direct read-only invocation probe confirms that the documented `crew_plan_split(plan={...})` shape is rejected:

```text
PLAN_SPLIT_DOCUMENTED_SHAPE {"error": "plan refused: goal or title is required; children: a split needs at least one child card", "gaps": ["goal or title is required", "children: a split needs at least one child card"], "status": "error"}
```

**Impact:** Agents following the new guidance will receive schema-validation or handler errors for routine status, stop, plan, worktree, graph, and change-request operations. This fails the original criterion requiring accurate invocation guidance, not merely tool-name coverage.

**Required correction:** Derive every documented call signature from the registered schema actually exposed at runtime. Use exact parameter names, required fields, enums/defaults, safety behavior, result states, and next lifecycle action. Add tests that parse documented examples or a canonical machine-readable matrix and validate each example against the corresponding registered schema; exact-name presence alone is insufficient.

### R2-C-02 — `crew_card_create` documentation claims a constraint contract that the handler silently discards

**Evidence:**

- `crew-no-spec/SKILL.md:62-74` instructs coordinators to pass `proof_mode` and a Zero-Checkout `constraints` string to `crew_card_create`.
- `crew-no-spec/SKILL.md:111` repeats `proof_mode` and `constraints` as arguments.
- `crew/SKILL.md:291` describes a shortened required-argument list but elsewhere mandates that codebase card constraints carry Zero-Checkout.
- `CREW_CARD_CREATE_SCHEMA` at `native_tools.py:50-119` declares neither `proof_mode` nor `constraints`.
- The handler reads `proof_mode` at `native_tools.py:278-279` but never reads `constraints`; its contract dictionary at `native_tools.py:262-286` omits the field entirely.

A direct dry-run probe used a unique constraints marker and read back the generated card body:

```text
CARD_CREATE_STATUS ok
CONSTRAINT_PRESENT False
```

The generated card body contained no `Constraints:` line despite the caller providing `constraints="ZERO-CHECKOUT-MUST-SURVIVE"`.

**Impact:** The canonical fast-track worker example can silently create a code card without the Zero-Checkout constraint it claims to enforce. This is an operational safety defect and contradicts `crew-no-spec/SKILL.md:73`, `crew/SKILL.md:88-90,111-112,314-315`, and the Zero-Checkout mandate.

**Required correction:** Either add `constraints` to `CREW_CARD_CREATE_SCHEMA` and propagate it into the contract passed to `open_card`, or stop recommending `crew_card_create` for constraint-bearing cards and use a path that preserves the field. Add a regression test proving a unique constraint survives into the dry-run/opened card body. Declare every accepted field, including `proof_mode`, in the schema.

## WARNING finding

### R2-W-01 — New documentation tests prove name presence, not correctness or role appropriateness

**Evidence:**

`tests/test_crew_versions.py:39-46` passes when each manifest tool name appears anywhere in any shipped skill. It does not verify argument names, required fields, allowed roles, mutability/safety text, result states, lifecycle actions, or installed-tree parity. That weak test passes while R2-C-01 and R2-C-02 remain reproducible.

The force-loaded-skill test at `tests/test_crew_versions.py:48-61` also uses a hard-coded allowlist rather than resolving through the actual installed skill registry, so it proves the current names are allowlisted—not that an intended target profile can load them.

**Required correction:** Replace string-presence checks with schema-backed documentation contract tests and verify referenced skills against a real package/installed registry source. Keep the current tests as smoke checks if useful, but do not treat them as the acceptance gate.

## INFO findings

### R2-I-01 — Original version, missing-skill, taxonomy, and public-catalog defects are resolved

All six skill versions match `plugin.yaml` at `0.9.13`; the obsolete `completed-handoff-review` reference is removed; all five verification modes are described; and README/REFERENCE now enumerate the 17-tool catalog.

### R2-I-02 — Repository and installed skill trees are byte-identical

Fresh SHA-256 comparison returned `PARITY_ALL True` for all six pairs. This means the remaining defects are deployed consistently in both trees.

### R2-I-03 — Focused implementation suites are green

Command:

```text
python -m unittest -v tests.test_native_tools tests.test_extended_tools tests.test_crew_versions tests.test_crew_run_launcher
```

Result:

```text
Ran 76 tests in 5.712s
OK (skipped=2)
```

The two skips are POSIX-only launcher execution tests on Windows. The green suite does not supersede the direct schema/documentation mismatches above because those examples are not covered by current tests.

## Zero-Checkout boundary gate

Fresh branch checks returned:

```text
REPO=O:/workspaces BRANCH=main
REPO=O:/workspaces/oss/crew BRANCH=main
REPO=O:/workspaces/oss/hermes-agent BRANCH=main
REPO=O:/workspaces/oss/hermes-nerve BRANCH=main
```

All listed non-primary Crew and Hermes branches remain in registered worktrees under `O:/workspaces/.worktrees/`. This gate passes and is independent of the documentation verdict.

## Card proof evidence

The immutable card proof was executed through the Crew verdict runner after this artifact was written:

```text
proof command: test -s "oss/crew/reviews/findings-crew-skills-docs-r2.md"
rc=1
raw output:
(no output)
```

This failure is a card-contract path defect, not a missing artifact: the runner selects `Lands at: oss/crew` as its working directory, then evaluates a workspace-root-relative path beginning with `oss/crew/`, effectively looking below `oss/crew/oss/crew/...`. The actual requested artifact exists at `O:/workspaces/oss/crew/reviews/findings-crew-skills-docs-r2.md`. Because the proof command was owner-snapshotted and immutable, Reviewer did not rewrite or bypass it; the card cannot receive a proof PASS until the coordinator issues a corrected proof snapshot/card.

## Final verdict

# REJECTED

The remediation clears six of the eight original acceptance criteria, but criterion 1—the core accuracy requirement—still fails. The new guidance contains several non-callable argument shapes, and the recommended fast-track creation path silently drops the required Zero-Checkout constraint. Correct the schema/documentation contract and strengthen tests from name presence to invocation validity before approval. Independently, correct the review card's proof/landing path contract so its immutable proof can execute from the selected working directory.
# Independent Review — Crew Skills Documentation and Tool Guidance

**Card:** `t_b1e2465d`  
**Reviewer:** `reviewer`  
**Review date:** 2026-10-19  
**Final verdict:** **REJECTED**

The Crew implementation exposes 17 distinct tools, but the shipped and installed skill sets provide exact-name operational guidance for only 6. Eleven tools—including every extended workflow/workspace/intelligence tool—are absent from every Crew skill. Additional blocking inconsistencies affect verification modes, skill loading, and release-version parity. The documentation does not currently meet the requirement that all newly added tools be documented and guide agents to use them correctly.

## Findings summary

| Severity | Count | IDs |
|---|---:|---|
| CRITICAL | 4 | C-01 through C-04 |
| WARNING | 2 | W-01 through W-02 |
| INFO | 2 | I-01 through I-02 |

## Scope

### Reviewed

- All 6 repository skills under `oss/crew/skills/*/SKILL.md`.
- All 6 installed skills under `_config/agent4070/hermes/skills/crew/*/SKILL.md`.
- The 17-tool manifest and registration sources:
  - `oss/crew/plugin.yaml`
  - `oss/crew/native_tools.py`
  - `oss/crew/scripts/crew_tools.py`
  - `oss/crew/__init__.py`
- Applicable OpenSpec sources of truth:
  - `openspec/specs/native-crew-tools/spec.md`
  - `openspec/specs/crew-extended-tools/spec.md`
  - `openspec/specs/crew-skills-regulations/spec.md`
  - `openspec/specs/crew-role-prompts/spec.md`
  - `openspec/specs/crew-runtime-events/spec.md`
- Relevant architecture/design documents for the native, extended, and skills-regulation changes.
- Public tool summaries in `README.md` and `REFERENCE.md`.
- Focused schema, registration, extended-tool, version, and launcher tests.

### Not reviewed

- The full Crew regression suite outside the four focused modules named under Test evidence.
- Live webhook delivery to an external endpoint; this audit reviewed its contract, implementation documentation, and focused tests only.
- Runtime behavior of tools not exposed to this reviewer session. The source schemas, manifest, registration tests, and OpenSpec contracts were used instead.
- Unrelated dashboard, notification, coordinator, and installer behavior.

## Evidence baseline

### Catalog reconciliation

The catalog consists of 17 distinct tools:

- 5 core tools from `native_tools.py:539-545`.
- 8 extended tools from `native_tools.py:1196-1205`.
- 4 additional non-overlapping script tools from `scripts/crew_tools.py:136-137`.
- The exact 17-name set is declared in `plugin.yaml:26-43` and asserted by `tests/test_extended_tools.py:93-101,182-209`.

### Skill-tree parity

A byte-level comparison found the repository and installed skill trees equivalent for all shared files. Matching SHA-256 prefixes were observed for each pair. This establishes deployment parity, but also means every defect below is present in both locations.

### Exact-name tool coverage in skills

| Tool | Exact-name guidance in a Crew skill | Result |
|---|---|---|
| `crew_card_create` | none | MISSING |
| `crew_diagnose` | `crew-diagnose/SKILL.md:18-32` | covered |
| `crew_verdict` | worker/content/verifier role skills | covered |
| `crew_status` | none | MISSING |
| `crew_event_subscribe` | none | MISSING |
| `crew_stop_card` | none | MISSING |
| `crew_review_handoff` | none | MISSING |
| `crew_request_changes` | none | MISSING |
| `crew_plan_split` | none | MISSING |
| `crew_worktree_create` | none | MISSING |
| `crew_worktree_cleanup` | none | MISSING |
| `crew_flow_graph` | none | MISSING |
| `crew_lesson_record` | none | MISSING |
| `crew_progress` | `crew-verifier/SKILL.md:40-41` | covered |
| `crew_proof_check` | `crew/SKILL.md:244-257` | covered |
| `crew_lesson` | coordinator and role skills | covered |
| `crew_plan` | `crew/SKILL.md:282-284` | covered |

**Coverage:** 6/17 documented by exact operational tool name; **11/17 missing**. Both skill trees have the same result.

## CRITICAL findings

### C-01 — Eleven of seventeen registered tools have no skill guidance

**Spec references:**

- `openspec/specs/native-crew-tools/spec.md:6-60`
- `openspec/specs/crew-extended-tools/spec.md:6-121`
- `openspec/specs/crew-runtime-events/spec.md:6-65`

**Evidence:**

- Registration and manifest sources enumerate all 17 tools (`plugin.yaml:26-43`, `native_tools.py:539-545,1196-1205`, `scripts/crew_tools.py:136-137`).
- Exact-name scan across both requested skill trees found no occurrence of the 11 tools marked MISSING in the matrix above.
- The absent set includes all 8 extended tools and 3 core tools (`crew_card_create`, `crew_status`, and `crew_event_subscribe`).

**Impact:** Agents cannot discover from the role skills when to create a guarded Crew card, park one card, hand work to review, return it for changes, split a plan, manage an isolated worktree, inspect a flow graph, record/show a lesson, query status, or subscribe to lifecycle events. Tool schemas alone do not provide lifecycle sequencing or role boundaries.

**Required resolution:** Add a complete role/tool decision matrix and concise invocation guidance for all 17 tools. Each entry must state: who may call it, when it replaces a generic Kanban or shell path, required arguments, mutability/safety behavior, expected result states, and the next lifecycle action. Add a test that fails when any `plugin.yaml` tool is absent from all shipped role skills.

### C-02 — Verification modes are internally inconsistent across shipped skills

**Spec references:**

- `openspec/specs/crew-role-prompts/spec.md:41-50`
- `contracts.py:64-84` (`proof`, `independent`, `agent`, `dual`, `closeout`)
- `native_tools.py:833-843` (`crew_review_handoff` accepts `independent`, `agent`, and `dual`)

**Evidence:**

- `crew-no-spec/SKILL.md:40-43,76-89` explicitly creates standalone reviewer cards with `Verify: agent`.
- `crew-verifier/SKILL.md:9-10` says it is used only for `independent` or `dual` and says a `proof` card never reaches it; it never defines the `agent` path.
- `crew-role-worker/SKILL.md:32-40` documents only `proof`, `independent`, and `closeout`, while the formal role specification in `contracts.py:728-731` includes `dual` in the review path.
- `crew-role-content/SKILL.md:25-28` likewise omits `agent` and `dual` completion behavior.

**Impact:** A verifier assigned a valid `Verify: agent` card receives a skill whose applicability statement excludes that card. Writers and content agents do not have a complete, authoritative completion rule for every mode accepted by the contract model. This can produce wrong terminal actions or skipped proof/verdict steps.

**Required resolution:** Define one canonical mode/state table and use it in all role skills. At minimum: explain whether `agent` is a standalone reviewer-owned card, whether `dual` is a same-card mode or a two-card pipeline, who runs `crew_verdict`, and which terminal action (`crew_review_handoff`, completion, or request changes) applies to each role/mode combination.

### C-03 — `crew-no-spec` force-loads a nonexistent skill

**Spec reference:** `openspec/specs/crew-skills-regulations/spec.md:45-52` (deterministic Turn-1 dispatch).

**Evidence:**

- `crew-no-spec/SKILL.md:26` requires `["completed-handoff-review", "openspec-verifier"]` for review work.
- Its dual-review example repeats the nonexistent name at `crew-no-spec/SKILL.md:75`.
- A bounded workspace filename search returned zero files named or containing a skill directory `completed-handoff-review`.
- The current card was dispatched with `crew-verifier`, demonstrating the available Crew review skill has a different name.

**Impact:** The documented card template can request a skill that the target reviewer cannot load. Depending on dispatcher validation, the card may fail creation, dispatch without the intended review procedure, or create false confidence that a review protocol was loaded.

**Required resolution:** Replace the nonexistent skill with the actual installed review skill(s), and add an automated check that every force-loaded skill named by shipped Crew documentation resolves through the installed skill registry.

### C-04 — Shipped and installed `crew-no-spec` versions are stale, and the focused version gate fails

**Spec references:**

- `openspec/specs/crew-skills-regulations/spec.md:69-77`
- `tests/test_crew_versions.py:21-29`

**Evidence:**

- Package version: `plugin.yaml:2` is `0.9.13`.
- Repository and installed copies of `crew-no-spec/SKILL.md:4` are `0.9.12`.
- The main regulation spec itself is stale at line 76, still naming `0.9.12` as the expected plugin version.
- Focused execution result:

```text
Ran 74 tests in 7.192s
FAILED (failures=1, skipped=2)
AssertionError: '0.9.13' != '0.9.12' : crew-no-spec/SKILL.md version
```

**Impact:** Release identity and skill drift detection are broken for a workflow-critical intake skill. The installed copy repeats the mismatch, so this is not repository-only drift.

**Required resolution:** Synchronize all shipped and installed skill versions to `plugin.yaml`, update the stale normative spec text so it does not hard-code an obsolete release, and keep the version test mandatory.

## WARNING findings

### W-01 — Cross-platform skill guidance still contains the command pattern the regulation change forbids

**Spec references:**

- `openspec/specs/crew-skills-regulations/spec.md:22-35`
- `openspec/changes/archive/2026-10-18-crew-skills-regulations/design.md:39-43`

**Evidence:**

- `crew-verifier/SKILL.md:14` presents `sh "$HERMES_HOME/plugins/crew/scripts/crew-run.sh" ...` as the proof-script form.
- `crew/SKILL.md:193-198,269-271` also shows `sh "$HERMES_HOME/..."` command forms.
- The regulation spec explicitly says instructions shall avoid brittle nested subshell patterns of that form on Windows/MSYS.

**Impact:** The docs retain the exact quoting/path pattern the change was intended to eliminate, so agents can reproduce the Windows argument-conversion failure mode despite the regulation.

**Required resolution:** Standardize one tested, cross-platform invocation pattern and reference it consistently. If the shell launcher must remain as a fallback, document its supported shell and argument boundary precisely instead of presenting it as a generic form.

### W-02 — Public architecture/reference documentation still advertises only six tools

**Evidence:**

- `README.md:168-174` states that the plugin registers six tools and lists only the legacy/script-facing set.
- `REFERENCE.md:218-223` likewise lists six tools under `scripts/crew_tools.py`.
- `plugin.yaml:26-43` and focused registration tests establish 17 distinct tools.

**Impact:** Even if skill guidance is repaired, users and maintainers will still receive a materially incomplete tool inventory from the public documentation and architecture reference.

**Required resolution:** Update both documents with the canonical 17-tool inventory grouped into Core, Pipeline, Workspace, Intelligence, and proof/progress helpers. Point each role to its applicable subset.

## INFO findings

### I-01 — Repository and installed skill trees are synchronized

All six corresponding skill files produced matching content hashes across `oss/crew/skills` and `_config/agent4070/hermes/skills/crew`. Remediation must update both through the supported installer/synchronization path; fixing only one tree will reintroduce drift.

### I-02 — Live Crew tools were not exposed to this reviewer session

`tool_search("crew")` returned no Crew tool matches and `tool_describe` could not resolve `crew_verdict`, `crew_progress`, or `crew_lesson`. Therefore this audit validated the 17-tool catalog against source schemas, manifest declarations, OpenSpec contracts, and focused registration tests rather than live tool calls. This does not change the documentation verdict, but runtime toolset exposure should be checked separately.

## Test evidence

Command:

```text
python -m unittest -v tests.test_native_tools tests.test_extended_tools tests.test_crew_versions tests.test_crew_run_launcher
```

Result:

```text
Ran 74 tests in 7.192s
FAILED (failures=1, skipped=2)
```

- Core and extended schema/handler/registration tests passed.
- The single failure is the real package/skill version mismatch in C-04.
- Two launcher execution tests were skipped because they are POSIX-only on this Windows host; the static no-`python3` skill check passed.

## Remediation acceptance criteria

A re-review may be approved only when all of the following are true:

1. Every one of the 17 manifest tools has accurate, role-appropriate skill guidance, with no ambiguous duplicate path.
2. Verification mode semantics are identical across `contracts.py`, coordinator intake, writer/content skills, and verifier skill.
3. Every skill name used in a card template resolves in the installed skill registry.
4. All shipped and installed skill versions match `plugin.yaml`.
5. The cross-platform proof/script examples conform to the regulation spec.
6. `README.md` and `REFERENCE.md` report the actual 17-tool catalog.
7. Focused version, launcher, native-tool, and extended-tool tests pass with exit code 0.
8. Repository and installed copies are verified byte-identical after supported synchronization.

## Final verdict

# REJECTED

The tool implementations and focused registration tests are largely healthy, but the documentation gate fails: 11 of 17 tools are not documented in either requested skill tree, valid verification modes conflict across roles, a documented review template references a missing skill, and the release-version gate is red. These are operational correctness defects, not cosmetic omissions.

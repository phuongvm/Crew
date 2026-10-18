# Independent Review Findings v1 — Standardized Crew Role Prompts & Contracts

## Verdict

**REJECTED**

Independent Phase 4 verification for OpenSpec change `crew-role-prompts` in `oss/crew` was executed. The core parser, enum alias coercions, Zero-Checkout prompt invariants, standard library boundaries, task proof commands, and the 132 unit tests pass. However, a rigorous specification audit against `specs/crew-role-prompts/spec.md` identified **2 CRITICAL specification compliance defects**:

1. **C-01**: `ContractGaps` is explicitly required as a structured domain model by Requirement 1 (`The system SHALL provide structured contract models (ContractCard, ContractGaps, Role, VerifyMode, ProofMode)`), but is not defined or exported in `contracts.py` (`ImportError` on import).
2. **C-02**: Requirement 3 Scenario (`Round-trip Canonical Markdown rendering`) mandates that a `ContractCard` can be reconstructed via `ContractCard.from_markdown()`, but `from_markdown` is missing on `ContractCard` (`AttributeError` on invocation; only module-level `parse_markdown_card` was implemented).

These defects must be corrected by the implementation role before this change can be approved and archived.

---

## Review Target & Context

- **Repository**: `O:/workspaces/oss/crew`
- **Change**: `crew-role-prompts`
- **Role**: Independent Verifier / Reviewer (`@reviewer` / `openspec-verifier`)
- **Review Round**: 1 (Cold artifact inspection, AST dependency analysis, and independent empirical execution)
- **Workflow Schema**: `spec-driven`
- **Reviewed Specification Artifacts**:
  - `openspec/changes/crew-role-prompts/proposal.md`
  - `openspec/changes/crew-role-prompts/design.md`
  - `openspec/changes/crew-role-prompts/specs/crew-role-prompts/spec.md`
  - `openspec/changes/crew-role-prompts/tasks.md`
- **Reviewed Source & Adapter Modules**:
  - `contracts.py`
  - `scripts/crew_card.py`
  - `skills/crew/SKILL.md`
- **Reviewed Test Suites**:
  - `tests/test_role_contracts.py`
  - `tests/test_crew_card.py`

---

## Invariant & Security Boundary Audit

- **Production Branch Invariant**: Clean on `main` (`git -C "O:/workspaces/oss/crew" branch --show-current` confirmed `main`).
- **Zero-Checkout Enforcement**: Zero `git checkout <branch>` or `git switch <branch>` commands were executed in `O:/workspaces/oss/crew`.
- **Reviewer Non-Mutation Principle**: In accordance with the `crew-verifier` protocol, Reviewer did not alter, patch, or self-repair the implementation code or test files under evaluation.
- **Inference Cost Boundary**: All model reasoning routed through `custom:ai-router`.

---

## Findings Summary

| Severity | Count | Status | Notes |
|---|---:|---|---|
| **CRITICAL** | 2 | Open | Blockers: Missing `ContractGaps` export (C-01) and missing `ContractCard.from_markdown` classmethod (C-02) |
| **WARNING** | 0 | None found | No regressions or parsing drift detected |
| **SUGGESTION** | 1 | Open | S-01: Add `to_markdown()` method alias on `ContractCard` matching `to_dict()`/`to_json()` |
| **INFO** | 5 | Verified | Verified tolerant parsing, enum alias coercion, Zero-Checkout prompt invariants, standard library isolation, and test suite pass rate |

---

## Detailed Findings

### C-01 — Missing `ContractGaps` Model in `contracts.py`

- **Severity**: **CRITICAL**
- **Spec Reference**: `openspec/changes/crew-role-prompts/specs/crew-role-prompts/spec.md:3-5`
  > "Requirement: Structured Contract Representation and Validation: The system SHALL provide structured contract models (`ContractCard`, `ContractGaps`, `Role`, `VerifyMode`, `ProofMode`) to represent and validate Crew task cards deterministically."
- **Proposal & Design References**:
  - `proposal.md:9`: "Implement formal domain models (`Role`, `VerifyMode`, `ProofMode`, `ContractCard`, `ContractGaps`)..."
  - `design.md:14`: "Provide typed domain models (`ContractCard`, `Role`, `VerifyMode`, `ProofMode`, `ContractGaps`) using Python standard library constructs..."
- **Code Reference**: `contracts.py:1-480`
- **Evidence**:
  ```bash
  python -c "from contracts import ContractGaps"
  ```
  Output:
  ```text
  Traceback (most recent call last):
    File "<string>", line 1, in <module>
  ImportError: cannot import name 'ContractGaps' from 'contracts' (O:\workspaces\oss\crew\contracts.py)
  ```
- **Cause**: While `validate_contract(c)` was implemented returning `List[str]`, the declared model `ContractGaps` was never defined, aliased, or exported in `contracts.py`.
- **Impact**: Code, external tool integrations, or type annotations importing `ContractGaps` as specified in the change contract fail at runtime with `ImportError`.
- **Required Correction**:
  1. Define and export `ContractGaps` in `contracts.py` (e.g. `ContractGaps = List[str]` or a structured dataclass/list subclass representing the ordered gap list).
  2. Update return type annotations on `validate_contract` and `ContractCard.validate_gaps` to reference `ContractGaps`.
  3. Add test coverage in `tests/test_role_contracts.py` asserting `from contracts import ContractGaps` and verifying gap container behavior.

---

### C-02 — Missing `from_markdown` Classmethod on `ContractCard`

- **Severity**: **CRITICAL**
- **Spec Reference**: `openspec/changes/crew-role-prompts/specs/crew-role-prompts/spec.md:34-36`
  > "Scenario: Round-trip Canonical Markdown rendering:
  > - **WHEN** a `ContractCard` is rendered into canonical Markdown via `render()` and parsed back via `from_markdown()`
  > - **THEN** all contract fields (role, goal, artifact, lands, for, done when, proof command, budget, verify) match the source card."
- **Code Reference**: `contracts.py:175-275` (`ContractCard` class definition)
- **Evidence**:
  ```bash
  python -c "import contracts; contracts.ContractCard.from_markdown('Role: worker\nGOAL: g\nDone when: d\nproof command: p\n')"
  ```
  Output:
  ```text
  Traceback (most recent call last):
    File "<string>", line 1, in <module>
  AttributeError: type object 'ContractCard' has no attribute 'from_markdown'
  ```
- **Cause**: `ContractCard` implements `to_dict()`, `from_dict()`, `to_json()`, `from_json()`, and `render()`, but the specified deserialization classmethod `from_markdown()` was not defined on `ContractCard`. Only the standalone module function `parse_markdown_card(body: str)` was provided, and the unit test `test_rendering_and_parsing_round_trip` in `tests/test_role_contracts.py:377` tested `parse_markdown_card` directly rather than invoking the classmethod required by the specification.
- **Impact**: Any consumer expecting object-oriented round-trip deserialization via `ContractCard.from_markdown(...)` crashes with `AttributeError`.
- **Required Correction**:
  1. Add `@classmethod def from_markdown(cls, body: str) -> ContractCard: return parse_markdown_card(body)` to `ContractCard` in `contracts.py`.
  2. Add unit test assertions in `tests/test_role_contracts.py` exercising `ContractCard.from_markdown(rendered_md)`.

---

### S-01 — Add `to_markdown()` Alias on `ContractCard`

- **Severity**: **SUGGESTION**
- **Reference**: `openspec/changes/crew-role-prompts/design.md:16` and `contracts.py:271`
- **Observation**: `ContractCard` has `to_dict()` and `to_json()`, but uses `render()` for canonical Markdown generation.
- **Recommendation**: Provide `to_markdown(self, ...)` as a convenience method forwarding to `self.render(...)` so that method names across serialization formats (`to_dict`, `to_json`, `to_markdown`) are symmetric with `from_dict`, `from_json`, and `from_markdown`.

---

## Verified Capabilities & Empirical Evidence

### 1. Tolerant Markdown Parser
- **Requirement**: Parser extracts all contract fields when keys are decorated (`**Role:**` or `**Role**:`) and captures multiline continuation blocks (`Done when:`, `Constraints:`, `Inputs:`, `GOAL:`) without truncation.
- **Verification Evidence**:
  ```bash
  python -c "import contracts
  card_a = contracts.parse_markdown_card('**Role:** worker\n**GOAL:** test A\nDone when:\n- line 1\n- line 2\nproof command: true\n')
  assert card_a.role == 'worker'
  assert 'line 2' in card_a.done_when

  card_b = contracts.parse_markdown_card('**Role**: worker\n**GOAL**: test B\nDone when:\n- bullet 1\n- bullet 2\nproof command: true\n')
  assert card_b.role == 'worker'
  assert 'bullet 2' in card_b.done_when
  print('PASS')
  "
  ```
  Result: `PASS`
- **Adapter Verification (`scripts/crew_card.py:field`)**:
  ```bash
  python -c "import sys; sys.path.insert(0, 'scripts'); import crew_card
  assert crew_card.field('**Role:** worker', 'role') == 'worker'
  assert crew_card.field('**Role**: worker', 'role') == 'worker'
  print('PASS')
  "
  ```
  Result: `PASS`

### 2. Typed Enums and Alias Coercions
- **Requirement**: `Role`, `VerifyMode`, `ProofMode` correctly coerce common aliases.
- **Verification Evidence**:
  - `Role.from_str`: `coder`, `engineer`, `dev` -> `Role.WORKER`; `designer`, `writer`, `copywriter` -> `Role.CONTENT`; `qa`, `auditor`, `tester` -> `Role.VERIFIER`; `leader`, `pm`, `intake` -> `Role.COORDINATOR`.
  - `VerifyMode.from_str`: Case-insensitive coercion for `proof`, `independent`, `agent`, `dual`, `closeout`.
  - `ProofMode.from_str`: Default to `SAFE`, coerce `brave` -> `ProofMode.BRAVE`.
  - Result: All coercions verified with 100% pass rate.

### 3. Zero-Checkout Invariant Codification
- **Requirement**: Zero-Checkout invariant codified in `RoleSpecification` and system prompt generation.
- **Verification Evidence**:
  ```bash
  python -c "import contracts
  w = contracts.get_role_specification('worker').render_system_prompt()
  assert 'Zero-Checkout' in w and 'git checkout' in w and '.worktrees' in w
  v = contracts.get_role_specification('verifier').render_system_prompt()
  assert 'Zero-Checkout' in v and 'Read-Only Verifier' in v
  print('PASS')
  "
  ```
  Result: `PASS`

### 4. Zero External Dependencies (Standard Library Only)
- **Requirement**: `contracts.py` must rely strictly on Python standard library modules.
- **Verification Evidence** (AST Inspection):
  - Imported modules: `['__future__', 'dataclasses', 'enum', 'json', 'os', 're', 'sys', 'typing']`.
  - Comparison against `sys.stdlib_module_names` confirmed 0 non-standard library dependencies.

### 5. Task Checklist Proof Command Execution
All 11 tasks in `openspec/changes/crew-role-prompts/tasks.md` executed cleanly:
- 1.1: `hasattr(contracts, 'ContractCard') and hasattr(contracts, 'Role')` -> `PASS 1.1`
- 1.2: `parse_markdown_card` bold headers & multiline blocks -> `PASS 1.2`
- 1.3: `validate_contract({})` missing field detection -> `PASS 1.3`
- 1.4: Bidirectional dict roundtrip -> `PASS 1.4`
- 2.1: `ROLE_SPECIFICATIONS` for worker, content, verifier, coordinator, diagnose -> `PASS 2.1`
- 2.2: `render_system_prompt()` contains Zero-Checkout and `.worktrees` -> `PASS 2.2`
- 3.1: `crew_card.field('**Role:** worker', 'role') == 'worker'` -> `PASS 3.1`
- 3.2: `contracts.py` referenced in `skills/crew/SKILL.md` -> `PASS 3.2`
- 4.1: `tests/test_role_contracts.py` file exists -> `PASS 4.1`
- 4.2: Unit test suite execution -> `27 passed in 0.04s`
- 4.3: OpenSpec strict validation -> `PASS 4.3` (`Change 'crew-role-prompts' is valid`)

### 6. Full Unit Test Suite Execution
- **Command**: `env -u HERMES_DELEGATED_CHILD_CONTEXT pytest tests/test_role_contracts.py tests/test_crew_card.py -v`
- **Output**:
  ```text
  ============================= test session starts =============================
  collected 132 items

  tests/test_role_contracts.py ...........................                 [ 20%]
  tests/test_crew_card.py ................................................ [ 56%]
  ..........................................................               [100%]

  ================== 132 passed, 28 subtests passed in 11.40s ===================
  ```
- **Result**: 132 passed, 0 failed, 100% pass rate.

---

## Required Remediation for Round 2

To achieve an `APPROVED` verdict on re-review:

1. **Fix C-01 (`ContractGaps`)**:
   - In `contracts.py`, define and export `ContractGaps` (e.g. `ContractGaps = List[str]`).
   - Annotate `validate_contract` and `ContractCard.validate_gaps` return types as `ContractGaps`.
   - In `tests/test_role_contracts.py`, import `ContractGaps` and assert its type/behavior.
2. **Fix C-02 (`ContractCard.from_markdown`)**:
   - In `contracts.py`, add `@classmethod def from_markdown(cls, body: str) -> ContractCard: return parse_markdown_card(body)` to `ContractCard`.
   - In `tests/test_role_contracts.py`, update `test_rendering_and_parsing_round_trip` to call `ContractCard.from_markdown(rendered_md)`.
3. **Optional S-01 (`ContractCard.to_markdown`)**:
   - Add `def to_markdown(...) -> str: return self.render(...)` for serialization API symmetry.
4. **Re-run tests**:
   - Ensure all tests in `tests/test_role_contracts.py` and `tests/test_crew_card.py` pass.
   - Run `openspec validate crew-role-prompts --strict`.
5. **Dispatch Round 2 Review**:
   - Re-invoke independent verification for final clearance.

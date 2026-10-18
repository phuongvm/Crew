# Exploration: Standardizing Crew Role Prompts, System Personas, and Structured Contract Models

- **Date:** 2026-10-18
- **Author:** AI Agent (@coder)
- **Target Project:** `oss/crew` (`O:/workspaces/oss/crew`)
- **Status:** Phase 1 Exploration Complete (Awaiting Phase 2 Approval)
- **Files Inspected:**
  - `skills/crew/SKILL.md` (Coordinator Intake — Track A OpenSpec Governance)
  - `skills/crew-no-spec/SKILL.md` (Fast-Track Coordinator Intake — Track B)
  - `skills/crew-role-worker/SKILL.md` (Worker Persona & Execution Rules)
  - `skills/crew-role-content/SKILL.md` (Content Creator Persona & Rendering Rules)
  - `skills/crew-verifier/SKILL.md` (Verifier Persona & Verification Rules)
  - `skills/crew-diagnose/SKILL.md` (Read-only Diagnostician Persona)
  - `scripts/crew_card.py` (Card Lifecycle, Contract Parser, Contract Gaps, Body Renderer)
  - `__init__.py` (Plugin Hooks, `_create_guard`, `_close_guard`)
  - `tests/test_crew_card.py` (Current Contract & Card Tests)

---

## 1. Problem Statement & Root Cause Analysis

### 1.1 The Fragility of Loose Markdown Regex Parsing
In the current implementation (`scripts/crew_card.py`), Kanban card bodies serve as the serialized data layer between the coordinator, the kanban board database (`tasks.body`), dispatched worker sessions, verifiers, and automated background watchdog loops.
However, extraction of contract fields relies entirely on loose line-oriented regular expressions:

```python
def field(body, key):
    m = re.search(r"^\s*%s:\s*(.+)$" % re.escape(key), body or "", re.M | re.I)
    return m.group(1).strip() if m else None
```

This parsing model exhibits critical vulnerabilities in production:
1. **Markdown Formatting Variations**: When LLMs generate or modify card bodies, they frequently output formatting variations such as bold headers (`**Role:** worker`, `**GOAL:** ...`), bullet lists (`- GOAL: ...`), or italicized tags (`*Done when:* ...`). The regex `^\s*%s:\s*(.+)$` fails completely on `**Role:** worker`, returning `None`.
2. **Multiline Fields Truncation**:
   - Fields such as `Done when:`, `Constraints:`, `GOAL:`, and `Inputs:` frequently require multiple sentences or bullet points.
   - The regex `field()` only extracts the first line (`(.+)$` without matching continuation lines). Any subsequent explanation or acceptance criterion is dropped into `unparsed_lines()`, which appends it under `Intake notes:` at the bottom of the card or loses it during round-trip serialization.
   - `contract_inputs(body)` and `inputs_block(body)` attempt to parse `Inputs:` by scanning for `>` quoted lines immediately below it. If an LLM formats inputs as a bullet list (`- https://...`), indentation without `>` quotes, or places another field immediately after, the parser truncates or misparses the inputs.
3. **Dropped Lines and Gaps Detection Thrashing**:
   - In `prepare_contract()`, missing fields trigger a `ValueError("contract incomplete, missing: ...")`.
   - When a formatting glitch causes `field()` to miss `GOAL` or `Done when`, `contract_gaps()` treats it as an unfilled field, throwing an intake refusal (`_create_refusal`). This forces the coordinator into unnecessary `clarify` thrash loops or prompts the model to try bypasses (as observed in incident 2026-10-13 where removing `Role:` bypassed `_create_guard`).
4. **Role & Mode Drift**:
   - `crew_card.py` line 619:
     ```python
     if str(c.get("role") or "").strip().lower() not in WRITER_ROLES + ("verifier", "reviewer"):
         gaps.append("role (worker, content, or verifier)")
     ```
   - Meanwhile, tests in `tests/test_crew_card.py` still expected `role (worker or content)` (failing 26 tests in the test suite).
   - Verify modes expanded (`proof`, `independent`, `agent`, `dual`, `closeout`), but validation was scattered across disparate functions with inconsistent case folding, whitespace stripping, and fallback defaults.

### 1.2 Persona & Role Prompt Divergence Across Skills
Crew relies on discrete personas loaded per task:
- **Coordinator** (`crew`, `crew-no-spec`): Intake gating, contract formulation, routing, card decomposition, zero autonomous chat execution.
- **Worker** (`crew-role-worker`): Code, config, infra, test-driven implementation, zero branch switching in production checkouts (Zero-Checkout).
- **Content** (`crew-role-content`): Media, reports, documentation, rendered output validation.
- **Verifier** (`crew-verifier`): Independent judgment, read-only evaluation, proof script generation in `.crew/`, never fixing code.
- **Diagnostician** (`crew-diagnose`): Read-only state inspection, next concrete steps.

Currently, these personas are documented only as unstructured Markdown text in `.agents/skills` or `oss/crew/skills/`. There is no central, programmatic definition of role capabilities, tool permissions, contract expectations, and structured output formatting.

---

## 2. Architectural Solution: Formal Structured Contract Models (`contracts.py`)

To eliminate regex brittleness and achieve zero-defect card serialization, deserialization, and validation, we must formalize contracts using a dedicated, strongly-typed module: `O:/workspaces/oss/crew/contracts.py`.

### 2.1 Core Domain Entities & Schemas

1. **Enumerations**:
   - `Role`: `WORKER = "worker"`, `CONTENT = "content"`, `VERIFIER = "verifier"`, `COORDINATOR = "coordinator"`, `REVIEWER = "reviewer"`, `DIAGNOSE = "diagnose"`.
   - `VerifyMode`: `PROOF = "proof"`, `INDEPENDENT = "independent"`, `AGENT = "agent"`, `DUAL = "dual"`, `CLOSEOUT = "closeout"`.
   - `ProofMode`: `SAFE = "safe"`, `BRAVE = "brave"`.

2. **Data Model (`ContractCard`)**:
   - `title`: `str` (required, 1-120 chars)
   - `role`: `Role` (required)
   - `goal`: `str` (required)
   - `artifact`: `str` (required)
   - `lands`: `str` (required)
   - `audience`: `str` (required; corresponds to `For:`)
   - `done_when`: `str` (required)
   - `proof_cmd`: `str` (required unless `allow_no_proof=True` or `verify=closeout`)
   - `verify`: `VerifyMode` (default: auto-coerced from proof command and script type)
   - `proof_mode`: `ProofMode` (default: `SAFE`)
   - `proof_approved`: `bool` (default: `False`)
   - `budget`: `int` (default: role-based default, enforced >= `budget_floor`)
   - `constraints`: `str` (default: "none stated")
   - `inputs`: `List[str]` or normalized `str` (URLs, file paths, quoted specs)
   - `units`: `List[str]` (delimited sub-units for progress tracking)
   - `route`: `str` (e.g. `auto`, model/provider pin, or empty)
   - `coordinator`: `str` (session id of creator)
   - `origin`: `str` (chat origin `platform:chat_id`)
   - `unparsed_notes`: `List[str]` (preserves extraneous notes without corruption)

3. **Validation & Normalization Engine**:
   - **Tolerant Markdown Lexer/Parser**:
     - Strips markdown formatting (`**`, `*`, `__`, backticks) from keys: `**GOAL:**`, `*Role:*`, `### Goal:`.
     - Multiline block capture: captures indented lines and bullet points under `Done when:`, `Constraints:`, `Inputs:`, and `GOAL:` rather than truncating at newline.
     - Preserves `Inputs:` formatted with `>` quotes, bullet lists (`- `), or comma separation.
   - **Zero-Defect Gap Reporting**:
     - Returns ordered, typed gap messages (`ContractGaps`) consistent with both human inspection and automated tooling.
     - Enforces the Zero-Checkout invariant in constraints for code tasks.
     - Validates `.crew/` script path collisions across open cards.
   - **Bidirectional Serialization**:
     - `to_markdown() / render()`: Emits the clean, canonical Markdown card body expected by the kanban board and human operators.
     - `to_dict() / to_json()`: Serializes into structured JSON for programmatic APIs, test suites, and subagent handoffs.
     - `from_markdown(body)`: Deterministically parses any compliant or semi-compliant card body into a validated `ContractCard`.
     - `from_dict(data)`: Validates and instantiates `ContractCard` from JSON dictionaries.

4. **Role Persona & System Prompt Specifications**:
   - Programmatic registry of role personas (`RoleSpecification`):
     - `name`: Role name
     - `persona_title`: Header title
     - `core_mandate`: Primary operational purpose
     - `allowed_actions`: Strict action list
     - `prohibited_actions`: Strict prohibition list (e.g. Zero-Checkout, no autonomous chat execution for coordinator)
     - `output_contract`: Required output structure and finish protocol
   - Generation of standard prompt sections injected into skills or agent session bootloaders.

---

## 3. Backward Compatibility & Test Migration Plan

1. **Integration with `crew_card.py`**:
   - `crew_card.py` will import and delegate `parse_contract`, `render_body`, and `contract_gaps` to `contracts.py` (or provide seamless adapters), ensuring that existing CLI commands (`open`, `verdict`, `plan`, `show-contract`) continue to function identically.
2. **Alignment of Test Suite**:
   - Reconcile test expectations in `tests/test_crew_card.py` regarding role validation messages (`role (worker, content, or verifier)`).
   - Create comprehensive unit tests in `tests/test_role_contracts.py` testing:
     - Robust parsing of diverse markdown formatting (bold, italics, extra whitespace, bulleted multiline fields).
     - Missing field detection and gap ordering.
     - Token budget floor enforcement.
     - Proof script conflict detection.
     - JSON round-trip serialization and deserialization.
     - Role prompt generation and persona invariants.

---

## 4. OpenSpec Change Roadmap (`crew-role-prompts`)

Following OpenSpec Workflow Governance (Track A), the proposed change `crew-role-prompts` will deliver:
- `proposal.md`: Formal change motivation, capabilities, and impact.
- `specs/crew-role-prompts/spec.md`: Behavioral requirements for contract parsing, field extraction, validation rules, and role persona contracts.
- `design.md`: Architectural specification of `contracts.py`, parser grammar, and role prompt generator.
- `tasks.md`: Fine-grained task checklist with deterministic proof commands.

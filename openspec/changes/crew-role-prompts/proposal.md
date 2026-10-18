## Why

Crew role definitions and contract enforcement across coordinator, worker, verifier, content, and diagnostician profiles currently rely on loose, line-oriented regular expressions in `scripts/crew_card.py` (e.g. `re.search(r"^\s*%s:\s*(.+)$")`). LLM markdown formatting variations (such as bolded field names `**Role:**`, bullet lists, and indented multiline acceptance criteria) cause silent truncation, dropped lines, false contract gaps, intake refusal thrash loops, and audit crashes.

Furthermore, role prompt templates and system personas are maintained as disparate, unstructured prose across skill files rather than being backed by formal, machine-verifiable contract schemas. Standardizing role prompts, personas, and contract models with a structured, zero-dependency validation engine ensures robust, zero-defect contract lifecycle operations across the entire agent fleet.

## What Changes

- **Structured Contract Data Models (`contracts.py`)**: Implement formal domain models (`Role`, `VerifyMode`, `ProofMode`, `ContractCard`, `ContractGaps`) providing type validation, token budget floor enforcement, and proof script conflict detection.
- **Tolerant Bidirectional Serialization**: Implement a resilient Markdown parser capable of extracting contract fields despite Markdown decorations (`**`, `*`, `__`, backticks), properly capturing multiline blocks (`Done when:`, `Constraints:`, `Inputs:`), and serializing to/from canonical Markdown and structured JSON.
- **Formalized Role Prompt & Persona Specifications**: Establish declarative role definitions and system personas (`RoleSpecification`) with explicit allowed actions, prohibited actions (including the Zero-Checkout invariant), and structured output contracts.
- **Adapter Integration**: Integrate `contracts.py` with `scripts/crew_card.py` so existing CLI entrypoints seamlessly benefit from robust parsing without breaking backwards compatibility.
- **Comprehensive Contract Test Suite (`tests/test_role_contracts.py`)**: Deliver unit and property tests verifying serialization, deserialization, gap detection, and error resiliency.

## Capabilities

### New Capabilities
- `crew-role-prompts`: Structured contract validation models, tolerant bidirectional Markdown/JSON parsing, and standardized role prompt specifications for Crew agent roles.

### Modified Capabilities
<!-- No requirement changes to existing main specs -->

## Impact

- **Source Files**: Creates `contracts.py`, integrates with `scripts/crew_card.py`.
- **Role Skills**: Standardizes contract and persona conventions across `skills/crew`, `skills/crew-role-worker`, `skills/crew-role-content`, `skills/crew-verifier`, and `skills/crew-diagnose`.
- **Test Suite**: Adds `tests/test_role_contracts.py` and reconciles role gap expectations in `tests/test_crew_card.py`.
- **Dependencies**: Zero new third-party dependencies; uses Python standard library for universal compatibility across all Hermes runtime profiles.

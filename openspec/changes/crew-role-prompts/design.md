# Design: Standardized Crew Role Prompts, Personas, and Structured Contract Models

## Context

The Crew multi-agent orchestration engine (`oss/crew`) uses Kanban cards as the primary medium of exchange between coordinators, workers, verifiers, and human operators. When tasks are dispatched, card bodies carry contract stipulations including roles, budgets, proof commands, and acceptance criteria.

Previously, `scripts/crew_card.py` parsed card bodies using simple single-line regular expressions (`re.search(r"^\s*%s:\s*(.+)$")`). When LLMs decorated keys (e.g. `**Role:**`), structured `Inputs:` with bullets instead of blockquotes, or provided multiline `Done when:` criteria, fields were silently truncated, unparsed, or rejected as missing contract gaps.

This design introduces a formal, zero-dependency contract validation and parsing library (`contracts.py`) paired with declarative role prompt and persona definitions.

## Goals / Non-Goals

**Goals:**
- Provide typed domain models (`ContractCard`, `Role`, `VerifyMode`, `ProofMode`, `ContractGaps`) using Python standard library constructs (`dataclasses`, `enum`, `typing`).
- Implement a robust Markdown parser that tolerates formatting artifacts (bold/italicized keys, irregular spacing, continuation lines for multiline values).
- Support bidirectional lossless conversion between `ContractCard`, canonical Markdown bodies, and structured JSON.
- Provide declarative `RoleSpecification` models for all roles (`worker`, `content`, `verifier`, `coordinator`, `diagnose`) embedding core invariants (such as Zero-Checkout) and output contracts.
- Maintain backwards compatibility with existing `crew_card.py` interfaces and CLI tooling.

**Non-Goals:**
- Introducing external schema dependencies (such as heavy Pydantic or Marshmallow runtimes) that could fail in bare Python environments.
- Changing the storage schema of the Kanban SQLite database (`tasks` table).
- Modifying Hermes core plugin hook architecture.

## Decisions

### Decision 1: Standard Library Dataclasses Over External Pydantic Dependency
- **Choice**: Use Python `dataclasses` and standard library modules (`re`, `json`, `enum`, `typing`).
- **Rationale**: Crew scripts are executed across heterogeneous environments (Windows, Linux, isolated agent profiles, virtual environments). Requiring external packages like Pydantic in `crew_card.py` or `contracts.py` risks import errors in subagents or minimal runners where external packages are not installed.
- **Alternatives Considered**: Using Pydantic v2. While Pydantic is installed in the active environment, relying on it would break standard library-only guarantees documented in `crew_card.py`.

### Decision 2: Multi-Pass Block-Aware Markdown Parser
- **Choice**: Implement a block-aware lexer/parser that normalizes field keys by stripping Markdown styling (`**`, `*`, `__`, backticks) and aggregates continuation lines (indented or bulleted lines following a key header) into the active field until the next recognized contract key is encountered.
- **Rationale**: LLMs naturally output bullet lists under `Done when:`, `Constraints:`, and `Inputs:`. A single-line regex drops every line after the first. A block-aware parser retains full context.
- **Alternatives Considered**: Requiring strict YAML frontmatter. While clean, this breaks existing cards already on the board and contradicts established `/crew` chat conventions.

### Decision 3: Centralized Role Persona Registry
- **Choice**: Define a programmatic `RoleSpecification` catalog in `contracts.py` exposing persona prompts, core directives, tool permissions, and termination invariants for each role.
- **Rationale**: Prevents prompt drift between skill documentation (`SKILL.md`) and runtime card generation, ensuring all roles inherit critical governance invariants (e.g., Zero-Checkout, no autonomous chat execution).

## Risks / Trade-offs

- **[Risk] Formatting Ambiguities in Arbitrary Notes**: Freeform text after contract fields might be misidentified as continuation lines.
  - *Mitigation*: Maintain a strict set of known contract key signatures (`Role`, `Budget`, `Verify`, `GOAL`, `Artifact`, `Lands at`, `For`, `Constraints`, `Inputs`, `Done when`, `proof command`, etc.) and preserve any remaining text in `unparsed_notes` attached to the card.
- **[Risk] Backwards Compatibility with Existing Tests**: Older tests in `tests/test_crew_card.py` had assertions tied to exact legacy gap strings.
  - *Mitigation*: Ensure `contracts.py` gap strings align with `crew_card.py` expectations while providing explicit test suites in `tests/test_role_contracts.py`.

## Migration Plan

1. Create `contracts.py` with domain models, parser, serializer, and role specifications.
2. Add adapter bindings in `scripts/crew_card.py` to leverage `contracts.py` for parsing, rendering, and gap evaluation.
3. Author dedicated unit tests in `tests/test_role_contracts.py`.
4. Validate strict OpenSpec compliance and run the full test suite.

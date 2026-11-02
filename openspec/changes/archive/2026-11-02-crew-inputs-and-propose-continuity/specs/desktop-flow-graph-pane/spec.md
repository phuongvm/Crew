# Delta Specification: Hermes Desktop Flow Graph Extension Pane (`crew-inputs-and-propose-continuity`)

## ADDED Requirements

### Requirement 5: Crew Card Contract Tab Completeness
The Crew card detail view (`scripts/crew_graph.py` and `ui/src/components/Panel.tsx`) SHALL extract and render the complete contract specification—including `Inputs`, `Artifact`, `Lands at`, `Constraints`, `Done when`, and `Proof command`—directly inside the default `Contract` tab of the `Coordinator · card` node.

#### Scenario: Reviewing a card displays Inputs and contract targets in the Contract tab
- **GIVEN** a Crew card whose body contains `GOAL:`, `Artifact:`, `Lands at:`, `Constraints:`, `Inputs:`, `Done when:`, and `proof command:`
- **WHEN** `crew_graph.build_graph()` builds the `card:<id>` node and `Panel.tsx` renders the `Contract` tab (`m.kind === 'card'`, `tab === 'Contract'`)
- **THEN** `card_ev` MUST contain `inputs` (preserving multiline quoted `> ` entries via `crew_card.contract_inputs`) and `constraints` (single-line `body_field` extraction; a multi-line `Constraints:` block exposes only its first line)
- **AND** the `Contract` tab `<dl>` MUST render `Inputs`, `Artifact`, `Lands at`, `Constraints`, `Done when`, and `Proof command` as visible key-value rows without requiring the user to open `Details -> Raw fields`.

#### Scenario: Contract tab avoids duplicate 40+ character text with panel subtitle
- **GIVEN** a Crew card where `ev.goal` is identical to `card.card_title` (rendered in the `.ps` panel subtitle)
- **WHEN** `Panel.tsx` renders the `Contract` tab
- **THEN** `Goal` SHALL only be rendered as a separate `<dl>` row when the trimmed `ev.goal` differs from the trimmed `card.card_title`, preserving the panel's zero-duplicate-text invariant (`crew_panel_steps_proof.py`).

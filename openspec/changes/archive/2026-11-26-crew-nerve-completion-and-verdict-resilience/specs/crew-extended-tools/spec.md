# Delta Spec: Crew Extended Tools — Review-Lane Parking Support

## MODIFIED Requirements

### Requirement: Stop Card Tool
The Crew plugin SHALL register a native tool `crew_stop_card` that stops exactly one named crew card: it SHALL kill only that card's own worker processes, close the sessions they left open, and park the card for the owner (including `review`-lane cards via `reopen-review` followed by `block` or `schedule`), or archive it when `archive` is true. The tool MUST refuse cards that are not crew cards and MUST support a dry run that changes nothing.

#### Scenario: Agent parks a running crew card
- **WHEN** an agent calls `crew_stop_card` with the id of a `ready` or `running` crew card
- **THEN** the card MUST be blocked with the owner-stop reason so the dispatcher does not reclaim it
- **AND** the result MUST report `status: ok`, `stopped: true` and the before/after facts.

#### Scenario: Agent parks a review-lane crew card
- **WHEN** an agent calls `crew_stop_card` with the id of a `review` crew card
- **THEN** the tool MUST transition the card out of `review` via `reopen-review` and immediately park it with the owner-stop reason (`block` when landed in `ready`, or `schedule` when parent-gated in `todo`)
- **AND** the tool SHALL record prior review-lane provenance (`prior_status: "review"` and `prior_reviewer`) without archiving the card
- **AND** the result MUST report `status: ok`, `stopped: true`, and `facts.parked: true`.

#### Scenario: Agent archives a card
- **WHEN** an agent calls `crew_stop_card` with `archive: true`
- **THEN** the card MUST end in the `archived` state and the result MUST report `archived: true`.

#### Scenario: Non-crew card or dry run
- **WHEN** the named card has no crew `Coordinator:`/`Role:` line
- **THEN** the tool MUST return `status: refused` and leave the card untouched
- **AND** when `dry_run` is true for a crew card, the tool MUST return `status: dry_run` and make no board change.

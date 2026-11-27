# Spec: Crew Heal, Coordinator Stop-Guard, and Review-Lane Parking Resilience

## Purpose
Protects verifier quality judgements, Commander input/capability blocks, and owner `/crew-stop` directives from being overridden by automated stale-block healing or concurrent coordinator decision passes, and enables non-destructive parking of `review`-lane Crew cards.

## ADDED Requirements

### Requirement: Verifier-Lane Block Recognition Across All Verifier Modes
`crew_card` SHALL separate verifier-owned verdict/block modes (`VERIFIER_VERIFY_MODES = ("independent", "agent", "dual")`, `uses_verifier_lane(body)` used by `closer_profiles()` and `verifier_block()`) from two-stage review-handoff modes (`TWO_STAGE_VERIFY_MODES = ("independent", "dual")`, `uses_review_handoff(body)` used by `hand_to_writer()`, `repin_for_review()`, and `send_to_verifier()`), protecting verifier judgements without hijacking standalone `Verify: agent` cards onto a writer.

#### Scenario: Verifier block on Verify dual card stops stale-verify healing and hands retry back to writer
- **GIVEN** a blocked two-stage Crew card with `Verify: dual` whose newest run is a verifier run ending with `outcome == "blocked"`
- **WHEN** `crew_card.verifier_block(card_id)` and `crew_heal.heal_card(card)` execute
- **THEN** `verifier_block(card_id)` MUST return `{"run": <run_id>, "reason": <reason>}`
- **AND** `heal_stale_verify` MUST return `None` without executing `run_proof` or unblocking the card
- **AND** coordinator `resolve()` SHALL refuse `verify`/`close` decisions and route any retry via `hand_to_writer()` back to the writer profile.

#### Scenario: Verifier block on standalone Verify agent card stops stale-verify healing without reassigning to writer
- **GIVEN** a blocked standalone verifier Crew card with `Verify: agent` (`Role: verifier`, assigned to the verifier profile) whose newest run ended with `outcome == "blocked"`
- **WHEN** `crew_card.verifier_block(card_id)`, `crew_heal.heal_card(card)`, and `crew_card.hand_to_writer(card_id)` execute
- **THEN** `verifier_block(card_id)` MUST return `{"run": <run_id>, "reason": <reason>}`
- **AND** `heal_stale_verify` MUST return `None` without executing `run_proof` or unblocking the card
- **AND** `hand_to_writer(card_id)` SHALL remain a no-op (`{"reopened": False, "assigned": ""}`) so the standalone verifier card stays assigned to the verifier profile rather than being reassigned to `crew-worker`.

#### Scenario: Verify proof card retains writer-owned stale-block healing
- **GIVEN** a `Verify: proof` Crew card blocked with `block_kind="transient"` (or untyped `None`) whose proof command now exits `0`
- **WHEN** `crew_heal.heal_card(card)` executes
- **THEN** `verifier_block(card_id)` SHALL return `None`
- **AND** `heal_stale_verify` SHALL re-run the proof and lift the stale block.

### Requirement: Human and Capability Block Protection in Stale-Verify Healing
`crew_heal` SHALL refuse `stale_verify` healing on any blocked card whose effective `block_kind` (read from `card.get("block_kind")` with authoritative fallback to `tasks.block_kind` in `KANBAN_DB`) is `"needs_input"` or `"capability"`, preserving human-input and capability gates even when the card's proof command exits `0`.

#### Scenario: Card blocked with needs_input or capability is never auto-unblocked by stale_verify
- **GIVEN** a blocked Crew card with `block_kind="needs_input"` or `block_kind="capability"` whose owner-confirmed proof command exits `0`
- **WHEN** `crew_heal.heal_card(card)` or `crew_heal.heal_stale_verify(card, dry=False)` is called (even if the caller's `card` dict omits the `block_kind` key)
- **THEN** `crew_heal` MUST resolve the authoritative `block_kind` from `KANBAN_DB` and return `None` without calling `crew_safety.run_proof()` or `crew_card.lift_block()`
- **AND** the card status SHALL remain `"blocked"` with zero `unblocked` or `self_heal` events recorded.

#### Scenario: Card blocked with transient or untyped failure breaker still heals when proof passes
- **GIVEN** a non-verifier-blocked Crew card with `block_kind="transient"` or `block_kind=None` whose owner-confirmed proof command exits `0`
- **WHEN** `crew_heal.heal_card(card)` executes
- **THEN** `heal_stale_verify` SHALL execute `run_proof()`, observe `rc == 0`, and lift the block into `ready`.

### Requirement: Post-Resolve Owner-Stop Re-Check in Coordinator Dispatch
`crew_coordinator.handle_card()` SHALL re-read live card state from SQLite and re-verify owner-stop and terminal-state guards immediately after `resolve()` returns and immediately before calling `apply_decision()`, closing the concurrency race window where `/crew-stop` runs during an in-flight LLM decision turn.

#### Scenario: Owner runs /crew-stop while coordinator resolve() is in flight
- **GIVEN** a blocked Crew card undergoing `crew_coordinator.handle_card()` where `resolve()` is in flight and decides `{"decision": "retry", "fix": "..."}`
- **WHEN** `/crew-stop <card_id>` parks the card in SQLite (writing the owner-stop `blocked`/`scheduled` event or archiving via `--archive`) before `resolve()` returns
- **THEN** `handle_card()` MUST re-check live `get_card()`, `crew_card.parked_by_owner(ctx.db, card_id)`, and `stopped_after(ctx, card_id, newest["id"])` before calling `apply_decision()`
- **AND** `handle_card()` SHALL abort without calling `apply_decision()`, without unblocking the card, and without recording an applied `retry` decision
- **AND** the returned action SHALL be `"skip"` explaining that the card was stopped by the owner during resolution.

#### Scenario: Unstopped card proceeds normally after resolve()
- **GIVEN** a blocked Crew card that remains unparked and unarchived when `resolve()` returns a valid `retry` decision
- **WHEN** the post-resolve stop guard executes in `handle_card()`
- **THEN** `handle_card()` SHALL apply the decision via `apply_decision()` and record the `crew_decision` event as normal.

### Requirement: Non-Destructive Parking of Review-Lane Cards
`crew_stop.park_card()` SHALL park `status == "review"` Crew cards using only kernel-native Kanban verbs (`reopen-review` followed by `block` or `schedule`), handling both `ready` and parent-gated `todo` post-reopen landings while preserving prior review-lane provenance.

#### Scenario: Stopping a review-lane card with satisfied parents parks it in blocked
- **GIVEN** an open Crew card in `status == "review"` assigned to `reviewer` with all parent cards satisfied
- **WHEN** `crew_stop.stop_card()` invokes `park_card(card_id, dry=False)`
- **THEN** `park_card` MUST capture `prior_reviewer` and run `hermes kanban reopen-review <card_id>` (landing in `ready`)
- **AND** `park_card` MUST immediately run `hermes kanban block <card_id> --kind <park_kind> <owner_stop_reason>`
- **AND** `crew_stop` SHALL append a `crew_stop_parked` event recording `{"prior_status": "review", "prior_reviewer": "<reviewer>"}`
- **AND** `stop_card()` SHALL report `ok=True`, `parked=True`, exit code `0`, and `parked_by_owner(db, card_id) > 0`.

#### Scenario: Stopping a parent-gated review-lane card parks it in scheduled
- **GIVEN** an open Crew card in `status == "review"` that has an incomplete parent task so `reopen-review` lands the card in `todo`
- **WHEN** `crew_stop.park_card(card_id, dry=False)` executes
- **THEN** after `reopen-review` lands the card in `todo`, `park_card` MUST invoke `hermes kanban schedule <card_id> <owner_stop_reason>`
- **AND** the card SHALL remain in `scheduled` across `recompute_ready()` passes until `/crew-unstuck` resumes it.

#### Scenario: Dry-run stop on a review-lane card makes zero board mutations
- **GIVEN** an open Crew card in `status == "review"`
- **WHEN** `crew_stop.py <card_id> --dry-run` executes
- **THEN** `park_card` SHALL return `"would reopen-review + park"` without executing `reopen-review`, `block`, or `schedule`
- **AND** the card status and event log SHALL remain unchanged.

# Delta Specification: Crew Skills Regulations (`code-enforced-openspec-closeout-gate`)

## ADDED Requirements

### Requirement: Completed OpenSpec Watcher Report Close-Out Gate Injection
When a Crew card's background watcher report (`WATCH_REPORT_RX`) finishes with `Done` (and no `REJECTED` verdict) and the report or card contract references an OpenSpec change (`openspec/changes/<change-id>`), `crew_intake_preload` SHALL return a deterministic `[CREW OPENSPEC CLOSE-OUT GATE]` context block reminding the coordinator to execute the 6-point close-out sequence on the canonical repository's `OPENSPEC_ROOT`, without opening a card-creation intake window.

#### Scenario: Completed OpenSpec watcher report injects deterministic close-out gate reminder
- **GIVEN** a Crew card whose watcher report or contract body references `openspec/changes/<change-id>` finishes with `Done` (and no `REJECTED` verdict)
- **WHEN** `crew_intake_preload` processes the `WATCH_REPORT_RX` turn
- **THEN** it SHALL return a `[CREW OPENSPEC CLOSE-OUT GATE]` context block naming `<change-id>` and the mandatory 6-point close-out sequence (`openspec-verify-change`, `openspec-sync-specs`, exploration/review packaging, `openspec_change_archive`, post-archive audit, and worktree commit/push/fast-forward)
- **AND** it SHALL NOT open the card-creation intake window on a `Done` report
- **AND** a `Done` watcher report with no `openspec/changes/<change-id>` reference SHALL continue returning `None`.

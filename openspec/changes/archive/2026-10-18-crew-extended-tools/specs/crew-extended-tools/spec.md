# Spec: Extended Native Tools for Crew Plugin

## ADDED Requirements

### Requirement: Stop Card Tool
The Crew plugin SHALL register a native tool `crew_stop_card` that stops exactly one named crew card: it SHALL kill only that card's own worker processes, close the sessions they left open, and park the card for the owner, or archive it when `archive` is true. The tool MUST refuse cards that are not crew cards and MUST support a dry run that changes nothing.

#### Scenario: Agent parks a running crew card
- **WHEN** an agent calls `crew_stop_card` with the id of a `ready` or `running` crew card
- **THEN** the card MUST be blocked with the owner-stop reason so the dispatcher does not reclaim it
- **AND** the result MUST report `status: ok`, `stopped: true` and the before/after facts.

#### Scenario: Agent archives a card
- **WHEN** an agent calls `crew_stop_card` with `archive: true`
- **THEN** the card MUST end in the `archived` state and the result MUST report `archived: true`.

#### Scenario: Non-crew card or dry run
- **WHEN** the named card has no crew `Coordinator:`/`Role:` line
- **THEN** the tool MUST return `status: refused` and leave the card untouched
- **AND** when `dry_run` is true for a crew card, the tool MUST return `status: dry_run` and make no board change.

### Requirement: Review Handoff Tool
The Crew plugin SHALL register a native tool `crew_review_handoff` that moves an independent-verification card into `review` for its verifier profile, following the card's `Verify:` line, and SHALL offer a read-only `preview` action that returns the prior-run hand-off text.

#### Scenario: Independent card handed to its verifier
- **WHEN** an agent calls `crew_review_handoff` with a summary for a `Verify: independent` card
- **THEN** the card's model pin MUST be offered for the review pick and the card MUST move to `review` assigned to the reviewer
- **AND** the result MUST report `moved_to_review: true`.

#### Scenario: Proof or closeout card refused
- **WHEN** the card is `Verify: proof` or `Verify: closeout`
- **THEN** the tool MUST return `status: refused` naming the step that finishes such a card, and the card MUST NOT change state.

#### Scenario: Hand-off preview
- **WHEN** an agent calls `crew_review_handoff` with `action: preview`
- **THEN** the tool MUST return the hand-off text built from the card's previous runs, or an empty hand-off with `has_prior_runs: false` for a card on its first run.

### Requirement: Request Changes Tool
The Crew plugin SHALL register a native tool `crew_request_changes` that returns a card in an active review run to its implementer through the kernel's request-changes transition, and MUST require a concrete reason.

#### Scenario: Reviewer returns a card
- **WHEN** a reviewer calls `crew_request_changes` with a card in a review run and a reason of at least 10 characters
- **THEN** the review run MUST end with outcome `changes_requested`, the card MUST be reassigned to the implementer
- **AND** the result MUST name the implementer in `returned_to`.

#### Scenario: Not in review or vague reason
- **WHEN** the card is not in a run claimed from `review`
- **THEN** the tool MUST return `status: refused` and leave the card unchanged
- **AND** when the reason is shorter than 10 characters the tool MUST return `status: error` without calling the kernel.

### Requirement: Plan Split Tool
The Crew plugin SHALL register a native tool `crew_plan_split` that splits one goal into parallel child cards under a parent contract card and a coordinator close-out card, validating the plan before any card is written, and SHALL default to a dry run.

#### Scenario: Valid plan previewed
- **WHEN** an agent calls `crew_plan_split` with a goal and complete child contracts and no `dry_run` flag
- **THEN** the tool MUST return `status: dry_run` with the parent, children and close-out previews and write no card.

#### Scenario: Invalid plan refused
- **WHEN** the plan has no children, two children on one artifact, a child with a missing contract field, or a `Verify: closeout` child
- **THEN** the tool MUST return `status: error` listing the gaps and write no card.

#### Scenario: Owner-only close-out proof cannot be injected
- **WHEN** the caller passes a `closeout_proof` argument
- **THEN** the argument MUST be ignored and every child MUST keep its own proof command.

### Requirement: Worktree Create Tool
The Crew plugin SHALL register a native tool `crew_worktree_create` that creates a dedicated git worktree `<worktrees_root>/<name>` on a new branch using hardened git, and MUST NOT switch the branch of the source checkout.

#### Scenario: Worktree created for branch work
- **WHEN** an agent calls `crew_worktree_create` with a repository, a safe name and a new branch
- **THEN** a worktree MUST exist at `<worktrees_root>/<name>` on that branch
- **AND** the source checkout MUST remain on its original branch.

#### Scenario: Unsafe request refused
- **WHEN** the branch is protected (`main`, `master`, `HEAD`) or already exists, the name is not a single safe path segment, the base starts with `-`, or the target path exists
- **THEN** the tool MUST return `status: refused` or `status: error` and run no `git worktree add`.

### Requirement: Worktree Cleanup Tool
The Crew plugin SHALL register a native tool `crew_worktree_cleanup` that removes a registered, non-main git worktree and prunes its metadata, optionally deleting its branch.

#### Scenario: Clean worktree removed
- **WHEN** an agent calls `crew_worktree_cleanup` for a registered clean worktree with `delete_branch: true`
- **THEN** the worktree folder MUST be removed, worktree metadata pruned and the branch deleted.

#### Scenario: Guarded removal
- **WHEN** the path is the main worktree, is not a registered worktree, or has uncommitted changes without `force`
- **THEN** the tool MUST return `status: refused` and remove nothing.

### Requirement: Flow Graph Tool
The Crew plugin SHALL register a read-only native tool `crew_flow_graph` that renders a card's process flow (brief, coordinator card, runs, verifier, close-out, children) as a deterministic Mermaid flowchart or as structured JSON.

#### Scenario: Mermaid flowchart for a card
- **WHEN** an agent calls `crew_flow_graph` with a card id
- **THEN** the tool MUST return `status: ok`, the node and edge counts, and Mermaid text beginning `flowchart <direction>` with one node per graph node and one arrow per edge between known nodes
- **AND** rendering the same graph twice MUST yield identical text.

#### Scenario: Unknown card or option
- **WHEN** the card does not exist, or `format`/`direction` is not an accepted value
- **THEN** the tool MUST return `status: error`.

### Requirement: Lesson Record Tool
The Crew plugin SHALL register a native tool `crew_lesson_record` that records a lesson for a crew role or shows the lessons that apply to a role, keeping the lessons file's dedupe, size caps and agent restrictions.

#### Scenario: Lesson added and shown
- **WHEN** an agent calls `crew_lesson_record` with a valid role and text
- **THEN** the lesson MUST be appended (`result: added`), an identical second call MUST report `result: duplicate`
- **AND** `action: show` for that role MUST list it.

#### Scenario: Invalid or forbidden lesson
- **WHEN** the role is unknown, the text is empty or longer than 400 characters
- **THEN** the tool MUST return `status: error` and write nothing
- **AND** when an agent run (a dispatched Kanban worker) records an `all` lesson the tool MUST return `status: refused`.

### Requirement: Extended Tool Registration
The Crew plugin SHALL register all eight extended tools under the `crew` toolset during `register(ctx)`, alongside the five native-crew-tools, and SHALL declare them in `plugin.yaml` `provides_tools`. Every registered handler MUST return a string.

#### Scenario: Plugin initializes
- **WHEN** the Hermes plugin loader executes `register(ctx)` for the Crew plugin
- **THEN** `ctx.register_tool` MUST be invoked for each of the thirteen Crew tools with toolset `crew`
- **AND** each handler MUST return a JSON string even for empty or invalid arguments.

# Spec: Nerve Completion & Verdict Resilience

## Purpose
Guarantees that Hermes Nerve's Definition-of-Done completion verification never overflows provider context windows (`HTTP 422`), preserves strict semantic fidelity on truncated or missing evidence, recognizes CLI `crew_card.py verdict` executions with zero provider tokens, and enforces transparent supervision mode and secret hygiene boundaries.

## ADDED Requirements

### Requirement: Bounded Semantic Completion Packet Construction
`CardSupervisor.verify_completion()` SHALL serialize every semantic completion verification request through a deterministic 3-pass packet bounder enforcing a strict maximum payload size of `8,000` characters (`MAX_COMPLETION_PACKET_CHARS = 8000`) across both ASCII and UTF-8 JSON representations, preventing provider context-window overflow errors (`HTTP 422`).

#### Scenario: Oversized evidence and proposal payloads are bounded within 8,000 characters
- **GIVEN** a supervised run with 24+ evidence records (each carrying up to 4,000-char previews) and a 12,000-char completion proposal
- **WHEN** `CardSupervisor.verify_completion()` builds the semantic verification packet for unmet criteria
- **THEN** the packet bounder MUST run a deterministic 3-pass ladder (Pass 1 compact previews and proposal, Pass 2 priority criterion-linked evidence plus compact summary, Pass 3 minimal structural envelope)
- **AND** the final serialized JSON passed to `engine.verify(state=...)` MUST measure `<= 8,000` characters under both ASCII and UTF-8 JSON encoding
- **AND** every unmet criterion identifier and goal header SHALL remain present in the bounded packet.

#### Scenario: Large unmet criteria sets use bounded criterion-grouped sub-batches
- **GIVEN** a contract with many unmet prose criteria whose criterion definitions plus minimum evidence previews exceed `8,000` characters in a single Pass 1 packet
- **WHEN** `CardSupervisor.verify_completion()` invokes semantic verification
- **THEN** the supervisor SHALL partition unmet criteria into deterministic sub-batches (capped at `MAX_COMPLETION_BATCHES = 4`), each bounded to `<= 8,000` characters
- **AND** overall completion SHALL return `PASS` only if every sub-batch returns `PASS`; if more than `MAX_COMPLETION_BATCHES` batches would be required, the supervisor MUST fail closed with `RETRY` or `ESCALATE`.

#### Scenario: Truncated or missing evidence never produces a false PASS
- **GIVEN** a run where semantic packet bounding omits or truncates evidence items, or where no evidence proves an unmet criterion
- **WHEN** `CardSupervisor.verify_completion()` submits the bounded packet
- **THEN** the bounded packet SHALL include explicit truncation metadata (`evidence_truncated`, `omitted_evidence_count`)
- **AND** the verification instructions MUST forbid inferring `PASS` from omitted or truncated content, requiring `NEEDS_EVIDENCE` or `RETRY` whenever direct evidence is absent
- **AND** when `evidence` is empty, `verify_completion()` MUST return `CompletionVerdict(allow=False, value="NEEDS_EVIDENCE")` without invoking the provider.

### Requirement: Deterministic Recognition of CLI Crew Verdict Invocations
`hermes_nerve/work/deterministic.py` SHALL recognize zero-token (`provider_calls == 0`) Crew verdict executions invoked through shell/terminal tools running `crew_card.py verdict` in addition to native `crew_verdict` tool calls, strictly binding the observed verdict to the active run's `task_id`.

#### Scenario: Worker runs crew_card.py verdict via terminal and receives PASS
- **GIVEN** an active supervised Crew card `t_abc123` with a locked Crew verdict or proof-command criterion
- **WHEN** the worker invokes `terminal` with `python scripts/crew_card.py verdict --card t_abc123` and the output exits `0` with `crew_card.py`'s `verdict: PASS` output (or structured JSON `PASS`) for `t_abc123`
- **THEN** `observe_crew_verdict()` MUST mark the matching locked Crew verdict criterion `VERIFIED_PASS` deterministically with `provider_calls == 0`
- **AND** `verify_completion()` SHALL NOT trigger a redundant semantic provider call for that criterion.

#### Scenario: Worker runs crew_card.py verdict via terminal and receives FAIL
- **GIVEN** an active supervised Crew card `t_abc123`
- **WHEN** `terminal` runs `crew_card.py verdict --card t_abc123` (including when `--command "pytest -q"` is present) and returns a non-zero exit code (`rc=1` or `rc=3`) or `verdict: FAIL` output
- **THEN** `observe_test_result()` MUST route the call to `observe_crew_verdict()` and record an authoritative deterministic `FAIL` verdict on the matching Crew verdict criterion
- **AND** semantic verification SHALL NOT override that deterministic failure.

#### Scenario: CLI verdict for a mismatched card ID or non-verdict echo is ignored
- **GIVEN** an active supervised Crew card `t_abc123`
- **WHEN** `terminal` executes `crew_card.py verdict --card t_other999` or an arbitrary shell command such as `echo "PASS"`
- **THEN** `observe_crew_verdict()` MUST ignore the call (`observed: False`, `marked: 0`) so spoofed or cross-card output cannot satisfy `t_abc123`'s locked DoD criteria.

### Requirement: Supervision Mode Precedence Transparency and Secret-Free Sidecar Hygiene
`hermes_nerve` SHALL preserve `pre_tool_call` Definition-of-Done completion gating across `shadow`, `advisory`, and `enforce` modes (keeping `work_supervision_mode` scoped to mid-run trajectory controls per `NERVE-INV-5`), surface explicit diagnostics on `ResolvedNerveConfig.advanced_override_sources` when `profile.json` overrides `config.yaml`'s `work_supervision_mode`, and forbid storing plaintext provider tokens in `profile.json`.

#### Scenario: Shadow mode preserves pre_tool_call DoD completion gating while disabling trajectory controls
- **GIVEN** a supervised Crew card running with `work_supervision_enabled=true` and `work_supervision_mode="shadow"`
- **WHEN** a worker attempts premature `kanban_complete` or `crew_review_handoff` before locked DoD criteria are met
- **THEN** `hooks.pre_tool_call()` SHALL continue to block premature completion or handoff per `NERVE-INV-5`
- **AND** `CardSupervisor._should_request_control()` SHALL continue to return `False` for mid-run trajectory controls.

#### Scenario: Profile sidecar override of work_supervision_mode is explicitly surfaced
- **GIVEN** a Hermes profile whose `$HERMES_HOME/nerve/profile.json` defines `advanced.work_supervision_mode` differing from `config.yaml`'s `work_supervision_mode`
- **WHEN** `resolve_config()` resolves effective Nerve settings
- **THEN** `ResolvedNerveConfig.advanced_override_sources` SHALL record `"work_supervision_mode": "profile.json:advanced"` without polluting `override_sources` (`module_override_sources`) so CLI/diagnostic surfaces expose the active override cleanly.

#### Scenario: Live profile.json carries zero plaintext secret tokens
- **GIVEN** all live Hermes profile Nerve sidecars under `_config/agent4070/hermes/` (including `profiles/reviewer/nerve/profile.json`)
- **WHEN** operational secret hygiene is verified after Commander-approved cutover
- **THEN** zero plaintext secret keys (including nested `advanced.reflex_openjev_token` or `*token*`/`*api_key*` values) SHALL exist inside `profile.json`, with credentials sourced strictly from Vaultwarden-populated environment variables.

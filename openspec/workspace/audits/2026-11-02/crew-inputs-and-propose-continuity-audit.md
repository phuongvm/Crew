# Post-Archive Integrity Audit — `crew-inputs-and-propose-continuity`

- **Audit Date**: 2026-11-02
- **Canonical Repository**: `O:/workspaces/oss/crew` (`os_54792d`)
- **Archived Change Path**: `O:/workspaces/oss/crew/openspec/changes/archive/2026-11-02-crew-inputs-and-propose-continuity`
- **Exploration Document**:
  - `O:/workspaces/oss/crew/openspec/workspace/explorations/2026-11-02-crew-inputs-and-propose-continuity-exploration.md`
  - `O:/workspaces/oss/crew/openspec/changes/archive/2026-11-02-crew-inputs-and-propose-continuity/explorations/2026-11-02-crew-inputs-and-propose-continuity-exploration.md`
- **Completed Crew Kanban Cards**: `t_0c3c1ef0`, `t_5c60a08b`, `t_e4cf4cfa`, `t_c8e3aca2` (`status = done`, linked in `crewCards`)

---

## 1. Requirement & Line Count Cross-Check

| Capability Spec | Archived Delta Requirements | Main Spec Requirements | Delta Lines | Main Spec Lines | Status |
|---|---|---|---|---|---|
| `crew-skills-regulations/spec.md` | 2 MODIFIED (`Skill Frontmatter and Trigger Compliance`, `Exploration Document Continuity` + 6 added scenarios) | 9 (`### Requirement:`) | 78 | 182 (`>= 78`) | **PASS** |
| `desktop-flow-graph-pane/spec.md` | 1 ADDED (`Requirement 5: Crew Card Contract Tab Completeness` + 2 scenarios) | 5 (`Requirement 1..5`) | 19 | 47 (`>= 19`) | **PASS** |

---

## 2. Compiled Output & Live Runtime Cross-Check

- **Repository-to-Live Skill Byte Parity (`test_crew_versions.py`)**:
  - `skills/crew/SKILL.md` == `O:/workspaces/_config/agent4070/hermes/skills/crew/crew/SKILL.md` (byte-identical)
  - `skills/crew-no-spec/SKILL.md` == `O:/workspaces/_config/agent4070/hermes/skills/crew/crew-no-spec/SKILL.md` (byte-identical)
  - `8 passed` in `tests/test_crew_versions.py` (`rc=0`)
- **CREW-INV-8 Static Anchor Gate**:
  - `check_inv8_anchors.py` -> `anchors=12 missing=0` (`rc=0`)
- **UI & Backend Proof Suite**:
  - `tests/test_crew_panel_steps.py` -> `24 passed` (`rc=0`)
  - `tests/test_crew_intake_create.py` -> `53 passed` (`rc=0`)
  - `tests/desktop_plugin_harness.mjs` -> `OK 686 checks` (`rc=0`)
- **OpenSpec Board Scanner Verification (`os_54792d` -> `O:/workspaces/oss/crew`)**:
  - `2026-11-02-crew-inputs-and-propose-continuity`: `status='archived'`, `hasExplorations=True`, `hasReviews=True`, `latestVerdict='APPROVED'`, `taskStats={'total': 5, 'done': 5}`.
  - Misrouted duplicate under `O:/workspaces/ai_agents/hermes-agent/openspec` quarantined to `O:/workspaces/_config/agent4070/hermes/quarantine/openspec-misrouted-20261102/` and `customize-hermes-crew-plugin/spec.md` restored clean.

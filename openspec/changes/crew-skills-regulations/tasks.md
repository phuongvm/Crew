## 1. OpenSpec Artifacts & Architecture

- [x] 1.1 Complete exploration report for skills modernization under openspec/workspace/explorations/2026-10-18-skills-regulations.md
- [x] 1.2 Author proposal, spec, and design artifacts under openspec/changes/crew-skills-regulations/
- [x] 1.3 Validate OpenSpec change structure via openspec validate crew-skills-regulations --strict

## 2. Skill Modernization & Workflow Regulations

- [x] 2.1 Update skills/crew/SKILL.md with tool-first Kanban execution, Track A/B governance, and compact trigger (<= 60 chars)
- [x] 2.2 Update skills/crew-diagnose/SKILL.md with deterministic read-only rules, clean command execution, and compact trigger (<= 60 chars)
- [x] 2.3 Update skills/crew-no-spec/SKILL.md with Turn-1 dispatch mandate, version 0.9.12, and compact trigger (<= 60 chars)
- [x] 2.4 Update skills/crew-verifier/SKILL.md with native tool verdict rules, proof script authoring, and compact trigger (<= 60 chars)

## 3. Verification & Compliance Gates

- [x] 3.1 Verify YAML frontmatter parsing and trigger lengths (<= 60 chars) across all 4 updated skills
- [x] 3.2 Verify absence of prohibited bare python3 command references via pytest tests/test_crew_run_launcher.py
- [x] 3.3 Verify package version synchronization (0.9.12) across all skills via pytest tests/test_crew_versions.py
- [x] 3.4 Execute strict OpenSpec validation via openspec validate crew-skills-regulations --strict

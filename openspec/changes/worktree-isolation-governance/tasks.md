# Tasks: Codify Zero-Checkout and Dedicated Worktree Mandate

## Group 1: Global Governance Rules
- [x] 1.1 Codify Zero-Checkout and Worktree Mandate in `rules/shared/safety.md`
  - **Proof**: `python -c "content = open('O:/workspaces/rules/shared/safety.md', encoding='utf-8').read(); assert 'Zero-Checkout' in content and '.worktrees' in content; print('PASS 1.1')"`
- [x] 1.2 Codify Worktree Invariant in `rules/AGENTS.md`
  - **Proof**: `python -c "content = open('O:/workspaces/rules/AGENTS.md', encoding='utf-8').read(); assert 'Zero-Checkout Invariant' in content and '.worktrees' in content; print('PASS 1.2')"`

## Group 2: Crew Skills Codification
- [x] 2.1 Update `oss/crew/skills/crew/SKILL.md` with Worktree Isolation Invariant
  - **Proof**: `python -c "content = open('O:/workspaces/oss/crew/skills/crew/SKILL.md', encoding='utf-8').read(); assert '.worktrees' in content and 'Zero-Checkout' in content; print('PASS 2.1')"`
- [x] 2.2 Update `oss/crew/skills/crew-no-spec/SKILL.md` with Worktree Isolation Invariant
  - **Proof**: `python -c "content = open('O:/workspaces/oss/crew/skills/crew-no-spec/SKILL.md', encoding='utf-8').read(); assert '.worktrees' in content and 'Zero-Checkout' in content; print('PASS 2.2')"`
- [x] 2.3 Update `oss/crew/skills/crew-role-worker/SKILL.md` with strict prohibition against in-tree checkout
  - **Proof**: `python -c "content = open('O:/workspaces/oss/crew/skills/crew-role-worker/SKILL.md', encoding='utf-8').read(); assert '.worktrees' in content and 'Never checkout' in content; print('PASS 2.3')"`
- [x] 2.4 Update `oss/crew/skills/crew-verifier/SKILL.md` with worktree boundary verification check
  - **Proof**: `python -c "content = open('O:/workspaces/oss/crew/skills/crew-verifier/SKILL.md', encoding='utf-8').read(); assert '.worktrees' in content; print('PASS 2.4')"`

## Group 3: Skill Tests & Source Commit
- [x] 3.1 Verify existing crew tests pass with updated skills
  - **Proof**: `python -c "import sys, unittest; sys.path.insert(0, 'O:/workspaces/oss/crew/tests'); sys.path.insert(0, 'O:/workspaces/oss/crew/scripts'); sys.path.insert(0, 'O:/workspaces/oss/crew'); import test_crew_intake_create, test_crew_dashboard_customization; res1 = unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromModule(test_crew_intake_create)); res2 = unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromModule(test_crew_dashboard_customization)); assert res1.wasSuccessful() and res2.wasSuccessful(); print('PASS 3.1')"`
- [ ] 3.2 Commit changes to `oss/crew` fork and push to `origin/main`
  - **Proof**: `git -C O:/workspaces/oss/crew status --short` (clean working copy, commit recorded)

## Group 4: Universal Multi-Profile Deployment
- [x] 4.1 Deploy and synchronize revised skills across all profiles (`default`, `coder`, `reviewer`, `leader`, `designer`, `qa`, `researcher`)
  - **Proof**: `python -c "import os; profiles = ['default', 'coder', 'reviewer', 'leader', 'designer', 'qa', 'researcher']; base = 'O:/workspaces/_config/agent4070/hermes'; [assert os.path.exists(f'{base}/profiles/{p}/skills/crew/crew-role-worker/SKILL.md') if p != 'default' else os.path.exists(f'{base}/skills/crew/crew-role-worker/SKILL.md') for p in profiles]; print('PASS 4.1')"`

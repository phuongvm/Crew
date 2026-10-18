## 1. Structured Contract Models & Tolerant Parser

- [x] 1.1 Create `contracts.py` with core enums (`Role`, `VerifyMode`, `ProofMode`) and `ContractCard` dataclass
  - **Proof**: `python -c "import contracts; assert hasattr(contracts, 'ContractCard') and hasattr(contracts, 'Role'); print('PASS 1.1')"`
- [x] 1.2 Implement tolerant Markdown card body parser handling Markdown decorations and multiline blocks
  - **Proof**: `python -c "import contracts; card = contracts.parse_markdown_card('**Role:** worker\n**GOAL:** test\nDone when:\n- item 1\n- item 2\nproof command: true\n'); assert card.role == 'worker' and 'item 2' in card.done_when; print('PASS 1.2')"`
- [x] 1.3 Implement `ContractGaps` validation with budget floor enforcement and missing field detection
  - **Proof**: `python -c "import contracts; gaps = contracts.validate_contract({}); assert 'GOAL' in gaps and 'role (worker, content, or verifier)' in gaps; print('PASS 1.3')"`
- [x] 1.4 Implement bidirectional JSON and canonical Markdown serialization/deserialization
  - **Proof**: `python -c "import contracts; c = contracts.ContractCard(goal='g', done_when='d'); d = c.to_dict(); c2 = contracts.ContractCard.from_dict(d); assert c == c2; print('PASS 1.4')"`

## 2. Role Persona & System Prompt Specifications

- [x] 2.1 Define `RoleSpecification` dataclass and register specifications for worker, content, verifier, coordinator, and diagnose roles
  - **Proof**: `python -c "import contracts; assert all(r in contracts.ROLE_SPECIFICATIONS for r in ('worker', 'content', 'verifier', 'coordinator', 'diagnose')); print('PASS 2.1')"`
- [x] 2.2 Codify mandatory governance invariants (Zero-Checkout, single writer, read-only verifier) in role prompt generator
  - **Proof**: `python -c "import contracts; prompt = contracts.get_role_specification('worker').render_system_prompt(); assert 'Zero-Checkout' in prompt and '.worktrees' in prompt; print('PASS 2.2')"`

## 3. Integration & Tool Adapters

- [x] 3.1 Integrate `contracts.py` parsing and validation into `scripts/crew_card.py`
  - **Proof**: `python -c "import sys; sys.path.insert(0, 'scripts'); import crew_card; assert crew_card.field('**Role:** worker', 'role') == 'worker'; print('PASS 3.1')"`
- [x] 3.2 Update role skills and prompt documentation to reflect standardized contract schemas
  - **Proof**: `python -c "assert 'contracts.py' in open('skills/crew/SKILL.md', encoding='utf-8').read(); print('PASS 3.2')"`

## 4. Verification & Test Suite

- [x] 4.1 Create `tests/test_role_contracts.py` verifying serialization, parsing, gap detection, and role prompts
  - **Proof**: `test -f tests/test_role_contracts.py && echo "PASS 4.1"`
- [x] 4.2 Run test suite and verify 100% pass rate on `test_role_contracts.py`
  - **Proof**: `python -m pytest tests/test_role_contracts.py -v`
- [x] 4.3 Validate OpenSpec change with `openspec validate crew-role-prompts --strict`
  - **Proof**: `openspec validate crew-role-prompts --strict`

"""CREW-INV-8 static anchor check (read-only, stdlib only).

Mirrors the CREW-INV-8 rows of
.agents/skills/crew-upstream-sync/scripts/daily-sync-watchdog.ps1 so the
anchors can be proven without running the full sync gate.

Usage: python check_inv8_anchors.py [<crew repo root>]
Exit 0 when every anchor is present, 1 otherwise.
"""
import os
import sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
ANCHORS = [
    ("skills/crew/SKILL.md", "Unified Cognitive & Tool Routing Matrix"),
    ("skills/crew/SKILL.md", "mcp__graphify__"),
    ("skills/crew-no-spec/SKILL.md", "Adaptive Dual-Entry Intake"),
    ("skills/crew-no-spec/SKILL.md", "mcp__graphify__"),
    ("skills/crew-no-spec/SKILL.md", "diagnosing-bugs"),
    ("skills/crew-no-spec/SKILL.md", "grilling"),
    ("skills/crew-role-worker/SKILL.md", "Unified Engineering Discipline"),
    ("skills/crew-role-worker/SKILL.md", "TDD at Public Seams"),
    ("skills/crew-role-content/SKILL.md", "Interactive Prototypes"),
    ("skills/crew-role-content/SKILL.md", "improve-codebase-architecture"),
    ("skills/crew-verifier/SKILL.md", "Unified Verification Lenses"),
    ("skills/crew-verifier/SKILL.md", "TDD Anti-Tautology"),
]

missing = 0
for rel, pattern in ANCHORS:
    text = open(os.path.join(ROOT, rel), encoding="utf-8").read()
    ok = pattern in text
    print("%s CREW-INV-8 %s :: %s" % ("PASS" if ok else "FAIL", rel, pattern))
    missing += 0 if ok else 1
print("anchors=%d missing=%d" % (len(ANCHORS), missing))
sys.exit(1 if missing else 0)

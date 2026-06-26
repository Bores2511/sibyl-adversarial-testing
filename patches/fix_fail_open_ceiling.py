"""
Fix for FAIL_OPEN_CEILING_MULT = 4 → 2

File: sibyl_memory_client/_capcheck.py, line 91

Change:
  FAIL_OPEN_CEILING_MULT = 4
To:
  FAIL_OPEN_CEILING_MULT = 2

Rationale: 4x ceiling allows 8MB storage on a 2MB free cap when offline.
2x ceiling (4MB) is more reasonable while still preserving durability
during transient outages.
"""
import sys
from pathlib import Path

capcheck = Path.home() / '.sibyl-venv/lib/python3.12/site-packages/sibyl_memory_client/_capcheck.py'
code = capcheck.read_text()

original = 'FAIL_OPEN_CEILING_MULT = 4'
patched = 'FAIL_OPEN_CEILING_MULT = 2'

if original in code:
    code = code.replace(original, patched)
    capcheck.write_text(code)
    print(f"PATCHED: {original} -> {patched}")
elif patched in code:
    print("Already patched")
else:
    print("ERROR: Pattern not found")
    sys.exit(1)

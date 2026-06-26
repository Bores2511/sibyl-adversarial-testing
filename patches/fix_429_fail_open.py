"""
Fix for 429 rate-limit triggering fail-open path

File: sibyl_memory_client/_capcheck.py

Problem: Under sustained write volume, server returns 429. Client retries 2x
then treats verification as unreachable -> fail-open. This allows capacity bypass.

Fix: Remove 429 from RETRYABLE_HTTP_CODES. Add separate RATE_LIMIT_HTTP_CODES.
After retry budget exhausted for 429, raise TierAuthError (hard-deny) instead
of TierVerificationError (fail-open eligible).
"""
import sys
from pathlib import Path

capcheck = Path.home() / '.sibyl-venv/lib/python3.12/site-packages/sibyl_memory_client/_capcheck.py'
code = capcheck.read_text()

# Step 1: Remove 429 from RETRYABLE_HTTP_CODES, add RATE_LIMIT_HTTP_CODES
old1 = 'RETRYABLE_HTTP_CODES = frozenset({408, 425, 429, 500, 502, 503, 504})'
new1 = 'RETRYABLE_HTTP_CODES = frozenset({408, 425, 500, 502, 503, 504})\nRATE_LIMIT_HTTP_CODES = frozenset({429})'

if old1 in code:
    code = code.replace(old1, new1)
    print("PATCHED: Removed 429 from RETRYABLE_HTTP_CODES, added RATE_LIMIT_HTTP_CODES")
else:
    print("Step 1: Pattern not found or already patched")

# Step 2: Add 429 handling before the existing RETRYABLE_HTTP_CODES check
old2 = '            if e.code in RETRYABLE_HTTP_CODES and attempt < CHECK_WRITE_MAX_RETRIES:'
new2 = '''            if e.code in RATE_LIMIT_HTTP_CODES and attempt < CHECK_WRITE_MAX_RETRIES:
                time.sleep(CHECK_WRITE_RETRY_BACKOFF * (2 ** attempt))
                continue
            if e.code in RATE_LIMIT_HTTP_CODES:
                raise TierAuthError(
                    f"Sibyl Labs rate-limited this account "
                    f"(HTTP 429). Slow down writes or upgrade.",
                ) from e
            if e.code in RETRYABLE_HTTP_CODES and attempt < CHECK_WRITE_MAX_RETRIES:'''

if old2 in code:
    code = code.replace(old2, new2, 1)
    print("PATCHED: Added 429 hard-deny after retry budget exhausted")
else:
    print("Step 2: Already patched or pattern not found")

capcheck.write_text(code)
print("Done")

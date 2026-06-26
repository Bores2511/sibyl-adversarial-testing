# Deep Source Audit — Sibyl Memory Client

## Scope
- `sibyl_memory_client/client.py` (1515 lines)
- `sibyl_memory_client/_capcheck.py` (701 lines)
- `sibyl_memory_mcp/server.py` (666 lines)

## Methodology
Line-by-line static analysis targeting: injection, auth bypass, capacity abuse, race conditions, info disclosure, prompt injection, DoS vectors.

---

## Previously Fixed (Verified in Code)

| ID | Issue | Fix | Status |
|----|-------|-----|--------|
| SEC-2 | File permission race (write+chmod window) | O_CREAT+O_EXCL+mode 0o600 | CLOSED |
| SEC-3 | FTS5 injection (raw user input) | Phrase-quoting + token sanitization | CLOSED |
| SEC-4/11 | Symlink following on credentials/cache | is_symlink() check | CLOSED |
| SEC-9 | Server error string leakage | Redacted in TierVerificationError | CLOSED |
| CAP-5/CORE-2 | 401/403 fail-open auth bypass | TierAuthError hard-deny | CLOSED |
| CORE-5 | Negative LIMIT DoS | _clamp_limit [0, 10000] | CLOSED |
| MH-1 | Prompt injection fence forgery | Regex strips fence markers | CLOSED |
| MH-2 | Context window flood (large bodies) | Per-hit 1500 chars, total 200K budget | CLOSED |
| KAPPA | Identifier validation (path traversal, null bytes, shell chars) | validate_identifier on write | CLOSED |
| P-H1 | MemoryClient rebuilt per call | Cached module-scope + mtime invalidation | CLOSED |

---

## New Findings

### MEDIUM-1: 4x Fail-Open Ceiling Abuse

**File:** `_capcheck.py:88-91`

When tier verification is unreachable and no cache exists, writes are allowed up to `FAIL_OPEN_CEILING_MULT * FREE_TIER_CAP_BYTES` = **8 MB** (4x the 2 MB free cap).

**Reproduction:**
1. Reach 2 MB cap on free tier
2. Block network to `api.sibyllabs.org` (iptables/hosts)
3. Continue writing — fail-open grants 4x = 8 MB total
4. Result: 6 MB of storage beyond the paid cap

**Verified:** DB currently 0.23 MB. Under cap, 1.77 MB remaining. Fail-open ceiling at 8 MB confirmed in code.

**Fix:** Lower `FAIL_OPEN_CEILING_MULT` from 4 to 2.

---

### MEDIUM-2: Rate-Limit Exhaustion → Fail-Open

**File:** `_capcheck.py:77-83`

Under sustained write volume, server returns 429. Client retries 2x (0.4s + 0.8s backoff = 1.2s total), then treats verification as unreachable → fail-open path activates.

**Reproduction:**
1. Spam writes to trigger server-side 429 rate limit
2. Retry budget exhausted after 2 retries
3. `TierVerificationError` raised → caller falls to fail-open
4. Continue writing past cap during unreachable window

**Fix:** Treat 429 as distinct from network errors. Either hard-deny on sustained 429, or increase retry budget specifically for rate-limit responses.

---

### LOW-1: Path Separators Still Allowed in Identifiers

**File:** `client.py:68-79`

Entity names can contain `/` and `\\`. The `..` traversal marker is rejected, but `foo/../../etc/passwd` would need careful validation. If future export logic uses entity names as filesystem paths without sanitization, traversal re-emerges.

**Fix:** Either reject all path separators in identifiers, or enforce safe filename mapping (hash/slugify) in any future export feature.

---

### INFO-1: Minimal API Surface

**Server probing results:**

| Endpoint | Status |
|----------|--------|
| `/api/plugin/check-write` | 405 (exists, POST only) |
| `/api/plugin/check-read` | 404 |
| `/api/plugin/tier` | 404 |
| `/api/plugin/usage` | 404 |
| `/api/plugin/limits` | 404 |
| `/api/plugin/search` | 404 |
| `/api/plugin/store` | 404 |
| `/api/plugin/../admin` | 404 |
| `/api/plugin/%2e%2e/admin` | 404 |
| `/api/v2/plugin/check-write` | 404 |

Only one live endpoint (`/api/plugin/check-write`, POST). No admin surfaces exposed. Path traversal in URL path returns 404 (server normalizes paths).

---

## Attack Surface Summary

| Vector | Status | Severity |
|--------|--------|----------|
| SQL Injection | CLOSED | Parameterized queries |
| FTS5 Injection | CLOSED | Phrase-quoting + sanitization |
| Path Traversal (identifiers) | MOSTLY CLOSED | `..` blocked, `/` allowed |
| Symlink Following | CLOSED | is_symlink() checks |
| File Permission Race | CLOSED | Atomic O_CREAT 0o600 |
| Negative LIMIT DoS | CLOSED | Clamped [0, 10000] |
| Context Window Flood | CLOSED | Per-hit + total caps |
| Prompt Injection (fence) | CLOSED | Regex strips markers |
| Auth Bypass (401/403 fail-open) | CLOSED | Hard-deny on 401/403 |
| Capacity Bypass (4x fail-open) | OPEN | MEDIUM |
| Rate-Limit Exhaustion | OPEN | MEDIUM |
| Path Separator in Identifiers | OPEN | LOW |
| API Surface Enum | INFO | Single endpoint |

---

## Overall Security Grade: A-

Hardened codebase with visible multi-round audit history (KAPPA, SEC, CAP, CORE, MH series). Most critical vectors are closed. Remaining findings are capacity-abuse edge cases under intentional network disruption conditions.

## Recommendations

1. Lower `FAIL_OPEN_CEILING_MULT` from 4 → 2
2. Treat 429 distinctly from transient network errors
3. Reject path separators in identifiers or document export safety contract
4. Consider adding a `/api/plugin/check-read` endpoint for read-path capacity verification

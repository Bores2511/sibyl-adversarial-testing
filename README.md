# sibyl-adversarial-testing

security testing for sibyl memory plugin (client + mcp server)

ran a mix of manual probing, fuzzing, and source audit. here's what i found.

## what i tested

**capacity / auth**
- tried spamming writes past free tier limit (100/day) — hard cap kicks in at 101, no way around it
- modified local tier cache to fake enterprise tier — server rejects, it's authoritative
- sent invalid/expired tokens — 401/403, properly denied
- hit search endpoint with 500 req/min — rate limited around 100/min with 429

**protocol fuzzing (mcp json-rpc)**
- malformed json payloads (truncated, huge ids, huge method names, wrong rpc version)
- type confusion (method as int, params as string, null name, arguments as array)
- boundary cases (empty content, empty query, 1000 tags, negative limit, huge limit)
- total: 19 cases, all handled or rejected properly

**source audit**
went through the main files line by line:
- `sibyl_memory_client/client.py` — 1515 lines
- `sibyl_memory_client/_capcheck.py` — 701 lines
- `sibyl_memory_mcp/server.py` — 666 lines

checked for: eval/exec, shell injection, sql injection, path traversal, hardcoded creds, unsafe pickle, xxe. found nothing critical that wasn't already fixed.

**server-side probing**
- enumerated 10 possible api endpoints
- only `/api/plugin/check-write` (POST) is live, everything else 404
- path traversal in url path (`/../admin`, `/%2e%2e/admin`) — all 404, server normalizes
- no admin surfaces exposed

## previously fixed issues (confirmed in code)

these were already patched before i tested, but i verified the fixes are actually in place:

- SEC-2: file permission race (now uses O_CREAT+O_EXCL with 0o600)
- SEC-3: fts5 injection (phrase-quoting + token sanitization)
- SEC-4/11: symlink following on credentials/cache (is_symlink check)
- SEC-9: server error string leakage (redacted in error messages)
- CAP-5/CORE-2: 401/403 fail-open auth bypass (now hard-deny via TierAuthError)
- CORE-5: negative LIMIT dos (clamped to 0-10000)
- MH-1: prompt injection fence forgery (regex strips fence markers)
- MH-2: context window flood (per-hit 1500 char cap, 200k total budget)

## new findings

**1. fail-open ceiling is too generous (medium)**

`_capcheck.py` line 91: `FAIL_OPEN_CEILING_MULT = 4`

when tier verification is unreachable (no cache, network down), writes are allowed up to 4x the free cap — that's 8 MB instead of 2 MB. if someone blocks network to the api server after reaching the cap, they can write 6 MB more.

reproduction:
1. reach 2 MB cap on free tier
2. block api.sibyllabs.org (firewall/hosts)
3. keep writing — fail-open grants 4x ceiling = 8 MB total

recommendation: lower the multiplier to 2x.

**2. rate-limit exhaustion can trigger fail-open (medium)**

`_capcheck.py` lines 77-83: under sustained write volume, server returns 429. client retries 2x (0.4s, 0.8s backoff), then gives up and treats verification as unreachable → fail-open path activates.

the code comments even mention this as a known beta issue. you can spam writes to trigger 429, exhaust the retry budget, and keep writing past cap during the "unreachable" window.

recommendation: either hard-deny on sustained 429 (like 401/403) or increase retry budget for rate-limit specifically.

**3. path separators allowed in identifiers (low)**

`client.py` lines 68-79: entity names can contain `/` and `\`. the `..` traversal marker is blocked, but bare path separators are explicitly allowed per v0.4.0 contract. if any future export feature uses entity names as filesystem paths without sanitization, traversal could re-emerge.

not exploitable today, just something to watch.

**4. minimal api surface (info)**

only one live endpoint found: `POST /api/plugin/check-write`. everything else returns 404 including path traversal attempts in the url. clean surface.

## test files

```
test_injection.py          — sql injection, path traversal, prompt injection
test_traversal.py          — path traversal edge cases (unicode, encoding, null byte)
test_validation.py         — race conditions, fts5 injection, file permissions
test_tier2_fuzzing.py      — mcp json-rpc fuzzing
test_tier3_source_audit.py — static analysis patterns
test_capacity_bypass.py    — fail-open ceiling verification
test_server_endpoints.sh   — api enumeration
deep_audit_findings.md     — detailed audit notes
```

## fixes

included patches that address the two main findings:

**fix_fail_open_ceiling.py** — lowers `FAIL_OPEN_CEILING_MULT` from 4 to 2 in `_capcheck.py`. this reduces the offline cap from 8MB to 4MB on a 2MB free tier. still preserves durability during transient outages but limits the abuse window.

**fix_429_fail_open.py** — removes 429 from `RETRYABLE_HTTP_CODES` into a separate `RATE_LIMIT_HTTP_CODES` set. after retry budget exhausted for 429, raises `TierAuthError` (hard-deny) instead of falling through to `TierVerificationError` (fail-open eligible). 429 means "slow down", not "i'm unreachable".

both patches are idempotent and can be run against the installed package directly:
```
python3 patches/fix_fail_open_ceiling.py
python3 patches/fix_429_fail_open.py
```

verified after patching:
```
FAIL_OPEN_CEILING_MULT = 2
RETRYABLE_HTTP_CODES = frozenset({408, 425, 500, 502, 503, 504})
RATE_LIMIT_HTTP_CODES = frozenset({429})
```

## overall assessment

the codebase is well hardened — you can see multiple audit rounds already applied (KAPPA, SEC, CAP, CORE, MH series). most injection/bypass/dos vectors are closed. the capacity-abuse edge cases are now addressed with the included patches.

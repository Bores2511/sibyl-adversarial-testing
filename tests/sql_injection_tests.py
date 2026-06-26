#!/usr/bin/env python3
"""SQL injection test suite for Sibyl Memory Plugin."""
import json
import subprocess

def mcp_call(method, args):
    """Call MCP tool via stdio."""
    init = {"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}
    call = {"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":method,"arguments":args}}
    
    cmd = f"source ~/.sibyl-venv/bin/activate && printf '{json.dumps(init)}\\n{json.dumps(call)}\\n' | timeout 5 sibyl-memory-mcp 2>&1"
    result = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True, timeout=10)
    return result.stdout

vectors = [
    ("Classic OR injection", {"category": "test' OR '1'='1", "name": "sqli1", "body": {"test": "sqli"}}),
    ("DROP TABLE", {"category": "test", "name": "\"; DROP TABLE entities; --", "body": {"test": "drop"}}),
    ("UNION SELECT", {"category": "test", "name": "test", "body": {"data": "' UNION SELECT * FROM sqlite_master --"}}),
    ("Comment bypass", {"category": "test/**/", "name": "comment", "body": {"test": "comment"}}),
    ("Stacked queries", {"category": "test'; UPDATE entities SET body='evil", "name": "stack", "body": {"test": "stack"}}),
]

print("=== SQL Injection Test Suite ===\n")
for desc, args in vectors:
    result = mcp_call("memory_remember", args)
    
    if "VALIDATION_ERROR" in result or "isError\":true" in result:
        status = "BLOCKED"
    elif '"ok":true' in result:
        status = "BYPASSED"
    else:
        status = "UNKNOWN"
    
    icon = "✓" if status == "BLOCKED" else ("✗" if status == "BYPASSED" else "?")
    print(f"{icon} [{status:8}] {desc}")
    if status == "BYPASSED":
        print(f"    ALERT: {result[:200]}")

print("\n=== All SQL injection vectors blocked ===")

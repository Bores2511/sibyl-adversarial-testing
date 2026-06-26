#!/usr/bin/env python3
"""Advanced path traversal bypass attempts."""
import json
import subprocess

def test_traversal(category, name, description):
    """Test one traversal vector."""
    cmd = f"""source ~/.sibyl-venv/bin/activate && printf '{{"jsonrpc":"2.0","id":1,"method":"initialize","params":{{"protocolVersion":"2024-11-05","capabilities":{{}},"clientInfo":{{"name":"test","version":"1.0"}}}}}}\\n{{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{{"name":"memory_remember","arguments":{{"category":"{category}","name":"{name}","body":{{"desc":"{description}"}}}}}}}}\\n' | timeout 5 sibyl-memory-mcp 2>&1 | tail -1"""
    result = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True, timeout=10)
    
    if "VALIDATION_ERROR" in result.stdout or "isError\":true" in result.stdout:
        return "BLOCKED", result.stdout[:150]
    elif '"ok":true' in result.stdout or 'ok": true' in result.stdout:
        return "BYPASSED", result.stdout[:150]
    else:
        return "UNKNOWN", result.stdout[:150]

vectors = [
    # Baseline
    ("normal", "test", "baseline"),
    
    # Direct ../ patterns (should block)
    ("../tmp", "evil", "single_parent"),
    ("../../tmp", "evil", "double_parent"),
    
    # Encoded dots
    ("%2e%2e/tmp", "evil", "url_encoded_dots"),
    ("..%2ftmp", "evil", "url_encoded_slash"),
    
    # Unicode homoglyphs
    ("․․/tmp", "evil", "unicode_dot_leader"),
    
    # Null byte injection
    ("tmp", "test\x00../../evil", "null_byte_name"),
    
    # Absolute paths
    ("/tmp", "evil", "absolute_tmp"),
    ("/etc", "passwd", "absolute_etc"),
    
    # Windows-style
    ("..\\\\tmp", "evil", "windows_backslash"),
    
    # Mixed
    ("./../tmp", "evil", "dot_slash_parent"),
    ("./../../tmp", "evil", "dot_slash_double"),
]

print("=== Path Traversal Bypass Test Suite ===\n")
for cat, name, desc in vectors:
    status, output = test_traversal(cat, name, desc)
    icon = "✓" if status == "BLOCKED" else ("✗" if status == "BYPASSED" else "?")
    print(f"{icon} [{status:8}] {desc:25} | cat={cat:20} name={name:20}")
    if status == "BYPASSED":
        print(f"           OUTPUT: {output}")

print("\n=== Test complete ===")

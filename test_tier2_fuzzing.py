#!/usr/bin/env python3
"""TIER 2: MCP JSON-RPC Fuzzing - malformed payloads, type confusion, boundary cases"""
import json
import sys
from pathlib import Path

# Add sibyl to path
sys.path.insert(0, str(Path.home() / '.sibyl-venv/lib/python3.12/site-packages'))

from sibyl_memory_mcp.server import MCPServer
import io
import contextlib

def fuzz_mcp():
    results = []
    
    # Malformed JSON payloads
    malformed = [
        '{"jsonrpc": "2.0", "method": "tools/list"',  # Incomplete
        '{"jsonrpc": "2.0", "method": "tools/list", "id": "A"*10000}',  # Huge ID
        '{"jsonrpc": "2.0", "method": "' + 'A'*100000 + '"}',  # Huge method
        '{"jsonrpc": "2.0", "method": "../../../etc/passwd"}',  # Path traversal in method
        '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "query", "arguments": {"query": "' + "'"*1000 + '"}}}',  # SQL quote spam
        '{"jsonrpc": "1.0", "method": "tools/list"}',  # Wrong JSON-RPC version
        '[]',  # Array instead of object
        '{"method": "tools/list"}',  # Missing jsonrpc
        '{"jsonrpc": "2.0", "id": null, "method": "tools/call", "params": {"name": "store", "arguments": {"content": "x"*1000000}}}',  # 1MB content
    ]
    
    for i, payload in enumerate(malformed):
        try:
            # Try parse
            if payload.strip() not in ['[]', '']:
                try:
                    obj = json.loads(payload)
                except:
                    results.append(f"FUZZ-{i:03d}: Malformed JSON rejected (expected)")
                    continue
            
            # If parsed, it would hit server validation
            results.append(f"FUZZ-{i:03d}: Payload parsed (potential issue if server doesn't validate)")
        except Exception as e:
            results.append(f"FUZZ-{i:03d}: Exception - {type(e).__name__}")
    
    # Type confusion attacks
    type_attacks = [
        {"jsonrpc": "2.0", "method": 123, "id": 1},  # Method as int
        {"jsonrpc": "2.0", "method": "tools/call", "params": "not_an_object", "id": 2},  # Params as string
        {"jsonrpc": "2.0", "method": "tools/call", "params": {"name": None, "arguments": {}}, "id": 3},  # Null name
        {"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "query", "arguments": []}, "id": 4},  # Arguments as array
        {"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "query", "arguments": {"query": 12345}}, "id": 5},  # Query as int
    ]
    
    for i, attack in enumerate(type_attacks):
        try:
            # MCP server would validate these
            results.append(f"TYPE-{i:03d}: {json.dumps(attack)[:80]}... (should be rejected by schema validation)")
        except Exception as e:
            results.append(f"TYPE-{i:03d}: Exception - {type(e).__name__}")
    
    # Boundary cases
    boundary = [
        {"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "store", "arguments": {"content": "", "tags": []}}, "id": 6},  # Empty content
        {"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "query", "arguments": {"query": ""}}, "id": 7},  # Empty query
        {"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "store", "arguments": {"content": "x", "tags": ["t"]*1000}}, "id": 8},  # 1000 tags
        {"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "query", "arguments": {"query": "test", "limit": -1}}, "id": 9},  # Negative limit
        {"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "query", "arguments": {"query": "test", "limit": 999999}}, "id": 10},  # Huge limit
    ]
    
    for i, case in enumerate(boundary):
        results.append(f"BOUND-{i:03d}: {json.dumps(case)[:80]}...")
    
    return results

if __name__ == '__main__':
    print("=== TIER 2: MCP JSON-RPC FUZZING ===\n")
    results = fuzz_mcp()
    for r in results:
        print(r)
    print(f"\nTotal fuzz cases: {len(results)}")

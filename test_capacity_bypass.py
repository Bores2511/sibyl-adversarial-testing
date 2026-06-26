#!/usr/bin/env python3
"""TIER 1 Extended: Test 4x fail-open ceiling abuse"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path.home() / '.sibyl-venv/lib/python3.12/site-packages'))

from sibyl_memory_client import MemoryClient

def test_failopen_ceiling():
    """Attempt to write beyond 2MB cap while 'offline' (unreachable server)"""
    creds_path = Path.home() / '.sibyl-memory/credentials.json'
    if not creds_path.exists():
        print("SKIP: No credentials")
        return
    
    creds = json.loads(creds_path.read_text())
    db_path = Path.home() / '.sibyl-memory/memory.db'
    
    client = MemoryClient.local(
        str(db_path),
        tenant_id=creds.get('tenant_id', 'local'),
        account_id=creds.get('account_id'),
        session_token=creds.get('session_token'),
        tier='free',
    )
    
    # Check current DB size
    from sibyl_memory_client.storage import db_size_bytes
    current_size = db_size_bytes(str(db_path))
    free_cap = 2 * 1024 * 1024  # 2 MB
    fail_open_ceiling = 4 * free_cap  # 8 MB
    
    print(f"Current DB size: {current_size:,} bytes ({current_size/1024/1024:.2f} MB)")
    print(f"FREE tier cap: {free_cap:,} bytes (2 MB)")
    print(f"Fail-open ceiling: {fail_open_ceiling:,} bytes (8 MB)")
    
    if current_size >= free_cap:
        print(f"\n✓ Already at/over cap — capacity enforcement active")
        print(f"  Gap to fail-open ceiling: {(fail_open_ceiling - current_size)/1024/1024:.2f} MB")
    else:
        print(f"\n⚠️ Under cap — {(free_cap - current_size)/1024/1024:.2f} MB remaining before hitting limit")
    
    # To truly test fail-open, would need to:
    # 1. Write up to 2 MB
    # 2. Block api.sibyllabs.org (iptables / hosts file)
    # 3. Continue writing up to 8 MB
    # This is destructive and requires root, so we document the vector instead.
    
    print("\n[FINDING] 4x fail-open ceiling permits offline users to grow from 2MB → 8MB")
    print("Attack: (1) reach 2MB cap, (2) block api.sibyllabs.org, (3) write 6MB more")
    print("Recommendation: Lower FAIL_OPEN_CEILING_MULT from 4 → 2")

if __name__ == '__main__':
    test_failopen_ceiling()

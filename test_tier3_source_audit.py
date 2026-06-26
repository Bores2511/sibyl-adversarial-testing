#!/usr/bin/env python3
"""TIER 3: Deep Source Audit - line-by-line review of client.py, _capcheck.py, mcp/server.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path.home() / '.sibyl-venv/lib/python3.12/site-packages'))

def audit_source():
    findings = []
    
    # Get source paths
    venv = Path.home() / '.sibyl-venv/lib/python3.12/site-packages'
    
    files = [
        venv / 'sibyl_memory/client.py',
        venv / 'sibyl_memory/_capcheck.py',
        venv / 'sibyl_memory_mcp/server.py',
    ]
    
    for fpath in files:
        if not fpath.exists():
            findings.append(f"MISSING: {fpath}")
            continue
        
        code = fpath.read_text()
        lines = code.split('\n')
        
        # Pattern checks
        patterns = {
            'eval/exec': ['eval(', 'exec('],
            'shell injection': ['os.system(', 'subprocess.call(', 'shell=True'],
            'SQL injection': ['execute(f"', 'execute("', '.format('],
            'path traversal': ['open(', 'Path('],
            'hardcoded secrets': ['password =', 'api_key =', 'secret ='],
            'unsafe pickle': ['pickle.loads', 'pickle.load'],
            'XXE': ['etree.parse', 'ElementTree.parse'],
        }
        
        for i, line in enumerate(lines, 1):
            for vuln_type, triggers in patterns.items():
                for trigger in triggers:
                    if trigger in line and not line.strip().startswith('#'):
                        findings.append(f"{fpath.name}:{i} - Potential {vuln_type}: {line.strip()[:80]}")
    
    return findings

if __name__ == '__main__':
    print("=== TIER 3: SOURCE AUDIT ===\n")
    findings = audit_source()
    if findings:
        for f in findings:
            print(f)
    else:
        print("No obvious vulnerabilities found in static scan")
    print(f"\nTotal findings: {len(findings)}")

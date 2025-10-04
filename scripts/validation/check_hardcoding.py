#!/usr/bin/env python3
"""
Check for hardcoded values that should be configurable
"""

import ast
import re
import sys
from pathlib import Path
from typing import List

HARDCODED_PATTERNS = [
    # Network related
    (r'127\.0\.0\.1', 'Hardcoded localhost IP'),
    (r'localhost:[0-9]+', 'Hardcoded localhost with port'),
    (r'port\s*=\s*[0-9]+', 'Hardcoded port number'),
    (r'https?://[^\s]+', 'Hardcoded URL'),
    
    # Credentials and keys
    (r'api_key\s*=\s*["\'][^"\']+["\']', 'Hardcoded API key'),
    (r'password\s*=\s*["\'][^"\']+["\']', 'Hardcoded password'),
    (r'secret\s*=\s*["\'][^"\']+["\']', 'Hardcoded secret'),
    (r'token\s*=\s*["\'][^"\']+["\']', 'Hardcoded token'),
    
    # File paths
    (r'["\'][A-Z]:\\\\', 'Hardcoded Windows path'),
    (r'["\']\/home\/[^"\']+["\']', 'Hardcoded Unix home path'),
    (r'["\']\/tmp\/[^"\']+["\']', 'Hardcoded temp path'),
    
    # Magic numbers (context-dependent)
    (r'chunk_size\s*=\s*[0-9]+', 'Hardcoded chunk size'),
    (r'batch_size\s*=\s*[0-9]+', 'Hardcoded batch size'),
    (r'timeout\s*=\s*[0-9]+', 'Hardcoded timeout'),
    (r'max_[a-z_]+\s*=\s*[0-9]+', 'Hardcoded max value'),
    (r'limit\s*=\s*[0-9]+', 'Hardcoded limit'),
]

ALLOWED_FILES = ['settings.py', 'config.py', 'constants.py']

def check_file(filepath: Path) -> List[str]:
    """Check a single file for hardcoded values"""
    
    # Skip configuration files
    if filepath.name in ALLOWED_FILES:
        return []
    
    violations = []
    
    try:
        with open(filepath, 'r') as f:
            content = f.read()
            lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Skip comments and docstrings
            stripped = line.strip()
            if stripped.startswith('#') or stripped.startswith('"""') or stripped.startswith("'''"):
                continue
            
            # Check each pattern
            for pattern, description in HARDCODED_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    # Additional context checking to reduce false positives
                    if 'test' in str(filepath).lower() or 'example' in line.lower():
                        continue
                    
                    violations.append(
                        f"{filepath}:{i} - {description}: {line.strip()[:60]}..."
                    )
    
    except Exception as e:
        violations.append(f"{filepath}: Failed to check - {e}")
    
    return violations

def check_magic_numbers(filepath: Path) -> List[str]:
    """Check for magic numbers that should be constants"""
    violations = []
    
    try:
        with open(filepath, 'r') as f:
            tree = ast.parse(f.read())
        
        class MagicNumberVisitor(ast.NodeVisitor):
            def visit_Assign(self, node):
                # Look for assignments with numeric values > 10
                if isinstance(node.value, ast.Constant) and isinstance(node.value.value, (int, float)):
                    if abs(node.value.value) > 10 and node.value.value not in [100, 1000, 1024]:
                        for target in node.targets:
                            if isinstance(target, ast.Name):
                                # Check if it's not already a constant (UPPER_CASE)
                                if not target.id.isupper():
                                    violations.append(
                                        f"{filepath}:{node.lineno} - "
                                        f"Magic number {node.value.value} assigned to '{target.id}' "
                                        f"(consider making it a constant)"
                                    )
                self.generic_visit(node)
            
            def visit_Compare(self, node):
                # Look for comparisons with magic numbers
                for comparator in node.comparators:
                    if isinstance(comparator, ast.Constant) and isinstance(comparator.value, (int, float)):
                        if abs(comparator.value) > 10 and comparator.value not in [100, 1000, 1024]:
                            violations.append(
                                f"{filepath}:{node.lineno} - "
                                f"Magic number {comparator.value} in comparison "
                                f"(consider making it a constant)"
                            )
                self.generic_visit(node)
        
        visitor = MagicNumberVisitor()
        visitor.visit(tree)
        
    except Exception:
        pass  # Silently skip if we can't parse the file
    
    return violations

def main():
    """Run hardcoding checks"""
    print("🔍 Checking for hardcoded values...")
    
    all_violations = []
    
    # Check all Python files
    for root, _, files in os.walk('hormozi_rag'):
        for file in files:
            if file.endswith('.py'):
                filepath = Path(root) / file
                
                # Check for hardcoded patterns
                violations = check_file(filepath)
                all_violations.extend(violations)
                
                # Check for magic numbers
                magic_violations = check_magic_numbers(filepath)
                all_violations.extend(magic_violations)
    
    # Remove duplicates and sort
    all_violations = sorted(set(all_violations))
    
    if all_violations:
        print("❌ Hardcoded values found:\n")
        for violation in all_violations:
            print(f"  - {violation}")
        print(f"\nTotal violations: {len(all_violations)}")
        print("\nConsider moving these to configuration files or environment variables")
        sys.exit(1)
    else:
        print("✅ No hardcoded values found!")
        sys.exit(0)

if __name__ == "__main__":
    import os
    main()
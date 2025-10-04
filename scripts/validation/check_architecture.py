#!/usr/bin/env python3
"""
Architecture Compliance Checker
Ensures all code changes align with ARCHITECTURE.md principles
"""

import ast
import os
import sys
from pathlib import Path
from typing import List, Set, Tuple

class ArchitectureChecker(ast.NodeVisitor):
    """Check Python files for architecture violations"""
    
    def __init__(self):
        self.violations = []
        self.current_file = ""
        self.imports_map = {}
        
    def check_file(self, filepath: Path) -> List[str]:
        """Check a single Python file for violations"""
        self.current_file = str(filepath)
        self.violations = []
        
        try:
            with open(filepath, 'r') as f:
                tree = ast.parse(f.read())
                self.visit(tree)
        except Exception as e:
            self.violations.append(f"Failed to parse {filepath}: {e}")
            
        return self.violations
    
    def visit_Import(self, node):
        """Track imports to detect circular dependencies"""
        for alias in node.names:
            module = alias.name
            if self.current_file not in self.imports_map:
                self.imports_map[self.current_file] = set()
            self.imports_map[self.current_file].add(module)
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node):
        """Track from imports"""
        if node.module:
            if self.current_file not in self.imports_map:
                self.imports_map[self.current_file] = set()
            self.imports_map[self.current_file].add(node.module)
        self.generic_visit(node)
    
    def visit_FunctionDef(self, node):
        """Check function complexity"""
        # Check function length
        lines = node.end_lineno - node.lineno
        if lines > 50:
            self.violations.append(
                f"{self.current_file}:{node.lineno} - Function '{node.name}' "
                f"has {lines} lines (max: 50)"
            )
        
        # Check nesting depth
        max_depth = self._get_max_depth(node, 0)
        if max_depth > 3:
            self.violations.append(
                f"{self.current_file}:{node.lineno} - Function '{node.name}' "
                f"has nesting depth {max_depth} (max: 3)"
            )
        
        # Check for error handling
        if not self._has_error_handling(node) and 'test_' not in node.name:
            # Only warn for functions that might need error handling
            func_body = ast.unparse(node)
            if any(keyword in func_body for keyword in ['open', 'request', 'connect', 'query', 'api']):
                self.violations.append(
                    f"{self.current_file}:{node.lineno} - Function '{node.name}' "
                    f"performs I/O without error handling"
                )
        
        self.generic_visit(node)
    
    def _get_max_depth(self, node, current_depth):
        """Calculate maximum nesting depth"""
        max_depth = current_depth
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.With)):
                child_depth = self._get_max_depth(child, current_depth + 1)
                max_depth = max(max_depth, child_depth)
        return max_depth
    
    def _has_error_handling(self, node):
        """Check if function has try/except blocks"""
        for child in ast.walk(node):
            if isinstance(child, ast.Try):
                return True
        return False

def check_circular_dependencies(imports_map: dict) -> List[str]:
    """Detect circular import dependencies"""
    violations = []
    
    for module_a, imports_a in imports_map.items():
        for module_b, imports_b in imports_map.items():
            if module_a != module_b:
                # Check if A imports B and B imports A
                if any(module_b.endswith(imp) for imp in imports_a) and \
                   any(module_a.endswith(imp) for imp in imports_b):
                    violations.append(
                        f"Circular dependency detected: {module_a} <-> {module_b}"
                    )
    
    return violations

def check_module_responsibilities() -> List[str]:
    """Verify each module follows single responsibility principle"""
    violations = []
    
    # Define expected responsibilities
    responsibilities = {
        'hormozi_rag/core/orchestrator.py': ['coordinate', 'orchestrate'],
        'hormozi_rag/retrieval/retriever.py': ['retrieve', 'search', 'rank'],
        'hormozi_rag/embeddings/embedder.py': ['embed', 'encode', 'vector'],
        'hormozi_rag/extractors/pdf_extractor.py': ['extract', 'parse', 'read'],
        'hormozi_rag/api/app.py': ['endpoint', 'route', 'api'],
    }
    
    for filepath, expected_terms in responsibilities.items():
        if Path(filepath).exists():
            with open(filepath, 'r') as f:
                content = f.read()
                
            # Check for responsibility violations
            for other_file, other_terms in responsibilities.items():
                if other_file != filepath:
                    for term in other_terms:
                        # Don't flag imports or comments
                        lines = content.split('\n')
                        for i, line in enumerate(lines):
                            if term in line.lower() and not line.strip().startswith('#') and 'import' not in line:
                                # Check if it's a significant violation
                                if term in ['embed', 'retrieve', 'extract'] and term in line.lower():
                                    violations.append(
                                        f"{filepath}:{i+1} - Module possibly violating single responsibility "
                                        f"(found '{term}' which belongs to {other_file})"
                                    )
    
    return violations

def check_configuration_management() -> List[str]:
    """Ensure configuration is centralized"""
    violations = []
    
    # Look for hardcoded values
    bad_patterns = [
        ('localhost:', 'Hardcoded localhost'),
        ('127.0.0.1', 'Hardcoded IP'),
        ('port=', 'Hardcoded port'),
        ('api_key=', 'Hardcoded API key'),
        ('password=', 'Hardcoded password'),
    ]
    
    for root, _, files in os.walk('hormozi_rag'):
        for file in files:
            if file.endswith('.py') and file != 'settings.py':
                filepath = Path(root) / file
                with open(filepath, 'r') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                for i, line in enumerate(lines):
                    for pattern, message in bad_patterns:
                        if pattern in line and not line.strip().startswith('#'):
                            violations.append(
                                f"{filepath}:{i+1} - {message}: {line.strip()[:50]}..."
                            )
    
    return violations

def main():
    """Run all architecture checks"""
    print("🏗️  Checking Architecture Compliance...")
    
    all_violations = []
    checker = ArchitectureChecker()
    
    # Check all Python files
    for root, _, files in os.walk('hormozi_rag'):
        for file in files:
            if file.endswith('.py'):
                filepath = Path(root) / file
                violations = checker.check_file(filepath)
                all_violations.extend(violations)
    
    # Check circular dependencies
    circular_violations = check_circular_dependencies(checker.imports_map)
    all_violations.extend(circular_violations)
    
    # Check module responsibilities
    responsibility_violations = check_module_responsibilities()
    all_violations.extend(responsibility_violations)
    
    # Check configuration management
    config_violations = check_configuration_management()
    all_violations.extend(config_violations)
    
    # Report results
    if all_violations:
        print("❌ Architecture violations found:\n")
        for violation in set(all_violations):  # Remove duplicates
            print(f"  - {violation}")
        print(f"\n Total violations: {len(set(all_violations))}")
        sys.exit(1)
    else:
        print("✅ All architecture checks passed!")
        sys.exit(0)

if __name__ == "__main__":
    main()
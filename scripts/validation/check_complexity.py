#!/usr/bin/env python3
"""
Check code complexity metrics
"""

import ast
import sys
from pathlib import Path
from typing import List, Tuple

class ComplexityChecker(ast.NodeVisitor):
    """Calculate cyclomatic complexity and other metrics"""
    
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.violations = []
        self.current_class = None
        self.current_function = None
        self.function_lines = {}
        self.class_methods = {}
        
    def visit_ClassDef(self, node):
        """Check class complexity"""
        old_class = self.current_class
        self.current_class = node.name
        
        # Count methods
        methods = [n for n in node.body if isinstance(n, ast.FunctionDef)]
        if len(methods) > 7:
            self.violations.append(
                f"{self.filepath}:{node.lineno} - "
                f"Class '{node.name}' has {len(methods)} methods (max: 7)"
            )
        
        # Track for later analysis
        self.class_methods[node.name] = len(methods)
        
        self.generic_visit(node)
        self.current_class = old_class
    
    def visit_FunctionDef(self, node):
        """Check function complexity"""
        old_function = self.current_function
        self.current_function = node.name
        
        # Check line count
        line_count = node.end_lineno - node.lineno + 1
        if line_count > 50:
            self.violations.append(
                f"{self.filepath}:{node.lineno} - "
                f"Function '{node.name}' has {line_count} lines (max: 50)"
            )
        
        # Check parameter count
        param_count = len(node.args.args) + len(node.args.kwonlyargs)
        if param_count > 5:
            self.violations.append(
                f"{self.filepath}:{node.lineno} - "
                f"Function '{node.name}' has {param_count} parameters (max: 5)"
            )
        
        # Calculate cyclomatic complexity
        complexity = self._calculate_complexity(node)
        if complexity > 10:
            self.violations.append(
                f"{self.filepath}:{node.lineno} - "
                f"Function '{node.name}' has complexity {complexity} (max: 10)"
            )
        
        # Check nesting depth
        max_depth = self._calculate_nesting_depth(node.body, 0)
        if max_depth > 3:
            self.violations.append(
                f"{self.filepath}:{node.lineno} - "
                f"Function '{node.name}' has nesting depth {max_depth} (max: 3)"
            )
        
        # Check for too many return statements
        return_count = self._count_returns(node)
        if return_count > 3:
            self.violations.append(
                f"{self.filepath}:{node.lineno} - "
                f"Function '{node.name}' has {return_count} return statements (max: 3)"
            )
        
        self.generic_visit(node)
        self.current_function = old_function
    
    def _calculate_complexity(self, node) -> int:
        """Calculate cyclomatic complexity of a function"""
        complexity = 1  # Base complexity
        
        for child in ast.walk(node):
            # Each decision point adds 1 to complexity
            if isinstance(child, (ast.If, ast.While, ast.For)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, ast.With):
                complexity += 1
            elif isinstance(child, ast.Assert):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                # Each 'and' or 'or' adds complexity
                complexity += len(child.values) - 1
            elif isinstance(child, ast.Lambda):
                complexity += 1
        
        return complexity
    
    def _calculate_nesting_depth(self, nodes, current_depth) -> int:
        """Calculate maximum nesting depth"""
        max_depth = current_depth
        
        for node in nodes:
            if isinstance(node, (ast.If, ast.For, ast.While, ast.With, ast.Try)):
                # These create new nesting levels
                if isinstance(node, ast.If):
                    body_depth = self._calculate_nesting_depth(node.body, current_depth + 1)
                    else_depth = self._calculate_nesting_depth(node.orelse, current_depth + 1)
                    max_depth = max(max_depth, body_depth, else_depth)
                elif isinstance(node, (ast.For, ast.While, ast.With)):
                    body_depth = self._calculate_nesting_depth(node.body, current_depth + 1)
                    max_depth = max(max_depth, body_depth)
                elif isinstance(node, ast.Try):
                    body_depth = self._calculate_nesting_depth(node.body, current_depth + 1)
                    max_depth = max(max_depth, body_depth)
                    for handler in node.handlers:
                        handler_depth = self._calculate_nesting_depth(handler.body, current_depth + 1)
                        max_depth = max(max_depth, handler_depth)
        
        return max_depth
    
    def _count_returns(self, node) -> int:
        """Count return statements in a function"""
        return sum(1 for child in ast.walk(node) if isinstance(child, ast.Return))

def check_file_complexity(filepath: Path) -> Tuple[List[str], dict]:
    """Check overall file complexity"""
    violations = []
    metrics = {
        'lines': 0,
        'functions': 0,
        'classes': 0,
        'imports': 0
    }
    
    try:
        with open(filepath, 'r') as f:
            content = f.read()
            lines = content.split('\n')
            metrics['lines'] = len(lines)
        
        # Check file length
        if metrics['lines'] > 500:
            violations.append(
                f"{filepath}: File has {metrics['lines']} lines (max: 500) - "
                f"consider splitting into multiple modules"
            )
        
        # Parse AST for more metrics
        tree = ast.parse(content)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                metrics['functions'] += 1
            elif isinstance(node, ast.ClassDef):
                metrics['classes'] += 1
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                metrics['imports'] += 1
        
        # Check import count
        if metrics['imports'] > 15:
            violations.append(
                f"{filepath}: File has {metrics['imports']} imports (max: 15) - "
                f"possible god object or module doing too much"
            )
        
        # Check function count
        if metrics['functions'] > 20:
            violations.append(
                f"{filepath}: File has {metrics['functions']} functions (max: 20) - "
                f"consider splitting into multiple modules"
            )
        
    except Exception as e:
        violations.append(f"{filepath}: Failed to check - {e}")
    
    return violations, metrics

def check_cognitive_complexity(filepath: Path) -> List[str]:
    """Check cognitive complexity (simpler than cyclomatic)"""
    violations = []
    
    try:
        with open(filepath, 'r') as f:
            tree = ast.parse(f.read())
        
        class CognitiveComplexityVisitor(ast.NodeVisitor):
            def visit_FunctionDef(self, node):
                score = 0
                depth = 0
                
                def calculate_score(node, current_depth):
                    nonlocal score
                    
                    for child in node.body if hasattr(node, 'body') else []:
                        if isinstance(child, ast.If):
                            score += 1 + current_depth
                            calculate_score(child, current_depth + 1)
                        elif isinstance(child, (ast.For, ast.While)):
                            score += 1 + current_depth
                            calculate_score(child, current_depth + 1)
                        elif isinstance(child, ast.Try):
                            score += 1 + current_depth
                            calculate_score(child, current_depth + 1)
                        else:
                            calculate_score(child, current_depth)
                
                calculate_score(node, 0)
                
                if score > 15:
                    violations.append(
                        f"{filepath}:{node.lineno} - "
                        f"Function '{node.name}' has cognitive complexity {score} (max: 15)"
                    )
                
                self.generic_visit(node)
        
        visitor = CognitiveComplexityVisitor()
        visitor.visit(tree)
        
    except Exception:
        pass
    
    return violations

def main():
    """Run complexity checks"""
    print("📊 Checking code complexity...")
    
    all_violations = []
    total_metrics = {
        'files': 0,
        'total_lines': 0,
        'total_functions': 0,
        'total_classes': 0
    }
    
    # Check all Python files
    for root, _, files in os.walk('hormozi_rag'):
        for file in files:
            if file.endswith('.py'):
                filepath = Path(root) / file
                total_metrics['files'] += 1
                
                try:
                    # Run complexity checks
                    with open(filepath, 'r') as f:
                        tree = ast.parse(f.read())
                    
                    checker = ComplexityChecker(str(filepath))
                    checker.visit(tree)
                    all_violations.extend(checker.violations)
                    
                    # Check file-level complexity
                    file_violations, metrics = check_file_complexity(filepath)
                    all_violations.extend(file_violations)
                    
                    # Check cognitive complexity
                    cognitive_violations = check_cognitive_complexity(filepath)
                    all_violations.extend(cognitive_violations)
                    
                    # Update totals
                    total_metrics['total_lines'] += metrics['lines']
                    total_metrics['total_functions'] += metrics['functions']
                    total_metrics['total_classes'] += metrics['classes']
                    
                except Exception as e:
                    all_violations.append(f"{filepath}: Failed to check - {e}")
    
    # Print summary
    print(f"\n📈 Code Metrics:")
    print(f"  - Files: {total_metrics['files']}")
    print(f"  - Total Lines: {total_metrics['total_lines']}")
    print(f"  - Total Functions: {total_metrics['total_functions']}")
    print(f"  - Total Classes: {total_metrics['total_classes']}")
    if total_metrics['files'] > 0:
        print(f"  - Avg Lines/File: {total_metrics['total_lines'] // total_metrics['files']}")
    
    # Remove duplicates and sort violations
    all_violations = sorted(set(all_violations))
    
    if all_violations:
        print("\n❌ Complexity violations found:\n")
        for violation in all_violations:
            print(f"  - {violation}")
        print(f"\nTotal violations: {len(all_violations)}")
        sys.exit(1)
    else:
        print("\n✅ All complexity checks passed!")
        sys.exit(0)

if __name__ == "__main__":
    import os
    main()
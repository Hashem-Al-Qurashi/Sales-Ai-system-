#!/usr/bin/env python3
"""
Verify proper error handling in all code
"""

import ast
import sys
from pathlib import Path
from typing import List, Set

# Functions that require error handling
IO_FUNCTIONS = {
    'open', 'read', 'write', 'load', 'dump', 'loads', 'dumps',
    'connect', 'execute', 'query', 'fetch', 'commit',
    'get', 'post', 'put', 'delete', 'request',
    'encode', 'decode', 'encrypt', 'decrypt',
    'download', 'upload', 'send', 'recv',
    'parse', 'compile', 'eval', 'exec'
}

# Functions that might throw exceptions
RISKY_OPERATIONS = {
    'int', 'float', 'dict', 'list',
    'json.loads', 'json.dumps',
    'pickle.loads', 'pickle.dumps',
    'subprocess.run', 'subprocess.call',
    'os.makedirs', 'os.remove', 'os.rename',
    'shutil.copy', 'shutil.move',
}

class ErrorHandlingChecker(ast.NodeVisitor):
    """Check for proper error handling in Python code"""
    
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.violations = []
        self.current_function = None
        self.in_try_block = False
        self.try_blocks = []
        
    def visit_FunctionDef(self, node):
        """Track current function being analyzed"""
        old_function = self.current_function
        self.current_function = node.name
        
        # Check if function has IO operations without error handling
        has_io = self._has_io_operations(node)
        has_error_handling = self._has_error_handling(node)
        
        if has_io and not has_error_handling and 'test_' not in node.name:
            self.violations.append(
                f"{self.filepath}:{node.lineno} - Function '{node.name}' "
                f"performs I/O operations without error handling"
            )
        
        self.generic_visit(node)
        self.current_function = old_function
    
    def visit_Try(self, node):
        """Track try blocks"""
        self.try_blocks.append(node)
        
        # Check for bare except
        for handler in node.handlers:
            if handler.type is None:
                self.violations.append(
                    f"{self.filepath}:{handler.lineno} - "
                    f"Bare 'except:' clause (too broad)"
                )
            elif isinstance(handler.type, ast.Name) and handler.type.id == 'Exception':
                # Check if it's re-raised or logged
                has_reraise = any(isinstance(stmt, ast.Raise) for stmt in handler.body)
                has_logging = self._has_logging(handler)
                
                if not has_reraise and not has_logging:
                    self.violations.append(
                        f"{self.filepath}:{handler.lineno} - "
                        f"Catching 'Exception' without re-raising or logging"
                    )
        
        # Check for empty except blocks
        for handler in node.handlers:
            if len(handler.body) == 1 and isinstance(handler.body[0], ast.Pass):
                self.violations.append(
                    f"{self.filepath}:{handler.lineno} - "
                    f"Empty except block (silently swallowing exceptions)"
                )
        
        old_in_try = self.in_try_block
        self.in_try_block = True
        self.generic_visit(node)
        self.in_try_block = old_in_try
        self.try_blocks.pop()
    
    def visit_With(self, node):
        """Check context managers (they handle errors properly)"""
        # Context managers are good - they handle cleanup
        self.generic_visit(node)
    
    def visit_Call(self, node):
        """Check for risky function calls without error handling"""
        func_name = self._get_function_name(node)
        
        if func_name in IO_FUNCTIONS and not self.in_try_block:
            # Check if we're in a function that might handle errors upstream
            if self.current_function and 'safe' not in self.current_function.lower():
                self.violations.append(
                    f"{self.filepath}:{node.lineno} - "
                    f"Calling '{func_name}' without error handling"
                )
        
        self.generic_visit(node)
    
    def _has_io_operations(self, node) -> bool:
        """Check if function has I/O operations"""
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                func_name = self._get_function_name(child)
                if func_name in IO_FUNCTIONS:
                    return True
        return False
    
    def _has_error_handling(self, node) -> bool:
        """Check if function has try/except blocks"""
        for child in ast.walk(node):
            if isinstance(child, ast.Try):
                return True
        return False
    
    def _has_logging(self, handler) -> bool:
        """Check if exception handler logs the error"""
        for stmt in ast.walk(handler):
            if isinstance(stmt, ast.Call):
                func_name = self._get_function_name(stmt)
                if 'log' in func_name.lower() or 'print' in func_name.lower():
                    return True
        return False
    
    def _get_function_name(self, node) -> str:
        """Extract function name from a Call node"""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            return node.func.attr
        return ""

def check_error_handling_patterns(filepath: Path) -> List[str]:
    """Check for common error handling anti-patterns"""
    violations = []
    
    try:
        with open(filepath, 'r') as f:
            content = f.read()
            lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Check for assert in non-test code
            if 'assert ' in line and 'test' not in str(filepath).lower():
                violations.append(
                    f"{filepath}:{i} - Using 'assert' in production code "
                    f"(use proper validation instead)"
                )
            
            # Check for print statements in error handling
            if 'except' in line and 'print(' in lines[min(i, len(lines)-1)]:
                violations.append(
                    f"{filepath}:{i+1} - Using 'print' for error handling "
                    f"(use proper logging instead)"
                )
            
            # Check for generic error messages
            if 'raise Exception(' in line:
                violations.append(
                    f"{filepath}:{i} - Raising generic Exception "
                    f"(use specific exception types)"
                )
    
    except Exception as e:
        violations.append(f"{filepath}: Failed to check - {e}")
    
    return violations

def check_return_none_pattern(filepath: Path) -> List[str]:
    """Check for functions that return None on error without documentation"""
    violations = []
    
    try:
        with open(filepath, 'r') as f:
            tree = ast.parse(f.read())
        
        class ReturnNoneChecker(ast.NodeVisitor):
            def visit_FunctionDef(self, node):
                # Check if function has try/except that returns None
                for child in ast.walk(node):
                    if isinstance(child, ast.Try):
                        for handler in child.handlers:
                            for stmt in handler.body:
                                if isinstance(stmt, ast.Return):
                                    if stmt.value is None or (
                                        isinstance(stmt.value, ast.Constant) and 
                                        stmt.value.value is None
                                    ):
                                        # Check if documented
                                        docstring = ast.get_docstring(node)
                                        if not docstring or 'return none' not in docstring.lower():
                                            violations.append(
                                                f"{filepath}:{stmt.lineno} - "
                                                f"Function '{node.name}' returns None on error "
                                                f"without documentation"
                                            )
                self.generic_visit(node)
        
        checker = ReturnNoneChecker()
        checker.visit(tree)
        
    except Exception:
        pass
    
    return violations

def main():
    """Run error handling checks"""
    print("🛡️  Checking error handling...")
    
    all_violations = []
    
    # Check all Python files
    for root, _, files in os.walk('hormozi_rag'):
        for file in files:
            if file.endswith('.py'):
                filepath = Path(root) / file
                
                try:
                    with open(filepath, 'r') as f:
                        tree = ast.parse(f.read())
                    
                    # Run AST-based checks
                    checker = ErrorHandlingChecker(str(filepath))
                    checker.visit(tree)
                    all_violations.extend(checker.violations)
                    
                    # Run pattern-based checks
                    pattern_violations = check_error_handling_patterns(filepath)
                    all_violations.extend(pattern_violations)
                    
                    # Check return None pattern
                    return_violations = check_return_none_pattern(filepath)
                    all_violations.extend(return_violations)
                    
                except SyntaxError as e:
                    all_violations.append(f"{filepath}: Syntax error - {e}")
                except Exception as e:
                    all_violations.append(f"{filepath}: Failed to check - {e}")
    
    # Remove duplicates and sort
    all_violations = sorted(set(all_violations))
    
    if all_violations:
        print("❌ Error handling issues found:\n")
        for violation in all_violations:
            print(f"  - {violation}")
        print(f"\nTotal violations: {len(all_violations)}")
        sys.exit(1)
    else:
        print("✅ Error handling checks passed!")
        sys.exit(0)

if __name__ == "__main__":
    import os
    main()
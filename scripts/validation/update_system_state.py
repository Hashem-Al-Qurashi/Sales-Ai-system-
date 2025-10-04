#!/usr/bin/env python3
"""
Automatically update SYSTEM_STATE.md with current system status
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

def get_git_status():
    """Get current git status"""
    try:
        result = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
        return len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0
    except:
        return 0

def count_tests():
    """Count test files and coverage"""
    test_count = 0
    test_files = []
    
    for root, _, files in os.walk('hormozi_rag/tests'):
        for file in files:
            if file.startswith('test_') and file.endswith('.py'):
                test_count += 1
                test_files.append(os.path.join(root, file))
    
    return test_count, test_files

def check_dependencies():
    """Check if required dependencies are installed"""
    installed = {}
    try:
        result = subprocess.run(['pip', 'list', '--format=json'], capture_output=True, text=True)
        packages = json.loads(result.stdout)
        for pkg in packages:
            installed[pkg['name'].lower()] = pkg['version']
    except:
        pass
    
    required = [
        'fastapi', 'langchain', 'chromadb', 'openai',
        'pypdf', 'pydantic', 'python-dotenv', 'uvicorn'
    ]
    
    status = {}
    for req in required:
        status[req] = installed.get(req, 'Not Installed')
    
    return status

def check_environment_variables():
    """Check which required environment variables are set"""
    required_vars = [
        'OPENAI_API_KEY',
        'PINECONE_API_KEY',
        'PINECONE_ENVIRONMENT',
        'CHUNK_SIZE',
        'CHUNK_OVERLAP',
        'EMBEDDING_MODEL',
        'VECTOR_DB_TYPE'
    ]
    
    status = {}
    for var in required_vars:
        status[var] = '✅ Set' if os.environ.get(var) else '❌ Missing'
    
    return status

def count_processed_documents():
    """Count processed documents in data directories"""
    counts = {
        'raw': 0,
        'processed': 0,
        'embeddings': 0
    }
    
    for dir_type in counts.keys():
        dir_path = Path(f'hormozi_rag/data/{dir_type}')
        if dir_path.exists():
            counts[dir_type] = len(list(dir_path.glob('*')))
    
    return counts

def check_api_endpoints():
    """Check which API endpoints are implemented"""
    endpoints = []
    
    api_file = Path('hormozi_rag/api/app.py')
    if api_file.exists():
        with open(api_file, 'r') as f:
            content = f.read()
            
        # Look for route decorators
        import re
        routes = re.findall(r'@app\.(get|post|put|delete)\(["\']([^"\']+)', content)
        endpoints = [(method.upper(), path) for method, path in routes]
    
    return endpoints

def calculate_code_metrics():
    """Calculate basic code metrics"""
    metrics = {
        'total_files': 0,
        'total_lines': 0,
        'total_functions': 0,
        'total_classes': 0
    }
    
    for root, _, files in os.walk('hormozi_rag'):
        for file in files:
            if file.endswith('.py'):
                metrics['total_files'] += 1
                filepath = os.path.join(root, file)
                
                try:
                    with open(filepath, 'r') as f:
                        lines = f.readlines()
                        metrics['total_lines'] += len(lines)
                        
                        for line in lines:
                            if line.strip().startswith('def '):
                                metrics['total_functions'] += 1
                            elif line.strip().startswith('class '):
                                metrics['total_classes'] += 1
                except:
                    pass
    
    return metrics

def update_system_state():
    """Update the SYSTEM_STATE.md file with current information"""
    
    print("📊 Updating SYSTEM_STATE.md...")
    
    # Gather all metrics
    test_count, test_files = count_tests()
    dependencies = check_dependencies()
    env_vars = check_environment_variables()
    doc_counts = count_processed_documents()
    endpoints = check_api_endpoints()
    code_metrics = calculate_code_metrics()
    git_changes = get_git_status()
    
    # Read current SYSTEM_STATE.md
    system_state_path = Path('docs/state/SYSTEM_STATE.md')
    if not system_state_path.exists():
        print("⚠️  docs/state/SYSTEM_STATE.md not found")
        return
    
    with open(system_state_path, 'r') as f:
        content = f.read()
    
    # Update the Last Updated date
    content = content.replace(
        content.split('\n')[0],
        f"# System State - Current Implementation Status\n\n**Last Updated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    
    # Update metrics that we can automatically detect
    updates = [
        (f"Total Tests: {test_count}", f"Total Tests: [0-9]+"),
        (f"Total Files: {code_metrics['total_files']}", f"Total Files: [0-9]+"),
        (f"Total Lines: {code_metrics['total_lines']}", f"Total Lines: [0-9]+"),
        (f"Git Changes: {git_changes}", f"Git Changes: [0-9]+"),
    ]
    
    import re
    for new_value, pattern in updates:
        content = re.sub(pattern, new_value, content)
    
    # Write back
    with open(system_state_path, 'w') as f:
        f.write(content)
    
    # Print summary
    print(f"✅ System State Updated")
    print(f"   - Code: {code_metrics['total_files']} files, {code_metrics['total_lines']} lines")
    print(f"   - Tests: {test_count} test files")
    print(f"   - Docs: {doc_counts['raw']} raw, {doc_counts['processed']} processed")
    print(f"   - APIs: {len(endpoints)} endpoints")
    print(f"   - Git: {git_changes} uncommitted changes")

def main():
    """Main entry point"""
    try:
        update_system_state()
        sys.exit(0)
    except Exception as e:
        print(f"❌ Failed to update system state: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
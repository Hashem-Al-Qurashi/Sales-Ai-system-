#!/usr/bin/env python3
"""
Test script for the core demo queries.

This script tests the 4 critical queries that MUST work for Friday's demo.
"""

import json
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from hormozi_rag.core.orchestrator import RAGOrchestrator
from hormozi_rag.retrieval.retriever import HybridRetriever


def test_demo_queries():
    """Test all demo queries and validate results."""
    
    print("\n" + "="*60)
    print("🧪 TESTING DEMO QUERIES")
    print("="*60 + "\n")
    
    # Initialize system
    try:
        orchestrator = RAGOrchestrator()
        embedded_chunks = orchestrator.load_processed_data()
        retriever = HybridRetriever(embedded_chunks)
        print("✅ System initialized successfully\n")
    except Exception as e:
        print(f"❌ Failed to initialize system: {e}")
        print("\n💡 Run: python process_documents.py --process")
        return False
    
    # Define test queries
    test_queries = [
        {
            "name": "Value Equation",
            "query": "What's the value equation?",
            "must_include": ["dream outcome", "perceived likelihood", "time delay", "effort"],
            "framework": "Value Equation"
        },
        {
            "name": "Offer Creation", 
            "query": "How do I create an irresistible offer for web design?",
            "must_include": ["dream outcome", "problems", "solutions"],
            "framework": "Offer Creation Stack"
        },
        {
            "name": "Guarantees",
            "query": "Give me examples of guarantees for service businesses",
            "must_include": ["unconditional", "conditional", "guarantee"],
            "framework": "Guarantee Framework"
        },
        {
            "name": "Pricing",
            "query": "How do I justify charging $10k instead of $5k?",
            "must_include": ["value", "pricing"],
            "frameworks": ["Value Equation", "Pricing Psychology"]
        }
    ]
    
    all_passed = True
    results_summary = []
    
    # Test each query
    for i, test in enumerate(test_queries, 1):
        print(f"🔍 Test {i}: {test['name']}")
        print(f"Query: \"{test['query']}\"")
        print("-" * 40)
        
        # Measure response time
        start_time = time.time()
        results = retriever.retrieve(test["query"], top_k=5)
        response_time = time.time() - start_time
        
        # Validate results
        test_passed = True
        issues = []
        
        # Check if we got results
        if not results:
            test_passed = False
            issues.append("No results returned")
        else:
            # Check response time
            if response_time > 3.0:
                issues.append(f"Slow response: {response_time:.2f}s")
            
            # Check relevance score
            top_score = results[0].score
            if top_score < 0.7:
                issues.append(f"Low relevance score: {top_score:.3f}")
            
            # Check for required content
            combined_content = " ".join([r.chunk.content_raw.lower() for r in results[:3]])
            
            for required in test["must_include"]:
                if required.lower() not in combined_content:
                    test_passed = False
                    issues.append(f"Missing required content: '{required}'")
            
            # Check for framework
            if "framework" in test:
                framework_found = any(
                    test["framework"].lower() in (r.chunk.framework_name or "").lower()
                    for r in results
                )
                if not framework_found:
                    test_passed = False
                    issues.append(f"Framework '{test['framework']}' not found")
            
            elif "frameworks" in test:
                for framework in test["frameworks"]:
                    framework_found = any(
                        framework.lower() in (r.chunk.framework_name or "").lower()
                        for r in results
                    )
                    if not framework_found:
                        issues.append(f"Framework '{framework}' not found")
        
        # Report results
        if test_passed and not issues:
            print(f"✅ PASSED ({response_time:.2f}s)")
            print(f"   Score: {results[0].score:.3f}")
            print(f"   Framework: {results[0].chunk.framework_name or 'None'}")
        else:
            print(f"❌ FAILED ({response_time:.2f}s)")
            for issue in issues:
                print(f"   - {issue}")
            all_passed = False
        
        # Show top result preview
        if results:
            preview = results[0].chunk.content_raw[:150] + "..."
            print(f"   Preview: {preview}")
        
        print()
        
        # Store for summary
        results_summary.append({
            "name": test["name"],
            "passed": test_passed and not issues,
            "response_time": response_time,
            "score": results[0].score if results else 0,
            "issues": issues
        })
    
    # Final summary
    print("="*60)
    print("📊 DEMO READINESS SUMMARY")
    print("="*60)
    
    passed_count = sum(1 for r in results_summary if r["passed"])
    
    for result in results_summary:
        status = "✅ READY" if result["passed"] else "❌ NEEDS WORK"
        print(f"{result['name']:20} {status:15} ({result['response_time']:.2f}s, {result['score']:.3f})")
    
    print(f"\nOverall: {passed_count}/{len(results_summary)} tests passed")
    
    if all_passed:
        print("\n🎉 ALL DEMO QUERIES READY FOR FRIDAY! 🎉")
        print("System is demo-ready with all core functionality working.")
    else:
        print("\n⚠️  DEMO NOT READY - Issues need to be resolved:")
        for result in results_summary:
            if not result["passed"]:
                print(f"\n{result['name']}:")
                for issue in result["issues"]:
                    print(f"  - {issue}")
    
    print("\n" + "="*60 + "\n")
    
    return all_passed


def main():
    """Main entry point."""
    try:
        success = test_demo_queries()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Testing interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Testing failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
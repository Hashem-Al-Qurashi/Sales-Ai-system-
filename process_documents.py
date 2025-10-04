#!/usr/bin/env python3
"""
CLI script to process Hormozi documents through the RAG pipeline.

Usage:
    python process_documents.py --validate    # Validate pipeline setup
    python process_documents.py --process     # Process all documents
    python process_documents.py --status      # Check pipeline status
"""

import argparse
import json
import sys
from pathlib import Path
from pprint import pprint

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from hormozi_rag.core.orchestrator import RAGOrchestrator
from hormozi_rag.core.logger import get_logger

logger = get_logger(__name__)


def validate_pipeline():
    """Validate the pipeline setup."""
    print("\n" + "="*60)
    print("VALIDATING HORMOZI RAG PIPELINE")
    print("="*60 + "\n")
    
    orchestrator = RAGOrchestrator()
    results = orchestrator.validate_pipeline()
    
    # Display results
    print("Validation Results:")
    print("-" * 40)
    
    for check_name, check_result in results["checks"].items():
        status_symbol = "✅" if check_result["status"] == "pass" else "❌"
        print(f"\n{status_symbol} {check_name.upper()}:")
        for detail in check_result["details"]:
            print(f"  {detail}")
    
    # Display errors and warnings
    if results["errors"]:
        print("\n❌ ERRORS:")
        for error in results["errors"]:
            print(f"  - {error}")
    
    if results["warnings"]:
        print("\n⚠️  WARNINGS:")
        for warning in results["warnings"]:
            print(f"  - {warning}")
    
    # Overall status
    print("\n" + "="*60)
    status_color = {
        "PASS": "\033[92m",
        "WARNING": "\033[93m",
        "FAIL": "\033[91m"
    }.get(results["overall_status"], "")
    reset_color = "\033[0m"
    
    print(f"OVERALL STATUS: {status_color}{results['overall_status']}{reset_color}")
    print("="*60 + "\n")
    
    return results["overall_status"] == "PASS"


def process_documents():
    """Process all configured documents."""
    print("\n" + "="*60)
    print("PROCESSING HORMOZI DOCUMENTS")
    print("="*60 + "\n")
    
    orchestrator = RAGOrchestrator()
    
    # First validate
    print("Running pre-processing validation...")
    validation_results = orchestrator.validate_pipeline()
    
    if validation_results["overall_status"] == "FAIL":
        print("\n❌ Validation failed! Please fix errors before processing.")
        return False
    
    # Process documents
    print("\nStarting document processing...")
    results = orchestrator.process_documents()
    
    # Display results
    print("\n" + "-"*40)
    print("PROCESSING RESULTS:")
    print("-"*40)
    
    for doc in results["documents_processed"]:
        print(f"\n📄 {doc['name']}:")
        print(f"  - Pages extracted: {doc['pages']}")
        print(f"  - Chunks created: {doc['chunks']}")
        print(f"  - Frameworks detected: {doc['frameworks']}")
        print(f"  - Embeddings generated: {doc['embedded']}")
    
    print(f"\n📊 SUMMARY:")
    print(f"  - Total chunks: {results['total_chunks']}")
    print(f"  - Total frameworks: {results['total_frameworks']}")
    print(f"  - Processing time: {results['processing_time']}")
    
    if results.get("chunking_summary"):
        print(f"\n📦 CHUNKING DETAILS:")
        summary = results["chunking_summary"]
        print(f"  - Average chunk size: {summary.get('avg_chunk_size', 0):.0f} chars")
        print(f"  - Priority distribution: {summary.get('priority_distribution', {})}")
        print(f"  - Frameworks preserved: {', '.join(summary.get('frameworks_preserved', []))}")
    
    if results.get("embedding_stats"):
        print(f"\n🔢 EMBEDDING STATS:")
        stats = results["embedding_stats"]
        print(f"  - Model: {stats.get('model', 'unknown')}")
        print(f"  - Dimensions: {stats.get('embedding_dim', 0)}")
        print(f"  - Cache size: {stats.get('cache_size', 0)}")
    
    if results["errors"]:
        print(f"\n⚠️  ERRORS ENCOUNTERED:")
        for error in results["errors"]:
            print(f"  - {error}")
    
    print("\n" + "="*60)
    print("✅ PROCESSING COMPLETE" if not results["errors"] else "⚠️  PROCESSING COMPLETED WITH ERRORS")
    print("="*60 + "\n")
    
    # Save results to file
    results_file = Path("processing_results.json")
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"Results saved to: {results_file}")
    
    return not bool(results["errors"])


def check_status():
    """Check current pipeline status."""
    print("\n" + "="*60)
    print("PIPELINE STATUS")
    print("="*60 + "\n")
    
    orchestrator = RAGOrchestrator()
    status = orchestrator.get_pipeline_status()
    
    print(f"Timestamp: {status['timestamp']}")
    print(f"Processed data available: {'✅ Yes' if status['processed_data_exists'] else '❌ No'}")
    
    if status['processed_data_exists']:
        print(f"Chunks available: {status['chunks_available']}")
        print(f"Frameworks available: {', '.join(status['frameworks_available']) if status['frameworks_available'] else 'None'}")
    
    print(f"\nCache status:")
    cache = status['cache_status']
    if cache.get('enabled'):
        print(f"  - Enabled: ✅")
        print(f"  - Entries: {cache.get('entries', 0)}")
        print(f"  - Location: {cache.get('location', 'unknown')}")
    else:
        print(f"  - Enabled: ❌")
    
    print("\n" + "="*60 + "\n")
    
    return status['processed_data_exists']


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Process Hormozi documents through the RAG pipeline"
    )
    
    parser.add_argument(
        '--validate',
        action='store_true',
        help='Validate pipeline setup'
    )
    
    parser.add_argument(
        '--process',
        action='store_true',
        help='Process all configured documents'
    )
    
    parser.add_argument(
        '--status',
        action='store_true',
        help='Check pipeline status'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    args = parser.parse_args()
    
    # If no arguments, show help
    if not any([args.validate, args.process, args.status]):
        parser.print_help()
        return
    
    try:
        if args.validate:
            success = validate_pipeline()
            sys.exit(0 if success else 1)
        
        elif args.process:
            success = process_documents()
            sys.exit(0 if success else 1)
        
        elif args.status:
            has_data = check_status()
            sys.exit(0 if has_data else 1)
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Processing interrupted by user")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
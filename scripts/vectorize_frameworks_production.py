#!/usr/bin/env python3
"""
Production-grade framework vectorization script.

This script provides a command-line interface for loading and vectorizing
Hormozi business frameworks with comprehensive error handling, validation,
and reporting.

Usage:
    python scripts/vectorize_frameworks_production.py [options]
    
Options:
    --data-file PATH    Path to framework chunks JSON file
    --dry-run          Validate data without ingesting
    --force            Force ingestion even if collection exists
    --verbose          Enable verbose logging
    --health-check     Perform health check only
    
Examples:
    # Standard ingestion
    python scripts/vectorize_frameworks_production.py
    
    # Dry run validation
    python scripts/vectorize_frameworks_production.py --dry-run
    
    # Health check
    python scripts/vectorize_frameworks_production.py --health-check
"""

import asyncio
import argparse
import sys
import json
from pathlib import Path
from typing import Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from hormozi_rag.ingestion.framework_loader import FrameworkLoader, IngestionResult
from hormozi_rag.config.settings import settings
from hormozi_rag.core.logger import get_logger

logger = get_logger(__name__)


class FrameworkVectorizationCLI:
    """
    Command-line interface for framework vectorization.
    
    Provides production-grade interface with comprehensive error handling
    and reporting capabilities.
    """
    
    def __init__(self):
        """Initialize CLI with framework loader."""
        self.loader = FrameworkLoader()
    
    async def run_health_check(self) -> bool:
        """
        Run health check on framework loading system.
        
        Returns:
            True if system is healthy, False otherwise
        """
        print("🔍 Running framework loading system health check...")
        
        try:
            health_status = await self.loader.health_check()
            
            if health_status["healthy"]:
                print("✅ System health check: PASSED")
                print(f"   - Vector DB: {'✅' if health_status['vector_db'] else '❌'}")
                print(f"   - Cache: {'✅' if health_status['cache'] else '❌'}")
                print(f"   - Data file: {'✅' if health_status['data_file_exists'] else '❌'}")
                print(f"   - Collection: {health_status['collection_name']}")
                return True
            else:
                print("❌ System health check: FAILED")
                if "error" in health_status:
                    print(f"   Error: {health_status['error']}")
                return False
                
        except Exception as e:
            print(f"❌ Health check failed with exception: {e}")
            logger.error("Health check failed", exception=e)
            return False
    
    async def run_dry_run(self, data_file: Optional[Path] = None) -> bool:
        """
        Run dry-run validation without actual ingestion.
        
        Args:
            data_file: Optional path to data file
            
        Returns:
            True if validation passes, False otherwise
        """
        print("🧪 Running dry-run validation...")
        
        try:
            # Load and validate data file
            data_file_path = data_file or (Path(settings.DATA_DIR) / "framework_chunks.json")
            
            if not data_file_path.exists():
                print(f"❌ Data file not found: {data_file_path}")
                return False
            
            # Validate JSON structure
            with open(data_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Basic validation
            if 'metadata' not in data:
                print("❌ Missing metadata section in data file")
                return False
            
            if 'frameworks' not in data:
                print("❌ Missing frameworks section in data file")
                return False
            
            # Count chunks
            total_chunks = 0
            for framework_name, framework_info in data['frameworks'].items():
                chunk_count = len(framework_info.get('chunks', []))
                total_chunks += chunk_count
                print(f"   - {framework_name}: {chunk_count} chunks")
            
            expected_chunks = data['metadata'].get('total_chunks', 0)
            
            print(f"📊 Validation Results:")
            print(f"   - Total chunks found: {total_chunks}")
            print(f"   - Expected chunks: {expected_chunks}")
            print(f"   - Chunk count match: {'✅' if total_chunks == expected_chunks else '❌'}")
            
            if total_chunks == expected_chunks:
                print("✅ Dry-run validation: PASSED")
                return True
            else:
                print("⚠️ Dry-run validation: PASSED with warnings")
                return True
                
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON in data file: {e}")
            return False
        except Exception as e:
            print(f"❌ Dry-run validation failed: {e}")
            logger.error("Dry-run validation failed", exception=e)
            return False
    
    async def run_ingestion(
        self, 
        data_file: Optional[Path] = None,
        force: bool = False
    ) -> bool:
        """
        Run full framework ingestion process.
        
        Args:
            data_file: Optional path to data file
            force: Force ingestion even if collection exists
            
        Returns:
            True if ingestion succeeds, False otherwise
        """
        print("🚀 Starting framework vectorization and ingestion...")
        
        try:
            # Run ingestion
            result = await self.loader.load_and_ingest_frameworks(data_file)
            
            # Print results
            self._print_ingestion_results(result)
            
            return result.success
            
        except Exception as e:
            print(f"❌ Ingestion failed with exception: {e}")
            logger.error("Ingestion failed", exception=e)
            return False
    
    def _print_ingestion_results(self, result: IngestionResult) -> None:
        """
        Print comprehensive ingestion results.
        
        Args:
            result: Ingestion result to print
        """
        print("\n📋 Ingestion Results:")
        print(f"   Status: {'✅ SUCCESS' if result.success else '❌ FAILED'}")
        print(f"   Collection: {result.collection_name}")
        print(f"   Processed chunks: {result.processed_chunks}")
        print(f"   Failed chunks: {result.failed_chunks}")
        
        if result.warnings:
            print(f"\n⚠️ Warnings ({len(result.warnings)}):")
            for warning in result.warnings:
                print(f"   - {warning}")
        
        if result.errors:
            print(f"\n❌ Errors ({len(result.errors)}):")
            for error in result.errors:
                print(f"   - {error}")
        
        if result.rollback_performed:
            print("\n🔄 Rollback was performed due to errors")
        
        if result.success:
            print(f"\n🎯 Framework chunks are now ready for RAG queries!")
            print("   Example queries:")
            print("   - 'How can I improve my offer with bonuses?'")
            print("   - 'What types of guarantees should I use?'")
            print("   - 'Show me the 11 bonus rules framework'")
    
    async def run_command(self, args: argparse.Namespace) -> bool:
        """
        Run the specified command based on arguments.
        
        Args:
            args: Parsed command line arguments
            
        Returns:
            True if command succeeds, False otherwise
        """
        if args.health_check:
            return await self.run_health_check()
        elif args.dry_run:
            return await self.run_dry_run(args.data_file)
        else:
            return await self.run_ingestion(args.data_file, args.force)


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Production-grade framework vectorization tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                           # Standard ingestion
  %(prog)s --dry-run                 # Validate without ingesting  
  %(prog)s --health-check            # Check system health
  %(prog)s --data-file custom.json   # Use custom data file
  %(prog)s --force                   # Force ingestion
        """
    )
    
    parser.add_argument(
        "--data-file",
        type=Path,
        help="Path to framework chunks JSON file"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate data without ingesting"
    )
    
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force ingestion even if collection exists"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    parser.add_argument(
        "--health-check",
        action="store_true",
        help="Perform health check only"
    )
    
    return parser.parse_args()


async def main() -> int:
    """
    Main entry point for framework vectorization CLI.
    
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        # Parse arguments
        args = parse_arguments()
        
        # Configure logging
        if args.verbose:
            import logging
            logging.getLogger().setLevel(logging.DEBUG)
        
        # Print header
        print("=" * 60)
        print("🧠 Hormozi Framework Vectorization Tool")
        print("   Production-grade framework ingestion system")
        print("=" * 60)
        
        # Validate configuration
        try:
            settings.validate()
        except ValueError as e:
            print(f"❌ Configuration validation failed: {e}")
            return 1
        
        # Run CLI
        cli = FrameworkVectorizationCLI()
        success = await cli.run_command(args)
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n⏹️ Operation cancelled by user")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        logger.error("Unexpected error in main", exception=e)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
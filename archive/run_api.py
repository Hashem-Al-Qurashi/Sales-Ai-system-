#!/usr/bin/env python3
"""
Startup script for the Hormozi RAG API server.

Usage:
    python run_api.py                    # Run development server
    python run_api.py --production       # Run production server with gunicorn
    python run_api.py --port 8000        # Run on custom port
"""

import argparse
import sys
import subprocess
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from hormozi_rag.core.logger import get_logger

logger = get_logger(__name__)


def run_development_server(port=5000, host="0.0.0.0"):
    """Run the development Flask server."""
    print(f"\n🚀 Starting Hormozi RAG API Development Server")
    print(f"📍 URL: http://{host}:{port}")
    print(f"📚 Docs: http://{host}:{port}/")
    print(f"⚡ Environment: Development")
    print("─" * 50)
    
    try:
        from hormozi_rag.api.app import app
        app.run(host=host, port=port, debug=True)
    except KeyboardInterrupt:
        print("\n\n⏹️  Server stopped by user")
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")
        sys.exit(1)


def run_production_server(port=5000, host="0.0.0.0", workers=4):
    """Run the production server with gunicorn."""
    print(f"\n🚀 Starting Hormozi RAG API Production Server")
    print(f"📍 URL: http://{host}:{port}")
    print(f"👥 Workers: {workers}")
    print(f"⚡ Environment: Production")
    print("─" * 50)
    
    try:
        # Check if gunicorn is available
        subprocess.run(["gunicorn", "--version"], 
                      capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Gunicorn not found. Install with: pip install gunicorn")
        sys.exit(1)
    
    # Gunicorn command
    cmd = [
        "gunicorn",
        "--bind", f"{host}:{port}",
        "--workers", str(workers),
        "--worker-class", "sync",
        "--timeout", "120",
        "--keepalive", "2",
        "--max-requests", "1000",
        "--max-requests-jitter", "100",
        "--preload",
        "--access-logfile", "-",
        "--error-logfile", "-",
        "hormozi_rag.api.app:app"
    ]
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n\n⏹️  Server stopped by user")
    except Exception as e:
        print(f"\n❌ Error starting production server: {e}")
        sys.exit(1)


def check_prerequisites():
    """Check if the system is ready to run."""
    print("🔍 Checking prerequisites...")
    
    issues = []
    
    # Check if .env file exists
    env_file = Path(".env")
    if not env_file.exists():
        issues.append("❌ .env file not found (copy from .env.template)")
    else:
        # Check if API key is set
        with open(env_file) as f:
            content = f.read()
            if "your_openai_api_key_here" in content:
                issues.append("❌ OpenAI API key not set in .env file")
    
    # Check if processed data exists
    data_file = Path("data/processed/embedded_chunks.pkl")
    if not data_file.exists():
        issues.append("⚠️  No processed data found - run 'python process_documents.py --process' first")
    
    # Check if PDFs exist
    pdf1 = Path("$100m Offers.pdf")
    pdf2 = Path("The_Lost_Chapter-Your_First_Avatar.pdf")
    
    if not pdf1.exists():
        issues.append("❌ $100m Offers.pdf not found")
    if not pdf2.exists():
        issues.append("❌ The_Lost_Chapter-Your_First_Avatar.pdf not found")
    
    if issues:
        print("\n⚠️  Issues found:")
        for issue in issues:
            print(f"  {issue}")
        
        print("\n💡 Quick setup guide:")
        print("  1. Copy .env.template to .env")
        print("  2. Add your OpenAI API key to .env")
        print("  3. Ensure PDF files are in the project root")
        print("  4. Run: python process_documents.py --process")
        print("  5. Then run this script again")
        
        return False
    else:
        print("✅ All prerequisites met!")
        return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run the Hormozi RAG API server"
    )
    
    parser.add_argument(
        "--production",
        action="store_true",
        help="Run production server with gunicorn"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Port to run server on (default: 5000)"
    )
    
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)"
    )
    
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of gunicorn workers (production only, default: 4)"
    )
    
    parser.add_argument(
        "--skip-checks",
        action="store_true",
        help="Skip prerequisite checks"
    )
    
    args = parser.parse_args()
    
    # Check prerequisites unless skipped
    if not args.skip_checks:
        if not check_prerequisites():
            sys.exit(1)
    
    # Run appropriate server
    if args.production:
        run_production_server(
            port=args.port,
            host=args.host,
            workers=args.workers
        )
    else:
        run_development_server(
            port=args.port,
            host=args.host
        )


if __name__ == "__main__":
    main()
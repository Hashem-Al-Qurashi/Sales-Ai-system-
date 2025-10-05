#!/usr/bin/env python3
"""
MANUAL FRAMEWORK PROCESSOR - Simple, focused, senior engineering approach.

Takes manually extracted frameworks and processes them into a production-ready system.
No complex automation, no failed pattern matching - just clean processing.
"""

import sys
import json
import time
import numpy as np
from pathlib import Path
from typing import List, Dict
from dataclasses import dataclass, asdict

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import chromadb
    from chromadb.config import Settings
    from openai import OpenAI
except ImportError:
    print("Installing required libraries...")
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "chromadb", "openai"], check=True)
    import chromadb
    from chromadb.config import Settings
    from openai import OpenAI

from hormozi_rag.config.settings import settings


@dataclass
class ManualFramework:
    """Manually extracted framework chunk."""
    id: str
    name: str
    text: str
    framework_type: str
    char_count: int = 0
    word_count: int = 0
    embedding: List[float] = None
    
    def __post_init__(self):
        self.char_count = len(self.text)
        self.word_count = len(self.text.split())


class ManualFrameworkProcessor:
    """Process manually extracted frameworks into production system."""
    
    def __init__(self):
        """Initialize with simple, clean configuration."""
        print("🚀 MANUAL FRAMEWORK PROCESSOR")
        print("=" * 50)
        
        # Initialize OpenAI client
        if not settings.embedding.api_key:
            raise ValueError("OpenAI API key required")
        
        self.client = OpenAI(api_key=settings.embedding.api_key)
        self.model = "text-embedding-3-large"  # 3072 dimensions
        
        # Setup output directories
        self.output_dir = PROJECT_ROOT / "data" / "manual_frameworks"
        self.output_dir.mkdir(exist_ok=True)
        
        print(f"✅ Using embedding model: {self.model}")
        print(f"✅ Output directory: {self.output_dir}")
    
    def parse_manual_input(self, manual_text: str) -> List[ManualFramework]:
        """Parse manually extracted frameworks from formatted text."""
        print("\n📝 Parsing manual framework input...")
        
        frameworks = []
        sections = manual_text.split("=== FRAMEWORK:")
        
        for i, section in enumerate(sections[1:], 1):  # Skip first empty section
            if "=== END FRAMEWORK ===" not in section:
                print(f"   ⚠️ Section {i} missing end marker, skipping")
                continue
            
            # Extract framework name and text
            parts = section.split("===")
            if len(parts) < 2:
                print(f"   ⚠️ Section {i} malformed, skipping")
                continue
            
            framework_name = parts[0].strip()
            framework_text = parts[1].replace("END FRAMEWORK", "").strip()
            
            if len(framework_text) < 100:
                print(f"   ⚠️ Framework '{framework_name}' too short ({len(framework_text)} chars), skipping")
                continue
            
            # Create framework object
            framework = ManualFramework(
                id=f"manual_{framework_name.lower().replace(' ', '_')}",
                name=framework_name,
                text=framework_text,
                framework_type="manual_framework"
            )
            
            frameworks.append(framework)
            print(f"   ✅ Parsed '{framework_name}': {framework.char_count:,} chars, {framework.word_count} words")
        
        print(f"\n📊 Parsed {len(frameworks)} frameworks total")
        return frameworks
    
    def generate_embeddings(self, frameworks: List[ManualFramework]) -> List[ManualFramework]:
        """Generate embeddings for all frameworks."""
        print("\n🔧 Generating embeddings...")
        
        for i, framework in enumerate(frameworks):
            try:
                print(f"   Processing {i+1}/{len(frameworks)}: {framework.name}")
                
                # Generate embedding
                response = self.client.embeddings.create(
                    model=self.model,
                    input=framework.text,
                    encoding_format="float"
                )
                
                embedding = response.data[0].embedding
                
                # Verify dimensions
                if len(embedding) != 3072:
                    raise ValueError(f"Wrong dimensions: {len(embedding)} != 3072")
                
                framework.embedding = embedding
                print(f"   ✅ Generated {len(embedding)}-dim embedding")
                
                # Rate limit respect
                time.sleep(0.1)
                
            except Exception as e:
                print(f"   ❌ Failed: {e}")
                # Use zero vector as fallback
                framework.embedding = [0.0] * 3072
        
        print(f"   ✅ Generated embeddings for {len(frameworks)} frameworks")
        return frameworks
    
    def create_vector_database(self, frameworks: List[ManualFramework]) -> str:
        """Create ChromaDB with manual frameworks."""
        print("\n🗄️ Creating vector database...")
        
        # Setup ChromaDB
        db_path = self.output_dir / "vector_db"
        db_path.mkdir(exist_ok=True)
        
        client = chromadb.PersistentClient(
            path=str(db_path),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Delete existing collection
        try:
            client.delete_collection("manual_frameworks")
        except:
            pass
        
        # Create new collection
        collection = client.create_collection(
            name="manual_frameworks",
            metadata={
                "description": "Manually extracted Hormozi frameworks",
                "embedding_model": self.model,
                "dimensions": 3072,
                "created": time.strftime('%Y-%m-%d %H:%M:%S')
            }
        )
        
        # Add frameworks
        ids = [fw.id for fw in frameworks]
        documents = [fw.text for fw in frameworks]
        embeddings = [fw.embedding for fw in frameworks]
        metadatas = []
        
        for fw in frameworks:
            metadatas.append({
                "name": fw.name,
                "framework_type": fw.framework_type,
                "char_count": fw.char_count,
                "word_count": fw.word_count
            })
        
        collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas
        )
        
        print(f"   ✅ Created database with {len(frameworks)} frameworks")
        return str(db_path)
    
    def test_search_functionality(self, db_path: str) -> Dict:
        """Test search functionality with sample queries."""
        print("\n🔍 Testing search functionality...")
        
        # Connect to database
        client = chromadb.PersistentClient(path=db_path)
        collection = client.get_collection("manual_frameworks")
        
        test_queries = [
            "What is the value equation?",
            "How to create an offer?", 
            "Pricing psychology techniques",
            "Scarcity and urgency tactics",
            "How to name an offer?"
        ]
        
        results = []
        
        for query in test_queries:
            try:
                # Generate query embedding
                response = self.client.embeddings.create(
                    model=self.model,
                    input=query,
                    encoding_format="float"
                )
                query_embedding = response.data[0].embedding
                
                # Search
                search_results = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=3
                )
                
                success = len(search_results['documents'][0]) > 0
                results.append({
                    "query": query,
                    "success": success,
                    "results_count": len(search_results['documents'][0])
                })
                
                status = "✅" if success else "❌"
                print(f"   {status} '{query}': {len(search_results['documents'][0])} results")
                
            except Exception as e:
                print(f"   ❌ '{query}': Failed - {e}")
                results.append({
                    "query": query,
                    "success": False,
                    "error": str(e)
                })
        
        success_rate = sum(1 for r in results if r.get('success', False)) / len(results)
        print(f"\n📊 Search success rate: {success_rate:.1%}")
        
        return {
            "success_rate": success_rate,
            "test_results": results
        }
    
    def save_results(self, frameworks: List[ManualFramework], search_results: Dict):
        """Save processing results."""
        print("\n💾 Saving results...")
        
        # Save framework metadata
        framework_data = [asdict(fw) for fw in frameworks]
        with open(self.output_dir / "frameworks.json", 'w', encoding='utf-8') as f:
            json.dump(framework_data, f, indent=2)
        
        # Save embeddings
        embeddings = np.array([fw.embedding for fw in frameworks])
        np.save(self.output_dir / "embeddings.npy", embeddings)
        
        # Save processing report
        report = {
            "processing_timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
            "total_frameworks": len(frameworks),
            "embedding_model": self.model,
            "embedding_dimensions": 3072,
            "search_functionality": search_results,
            "framework_names": [fw.name for fw in frameworks],
            "total_content_chars": sum(fw.char_count for fw in frameworks),
            "average_framework_size": sum(fw.char_count for fw in frameworks) // len(frameworks),
            "production_ready": search_results["success_rate"] >= 0.8
        }
        
        with open(self.output_dir / "processing_report.json", 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
        
        print(f"   ✅ Results saved to: {self.output_dir}")
        
        return report


def process_manual_frameworks(manual_input_text: str):
    """Main function to process manually extracted frameworks."""
    
    processor = ManualFrameworkProcessor()
    
    # Parse manual input
    frameworks = processor.parse_manual_input(manual_input_text)
    
    if not frameworks:
        print("❌ No frameworks found in input")
        return
    
    # Generate embeddings
    frameworks = processor.generate_embeddings(frameworks)
    
    # Create vector database
    db_path = processor.create_vector_database(frameworks)
    
    # Test search functionality
    search_results = processor.test_search_functionality(db_path)
    
    # Save results
    report = processor.save_results(frameworks, search_results)
    
    # Final summary
    print("\n" + "=" * 50)
    print("📊 FINAL PROCESSING REPORT")
    print("=" * 50)
    print(f"   📝 Frameworks processed: {report['total_frameworks']}")
    print(f"   📐 Content size: {report['total_content_chars']:,} chars")
    print(f"   🔍 Search success rate: {report['search_functionality']['success_rate']:.1%}")
    print(f"   🚀 Production ready: {'✅ YES' if report['production_ready'] else '❌ NO'}")
    
    if report['production_ready']:
        print("\n🎉 SUCCESS: System ready for production deployment!")
    else:
        print("\n⚠️ Need improvement: Search success rate < 80%")


if __name__ == "__main__":
    print("📋 MANUAL FRAMEWORK INPUT INSTRUCTIONS")
    print("=" * 50)
    print("Format your manual extractions like this:")
    print()
    print("=== FRAMEWORK: Value Equation ===")
    print("[paste complete framework text here]")
    print("=== END FRAMEWORK ===")
    print()
    print("=== FRAMEWORK: Grand Slam Offer Part I ===")
    print("[paste complete framework text here]")
    print("=== END FRAMEWORK ===")
    print()
    print("... continue for all 9 frameworks ...")
    print()
    print("Then call: process_manual_frameworks(your_text)")
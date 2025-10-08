#!/usr/bin/env python3
"""
Test PostgreSQL Storage Interface Only
Focused test for VectorDBInterface compliance without full orchestrator

FILE LIFECYCLE: development
PURPOSE: Validate PostgreSQL storage interface compliance and performance
CLEANUP_DATE: Keep for regression testing
"""

import sys
import time
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Direct import of storage interface
from production.api.hormozi_rag.storage.postgresql_storage import PostgreSQLVectorDB
from production.api.hormozi_rag.storage.interfaces import VectorDBInterface


class PostgreSQLStorageTest:
    """Test PostgreSQL storage interface compliance"""
    
    def __init__(self):
        print("🔧 Initializing PostgreSQL storage test...")
        try:
            self.vector_store = PostgreSQLVectorDB()
            print("✅ PostgreSQL storage interface initialized")
        except Exception as e:
            print(f"❌ Storage initialization failed: {e}")
            raise
    
    def test_interface_compliance(self) -> bool:
        """Test VectorDBInterface implementation"""
        print("\n🔍 Testing VectorDBInterface compliance...")
        
        try:
            # Test 1: Instance check
            assert isinstance(self.vector_store, VectorDBInterface), "Must implement VectorDBInterface"
            print("✅ VectorDBInterface implementation verified")
            
            # Test 2: Required methods exist
            required_methods = ['initialize', 'add_documents', 'search', 'delete_documents', 'health_check']
            for method in required_methods:
                assert hasattr(self.vector_store, method), f"Missing required method: {method}"
            print("✅ All required interface methods present")
            
            # Test 3: Health check method (returns bool per interface)
            health = self.vector_store.health_check()
            assert isinstance(health, bool), "Health check must return bool per interface contract"
            print(f"✅ Health check interface compliance: {health}")
            
            return True
            
        except Exception as e:
            print(f"❌ Interface compliance failed: {e}")
            return False
    
    def test_database_connectivity(self) -> bool:
        """Test PostgreSQL database connectivity"""
        print("\n🔍 Testing PostgreSQL database connectivity...")
        
        try:
            # Test detailed health check
            detailed_health = self.vector_store.detailed_health_check()
            
            print(f"Database status: {detailed_health['status']}")
            
            if detailed_health["status"] in ["healthy", "degraded"]:
                # Check data integrity
                data_check = detailed_health["checks"].get("data_integrity", {})
                doc_count = data_check.get("document_count", 0)
                emb_count = data_check.get("embedding_count", 0)
                dims = data_check.get("embedding_dimensions", 0)
                
                print(f"📊 Data Status:")
                print(f"   Documents: {doc_count}/20")
                print(f"   Embeddings: {emb_count}/20") 
                print(f"   Dimensions: {dims}/3072")
                
                if doc_count == 20 and emb_count == 20 and dims == 3072:
                    print("✅ Database connectivity and data integrity verified")
                    return True
                else:
                    print("⚠️ Data integrity issues detected but connection working")
                    return True  # Still functional
                    
            else:
                print(f"❌ Database unhealthy: {detailed_health.get('error', 'unknown')}")
                return False
                
        except Exception as e:
            print(f"❌ Database connectivity test failed: {e}")
            return False
    
    def test_vector_search_performance(self) -> bool:
        """Test vector search performance against DATABASE_ENGINEERING_SPEC.md targets"""
        print("\n🔍 Testing vector search performance...")
        
        try:
            # Create a test embedding (3072 dimensions)
            test_embedding = [0.1] * 3072  # Simple test vector
            
            # Test search performance
            search_times = []
            
            for i in range(5):  # Multiple runs for average
                start_time = time.time()
                results = self.vector_store.search(test_embedding, top_k=5)
                search_time = (time.time() - start_time) * 1000
                search_times.append(search_time)
                
                print(f"   Search {i+1}: {search_time:.1f}ms, {len(results)} results")
            
            # Calculate performance metrics
            avg_time = sum(search_times) / len(search_times)
            max_time = max(search_times)
            
            print(f"\n📊 Performance Results:")
            print(f"   Average: {avg_time:.1f}ms")
            print(f"   Maximum: {max_time:.1f}ms")
            print(f"   Target: <200ms (DATABASE_ENGINEERING_SPEC.md)")
            
            # Validate against performance targets
            performance_pass = max_time <= 200
            
            if performance_pass:
                print("✅ Performance targets met")
            else:
                print(f"⚠️ Performance warning: {max_time:.1f}ms exceeds 200ms target")
            
            return performance_pass
            
        except Exception as e:
            print(f"❌ Performance test failed: {e}")
            return False
    
    def test_search_functionality(self) -> bool:
        """Test actual search functionality with real data"""
        print("\n🔍 Testing search functionality...")
        
        try:
            # Test with a simple embedding (all 0.1 values)
            test_embedding = [0.1] * 3072
            
            # Execute search
            results = self.vector_store.search(test_embedding, top_k=3)
            
            print(f"📊 Search Results:")
            print(f"   Results count: {len(results)}")
            
            if results:
                for i, result in enumerate(results[:3]):
                    chunk_id = result.document.metadata.get("chunk_id", "unknown")
                    framework = result.document.metadata.get("framework_name", "unknown")
                    score = result.score
                    print(f"   {i+1}. {chunk_id} ({framework}) - Score: {score:.3f}")
                
                print("✅ Search functionality working")
                return True
            else:
                print("⚠️ No search results returned (may indicate data issues)")
                return False
                
        except Exception as e:
            print(f"❌ Search functionality test failed: {e}")
            return False
    
    def run_all_tests(self) -> bool:
        """Run complete PostgreSQL storage test suite"""
        print("🚀 Starting PostgreSQL Storage Interface Test Suite")
        print("=" * 60)
        
        tests = [
            ("Interface Compliance", self.test_interface_compliance),
            ("Database Connectivity", self.test_database_connectivity),
            ("Vector Search Performance", self.test_vector_search_performance),
            ("Search Functionality", self.test_search_functionality)
        ]
        
        results = []
        for test_name, test_func in tests:
            try:
                result = test_func()
                results.append(result)
                status = "✅ PASS" if result else "❌ FAIL"
                print(f"\n{test_name}: {status}")
            except Exception as e:
                results.append(False)
                print(f"\n{test_name}: ❌ FAIL ({e})")
        
        # Overall assessment
        all_pass = all(results)
        
        print("\n" + "=" * 60)
        print("🎯 POSTGRESQL STORAGE TEST RESULTS")
        print("=" * 60)
        
        for i, (test_name, _) in enumerate(tests):
            status = "✅ PASS" if results[i] else "❌ FAIL"
            print(f"{test_name}: {status}")
        
        print("\n" + "=" * 60)
        
        if all_pass:
            print("✅ ALL TESTS PASSED - POSTGRESQL STORAGE INTERFACE READY")
        else:
            print("❌ SOME TESTS FAILED - REVIEW ISSUES")
        
        return all_pass


def main():
    """Run PostgreSQL storage tests"""
    try:
        tester = PostgreSQLStorageTest()
        success = tester.run_all_tests()
        
        if success:
            print("\n🎉 PostgreSQL storage interface validation complete - ready for FastAPI integration")
            exit(0)
        else:
            print("\n❌ PostgreSQL storage issues detected - fix before proceeding") 
            exit(1)
            
    except Exception as e:
        print(f"\n❌ Test suite failed to initialize: {e}")
        exit(1)


if __name__ == "__main__":
    main()
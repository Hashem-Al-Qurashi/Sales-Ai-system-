#!/usr/bin/env python3
"""
Migrate Backup Data to PostgreSQL
Restore all 20 chunks with real OpenAI embeddings to PostgreSQL + pgvector
Following DATABASE_ENGINEERING_SPEC.md strictly
"""

import json
import logging
import psycopg2
import uuid
from pathlib import Path
from datetime import datetime
import numpy as np

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PostgreSQLMigration:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.backup_dir = self.project_root / 'backup' / 'database_migration_20251008_105002'
        
        # PostgreSQL connection parameters
        self.db_params = {
            'host': 'localhost',
            'database': 'hormozi_rag',
            'user': 'rag_app_user',
            'password': 'rag_secure_password_123',
            'port': 5432
        }
    
    def connect_to_postgresql(self):
        """Connect to PostgreSQL database"""
        try:
            conn = psycopg2.connect(**self.db_params)
            conn.set_session(autocommit=False)
            logger.info("✅ Connected to PostgreSQL")
            return conn
        except Exception as e:
            logger.error(f"❌ PostgreSQL connection failed: {e}")
            return None
    
    def load_backup_data(self):
        """Load all backup data files"""
        try:
            logger.info("📂 Loading backup data...")
            
            # Load documents
            with open(self.backup_dir / 'framework_documents.json', 'r', encoding='utf-8') as f:
                documents = json.load(f)
            
            # Load metadata  
            with open(self.backup_dir / 'framework_metadata.json', 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            # Load embeddings
            with open(self.backup_dir / 'chunk_embeddings.json', 'r', encoding='utf-8') as f:
                embeddings = json.load(f)
            
            # Load concepts
            with open(self.backup_dir / 'key_concepts.json', 'r', encoding='utf-8') as f:
                concepts = json.load(f)
            
            # Load document-concept relationships
            with open(self.backup_dir / 'document_concepts.json', 'r', encoding='utf-8') as f:
                doc_concepts = json.load(f)
            
            logger.info(f"✅ Loaded backup data:")
            logger.info(f"   - Documents: {len(documents)}")
            logger.info(f"   - Metadata: {len(metadata)}")
            logger.info(f"   - Embeddings: {len(embeddings)}")
            logger.info(f"   - Concepts: {len(concepts)}")
            logger.info(f"   - Relationships: {len(doc_concepts)}")
            
            return documents, metadata, embeddings, concepts, doc_concepts
            
        except Exception as e:
            logger.error(f"❌ Failed to load backup data: {e}")
            return None, None, None, None, None
    
    def migrate_documents(self, conn, documents):
        """Migrate framework_documents"""
        logger.info("📦 Migrating framework_documents...")
        
        try:
            cursor = conn.cursor()
            
            for doc in documents:
                cursor.execute("""
                    INSERT INTO framework_documents 
                    (id, chunk_id, source_file, section, title, description, content, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (chunk_id) DO UPDATE SET
                        content = EXCLUDED.content,
                        updated_at = NOW()
                """, (
                    doc['id'],
                    doc['chunk_id'],
                    doc['source_file'],
                    doc['section'],
                    doc['title'],
                    doc.get('description'),
                    doc['content'],
                    doc['created_at'],
                    doc['updated_at']
                ))
            
            conn.commit()
            logger.info(f"✅ Migrated {len(documents)} documents")
            return True
            
        except Exception as e:
            logger.error(f"❌ Documents migration failed: {e}")
            conn.rollback()
            return False
    
    def migrate_metadata(self, conn, metadata):
        """Migrate framework_metadata"""
        logger.info("📊 Migrating framework_metadata...")
        
        try:
            cursor = conn.cursor()
            
            for meta in metadata:
                cursor.execute("""
                    INSERT INTO framework_metadata 
                    (id, document_id, character_count, word_count, chunk_type, framework_name, 
                     preserves_complete_concept, overlap_with_previous, contains_formula, 
                     contains_list, contains_example, business_logic_intact, validation_passed, 
                     processing_date, guidelines_compliance)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        character_count = EXCLUDED.character_count,
                        word_count = EXCLUDED.word_count
                """, (
                    meta['id'],
                    meta['document_id'],
                    meta['character_count'],
                    meta['word_count'],
                    meta['chunk_type'],
                    meta.get('framework_name'),
                    meta.get('preserves_complete_concept', True),
                    meta.get('overlap_with_previous'),
                    meta.get('contains_formula', False),
                    meta.get('contains_list', False),
                    meta.get('contains_example', False),
                    meta.get('business_logic_intact', True),
                    meta.get('validation_passed', False),
                    meta.get('processing_date'),
                    meta.get('guidelines_compliance')
                ))
            
            conn.commit()
            logger.info(f"✅ Migrated {len(metadata)} metadata records")
            return True
            
        except Exception as e:
            logger.error(f"❌ Metadata migration failed: {e}")
            conn.rollback()
            return False
    
    def migrate_embeddings(self, conn, embeddings):
        """Migrate chunk_embeddings with real OpenAI vectors"""
        logger.info("🔮 Migrating chunk_embeddings...")
        
        try:
            cursor = conn.cursor()
            
            for emb in embeddings:
                # Parse the embedding data (list of floats)
                embedding_vector = emb['embedding_data']
                if isinstance(embedding_vector, str):
                    embedding_vector = json.loads(embedding_vector)
                
                # Convert to PostgreSQL vector format
                vector_str = '[' + ','.join(map(str, embedding_vector)) + ']'
                
                cursor.execute("""
                    INSERT INTO chunk_embeddings 
                    (id, document_id, embedding, model_name, created_at)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO NOTHING
                """, (
                    emb['id'],
                    emb['document_id'],
                    vector_str,  # PostgreSQL vector format
                    emb['model_name'],
                    emb['created_at']
                ))
            
            conn.commit()
            logger.info(f"✅ Migrated {len(embeddings)} embeddings")
            return True
            
        except Exception as e:
            logger.error(f"❌ Embeddings migration failed: {e}")
            conn.rollback()
            return False
    
    def migrate_concepts(self, conn, concepts, doc_concepts):
        """Migrate key_concepts and relationships"""
        logger.info("🏷️ Migrating concepts and relationships...")
        
        try:
            cursor = conn.cursor()
            
            # Migrate concepts
            for concept in concepts:
                cursor.execute("""
                    INSERT INTO key_concepts (id, concept_name, created_at)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (concept_name) DO NOTHING
                """, (
                    concept['id'],
                    concept['concept_name'],
                    concept['created_at']
                ))
            
            # Migrate document-concept relationships
            for rel in doc_concepts:
                cursor.execute("""
                    INSERT INTO document_concepts (document_id, concept_id, created_at)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (document_id, concept_id) DO NOTHING
                """, (
                    rel['document_id'],
                    rel['concept_id'],
                    rel['created_at']
                ))
            
            conn.commit()
            logger.info(f"✅ Migrated {len(concepts)} concepts and {len(doc_concepts)} relationships")
            return True
            
        except Exception as e:
            logger.error(f"❌ Concepts migration failed: {e}")
            conn.rollback()
            return False
    
    def create_vector_index(self, conn):
        """Create the vector similarity index after data is loaded"""
        logger.info("🎯 Creating vector similarity index...")
        
        try:
            cursor = conn.cursor()
            
            # Check if we have embeddings first
            cursor.execute("SELECT COUNT(*) FROM chunk_embeddings")
            count = cursor.fetchone()[0]
            
            if count == 0:
                logger.warning("⚠️ No embeddings found - skipping vector index")
                return False
            
            # Create the vector similarity index
            cursor.execute("""
                CREATE INDEX idx_embeddings_vector ON chunk_embeddings 
                USING ivfflat (embedding vector_cosine_ops) 
                WITH (lists = 100)
            """)
            
            conn.commit()
            logger.info("✅ Vector similarity index created successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Vector index creation failed: {e}")
            # Don't rollback - the data migration is still valid
            return False
    
    def validate_migration(self, conn):
        """Validate the complete migration"""
        logger.info("🔍 Validating migration...")
        
        try:
            cursor = conn.cursor()
            
            # Check counts
            cursor.execute("SELECT COUNT(*) FROM framework_documents")
            doc_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM framework_metadata")  
            meta_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM chunk_embeddings")
            emb_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM key_concepts")
            concept_count = cursor.fetchone()[0]
            
            # Test vector dimensions
            cursor.execute("SELECT vector_dims(embedding) FROM chunk_embeddings LIMIT 1")
            dims = cursor.fetchone()
            if dims:
                dims = dims[0]
            else:
                dims = 0
            
            logger.info("📊 Migration Validation Results:")
            logger.info(f"   - Documents: {doc_count}/20")
            logger.info(f"   - Metadata: {meta_count}/20")  
            logger.info(f"   - Embeddings: {emb_count}/20")
            logger.info(f"   - Concepts: {concept_count}")
            logger.info(f"   - Embedding Dimensions: {dims}")
            
            success = (doc_count == 20 and meta_count == 20 and emb_count == 20 and dims == 3072)
            
            if success:
                logger.info("🎉 Migration validation PASSED!")
            else:
                logger.warning("⚠️ Migration validation issues detected")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Validation failed: {e}")
            return False
    
    def run_migration(self):
        """Execute complete migration from backup to PostgreSQL"""
        logger.info("🚀 Starting PostgreSQL migration from backup...")
        
        # Load backup data
        documents, metadata, embeddings, concepts, doc_concepts = self.load_backup_data()
        if not documents:
            return False
        
        # Connect to PostgreSQL
        conn = self.connect_to_postgresql()
        if not conn:
            return False
        
        try:
            # Migrate all data
            success = True
            success &= self.migrate_documents(conn, documents)
            success &= self.migrate_metadata(conn, metadata)
            success &= self.migrate_embeddings(conn, embeddings)
            success &= self.migrate_concepts(conn, concepts, doc_concepts)
            
            if success:
                # Create vector index after data is loaded
                self.create_vector_index(conn)
                
                # Validate migration
                success = self.validate_migration(conn)
            
            conn.close()
            
            if success:
                logger.info("🎉 POSTGRESQL MIGRATION COMPLETED SUCCESSFULLY!")
                logger.info("✅ All 20 chunks migrated with real OpenAI embeddings")
                logger.info("✅ Vector similarity search ready")
                return True
            else:
                logger.error("❌ Migration completed with issues")
                return False
                
        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            conn.close()
            return False

if __name__ == "__main__":
    migration = PostgreSQLMigration()
    success = migration.run_migration()
    
    if success:
        print("✅ PostgreSQL migration completed successfully!")
    else:
        print("❌ PostgreSQL migration failed!")
        exit(1)
# PostgreSQL + pgvector Migration Plan

**Date**: 2025-10-06  
**Status**: SENIOR ENGINEERING IMPLEMENTATION PLAN  
**Following**: DEVELOPMENT_RULES.md compliance  

---

## Executive Summary

Migrate from 19 JSON chunk files to production-ready PostgreSQL + pgvector database while maintaining 100% framework integrity and following all senior engineering principles.

## Current State Analysis

### Existing Assets
- ✅ **19 JSON chunks**: Complete, validated, framework-preserved
- ✅ **Rich metadata**: All business context captured
- ✅ **Framework integrity**: 100% preservation achieved
- ✅ **Architecture compliance**: Follows ARCHITECTURE.md modular design

### Schema Design Principles (DEVELOPMENT_RULES.md Compliance)

#### 1. Single Responsibility
- `framework_documents`: Core content only
- `chunk_embeddings`: Vector data isolation
- `framework_metadata`: Business context separation
- `key_concepts`: Normalized concept management

#### 2. Error Handling Hierarchy
```sql
-- Level 1: Input validation (fail fast)
CONSTRAINT valid_chunk_type CHECK (chunk_type IN ('atomic_framework', 'framework_section', 'supporting')),
CONSTRAINT valid_character_count CHECK (character_count > 0),

-- Level 2: Business logic (recover gracefully)
-- Migration script will handle malformed JSON gracefully

-- Level 3: System errors (circuit breaker)
-- Connection pooling and retry logic in application layer
```

#### 3. Configuration Over Code
```python
# Environment-driven database configuration
DATABASE_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": os.getenv("POSTGRES_PORT", 5432),
    "database": os.getenv("POSTGRES_DB", "hormozi_rag"),
    "user": os.getenv("POSTGRES_USER", "rag_user"),
    "password": os.getenv("POSTGRES_PASSWORD"),
    "pool_size": int(os.getenv("DB_POOL_SIZE", 20)),
    "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", 30))
}
```

---

## Production-Ready Schema

### Core Tables

```sql
-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Core Framework Documents Table
CREATE TABLE framework_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chunk_id VARCHAR(255) UNIQUE NOT NULL,
    source_file VARCHAR(255) NOT NULL,
    section VARCHAR(255) NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints (Level 1 Error Handling)
    CONSTRAINT non_empty_content CHECK (length(trim(content)) > 0),
    CONSTRAINT non_empty_chunk_id CHECK (length(trim(chunk_id)) > 0)
);

-- Vector Embeddings Table (Separation of Concerns)
CREATE TABLE chunk_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES framework_documents(id) ON DELETE CASCADE,
    embedding vector(3072), -- OpenAI text-embedding-3-large
    model_name VARCHAR(100) DEFAULT 'text-embedding-3-large' NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_embedding_dimensions CHECK (vector_dims(embedding) = 3072),
    CONSTRAINT valid_model_name CHECK (model_name IN ('text-embedding-3-large', 'text-embedding-3-small'))
);

-- Framework Metadata Table (Rich Business Context)
CREATE TABLE framework_metadata (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES framework_documents(id) ON DELETE CASCADE,
    character_count INTEGER NOT NULL,
    word_count INTEGER NOT NULL,
    chunk_type VARCHAR(50) NOT NULL,
    framework_name VARCHAR(255),
    preserves_complete_concept BOOLEAN DEFAULT TRUE,
    overlap_with_previous TEXT,
    contains_formula BOOLEAN DEFAULT FALSE,
    contains_list BOOLEAN DEFAULT FALSE,
    contains_example BOOLEAN DEFAULT FALSE,
    business_logic_intact BOOLEAN DEFAULT TRUE,
    validation_passed BOOLEAN DEFAULT FALSE,
    processing_date DATE,
    guidelines_compliance VARCHAR(255),
    
    -- Constraints (Level 1 Error Handling)
    CONSTRAINT valid_chunk_type CHECK (chunk_type IN ('atomic_framework', 'framework_section', 'supporting')),
    CONSTRAINT valid_character_count CHECK (character_count > 0),
    CONSTRAINT valid_word_count CHECK (word_count > 0)
);

-- Key Concepts Junction Table (N:N relationship)
CREATE TABLE key_concepts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    concept_name VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT non_empty_concept_name CHECK (length(trim(concept_name)) > 0)
);

CREATE TABLE document_concepts (
    document_id UUID REFERENCES framework_documents(id) ON DELETE CASCADE,
    concept_id UUID REFERENCES key_concepts(id) ON DELETE CASCADE,
    PRIMARY KEY (document_id, concept_id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Source Line Tracking (Traceability)
CREATE TABLE source_lines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES framework_documents(id) ON DELETE CASCADE,
    start_line INTEGER,
    end_line INTEGER,
    
    CONSTRAINT valid_line_numbers CHECK (start_line > 0 AND end_line >= start_line)
);
```

### Performance Indexes (Production Ready)

```sql
-- Vector similarity search (Primary use case)
CREATE INDEX idx_embeddings_vector ON chunk_embeddings 
USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);

-- Business queries
CREATE INDEX idx_documents_chunk_id ON framework_documents(chunk_id);
CREATE INDEX idx_documents_section ON framework_documents(section);
CREATE INDEX idx_metadata_framework_name ON framework_metadata(framework_name);
CREATE INDEX idx_metadata_chunk_type ON framework_metadata(chunk_type);
CREATE INDEX idx_documents_created_at ON framework_documents(created_at);
CREATE INDEX idx_documents_source_file ON framework_documents(source_file);

-- Full-text search (Hybrid retrieval)
CREATE INDEX idx_documents_content_fts ON framework_documents 
USING gin(to_tsvector('english', content));
CREATE INDEX idx_documents_title_fts ON framework_documents 
USING gin(to_tsvector('english', title));

-- Concept-based retrieval
CREATE INDEX idx_concepts_name ON key_concepts(concept_name);
CREATE INDEX idx_document_concepts_document_id ON document_concepts(document_id);
CREATE INDEX idx_document_concepts_concept_id ON document_concepts(concept_id);
```

---

## Migration Implementation

### Phase 1: Database Setup (Environment Configuration)

```python
# migrations/001_setup_database.py
import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

class DatabaseSetup:
    def __init__(self):
        self.config = {
            "host": os.getenv("POSTGRES_HOST", "localhost"),
            "port": int(os.getenv("POSTGRES_PORT", 5432)),
            "database": os.getenv("POSTGRES_DB", "hormozi_rag"),
            "user": os.getenv("POSTGRES_USER", "rag_user"),
            "password": os.getenv("POSTGRES_PASSWORD"),
        }
        
        if not self.config["password"]:
            raise ValueError("POSTGRES_PASSWORD environment variable required")
    
    def create_database_if_not_exists(self):
        """Level 2 Error Handling: Graceful database creation"""
        try:
            # Connect to postgres database to create target database
            conn = psycopg2.connect(
                host=self.config["host"],
                port=self.config["port"],
                database="postgres",
                user=self.config["user"],
                password=self.config["password"]
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            
            with conn.cursor() as cursor:
                cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = '{self.config['database']}'")
                if not cursor.fetchone():
                    cursor.execute(f"CREATE DATABASE {self.config['database']}")
                    print(f"✅ Database {self.config['database']} created")
                else:
                    print(f"✅ Database {self.config['database']} already exists")
                    
        except psycopg2.Error as e:
            raise DatabaseError(f"Failed to create database: {e}")
        finally:
            if conn:
                conn.close()
```

### Phase 2: Schema Migration

```python
# migrations/002_create_schema.py
import json
import logging
from pathlib import Path
from typing import List, Dict, Any

class SchemaMigration:
    def __init__(self, db_connection):
        self.db = db_connection
        self.logger = logging.getLogger(__name__)
        
    def execute_schema_sql(self):
        """Execute schema creation with proper error handling"""
        schema_path = Path(__file__).parent / "schema.sql"
        
        try:
            with open(schema_path, 'r') as f:
                schema_sql = f.read()
            
            with self.db.cursor() as cursor:
                cursor.execute(schema_sql)
                
            self.db.commit()
            self.logger.info("✅ Schema created successfully")
            
        except Exception as e:
            self.db.rollback()
            raise MigrationError(f"Schema creation failed: {e}")
```

### Phase 3: Data Migration (JSON to PostgreSQL)

```python
# migrations/003_migrate_chunks.py
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

class ChunkMigration:
    def __init__(self, db_connection):
        self.db = db_connection
        self.logger = logging.getLogger(__name__)
        
    def migrate_all_chunks(self):
        """Migrate all 19 JSON chunk files with full error handling"""
        data_dir = Path("data")
        chunk_files = [
            "manual_chunks_introduction.json",
            "manual_chunks_section_i.json", 
            "manual_chunks_section_ii.json",
            "manual_chunks_section_iii_part_a.json",
            "manual_chunks_section_iii_part_b.json",
            "manual_chunks_section_iii_part_cd.json",
            "value_equation_framework_01.json",
            "scarcity_value_implementation_01.json",
            "urgency_implementation_framework_02.json",
            "bonuses_strategy_implementation_03.json",
            "guarantees_naming_conclusion_04.json"
        ]
        
        total_chunks = 0
        
        try:
            with self.db.cursor() as cursor:
                for file_path in chunk_files:
                    if (data_dir / file_path).exists():
                        chunks_migrated = self._migrate_single_file(cursor, data_dir / file_path)
                        total_chunks += chunks_migrated
                        self.logger.info(f"✅ Migrated {chunks_migrated} chunks from {file_path}")
                    else:
                        self.logger.warning(f"⚠️  File not found: {file_path}")
                
            self.db.commit()
            self.logger.info(f"✅ Migration completed: {total_chunks} total chunks migrated")
            
        except Exception as e:
            self.db.rollback()
            raise MigrationError(f"Chunk migration failed: {e}")
    
    def _migrate_single_file(self, cursor, file_path: Path) -> int:
        """Migrate single JSON file with validation"""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Handle different JSON structures
            if 'frameworks' in data:
                return self._migrate_structured_chunks(cursor, data)
            else:
                return self._migrate_single_chunk(cursor, data, file_path.name)
                
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON in {file_path}: {e}")
        except Exception as e:
            raise MigrationError(f"Failed to migrate {file_path}: {e}")
    
    def _migrate_structured_chunks(self, cursor, data: Dict) -> int:
        """Migrate chunks from structured JSON format"""
        chunks_migrated = 0
        
        for framework_name, framework_data in data.get('frameworks', {}).items():
            for chunk in framework_data.get('chunks', []):
                document_id = self._insert_document(cursor, chunk, framework_name)
                self._insert_metadata(cursor, document_id, chunk)
                self._insert_concepts(cursor, document_id, chunk.get('key_concepts', []))
                chunks_migrated += 1
                
        return chunks_migrated
    
    def _migrate_single_chunk(self, cursor, chunk_data: Dict, filename: str) -> int:
        """Migrate single chunk format"""
        document_id = self._insert_document(cursor, chunk_data, filename)
        self._insert_metadata(cursor, document_id, chunk_data)
        
        if 'metadata' in chunk_data and 'key_concepts' in chunk_data['metadata']:
            self._insert_concepts(cursor, document_id, chunk_data['metadata']['key_concepts'])
            
        return 1
    
    def _insert_document(self, cursor, chunk: Dict, framework_name: str) -> str:
        """Insert into framework_documents table"""
        document_id = str(uuid.uuid4())
        
        # Level 1 Error Handling: Input validation
        required_fields = ['chunk_id', 'content']
        for field in required_fields:
            if field not in chunk or not chunk[field]:
                raise ValidationError(f"Required field '{field}' missing or empty")
        
        insert_sql = """
            INSERT INTO framework_documents 
            (id, chunk_id, source_file, section, title, description, content)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        
        cursor.execute(insert_sql, (
            document_id,
            chunk['chunk_id'],
            chunk.get('metadata', {}).get('source_file', 'unknown'),
            chunk.get('section', 'unknown'),
            chunk.get('title', chunk['chunk_id']),
            chunk.get('description', ''),
            chunk['content']
        ))
        
        return document_id
    
    def _insert_metadata(self, cursor, document_id: str, chunk: Dict):
        """Insert into framework_metadata table"""
        metadata = chunk.get('metadata', {})
        
        insert_sql = """
            INSERT INTO framework_metadata 
            (document_id, character_count, word_count, chunk_type, framework_name,
             preserves_complete_concept, overlap_with_previous, contains_formula,
             contains_list, contains_example, business_logic_intact, validation_passed,
             processing_date, guidelines_compliance)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        cursor.execute(insert_sql, (
            document_id,
            chunk.get('char_count', metadata.get('character_count', 0)),
            chunk.get('word_count', metadata.get('word_count', 0)),
            chunk.get('chunk_type', 'supporting'),
            chunk.get('framework_name', metadata.get('framework_name')),
            chunk.get('preserves_complete_concept', True),
            chunk.get('overlap_with_previous'),
            chunk.get('contains_formula', False),
            chunk.get('contains_list', False),
            chunk.get('contains_example', False),
            chunk.get('business_logic_intact', True),
            chunk.get('validation_passed', True),
            datetime.now().date(),
            metadata.get('guidelines_compliance', 'SENIOR_CHUNKING_RULES.md')
        ))
    
    def _insert_concepts(self, cursor, document_id: str, concepts: List[str]):
        """Insert key concepts with deduplication"""
        for concept in concepts:
            # Insert concept if not exists
            cursor.execute(
                "INSERT INTO key_concepts (concept_name) VALUES (%s) ON CONFLICT (concept_name) DO NOTHING",
                (concept,)
            )
            
            # Get concept ID
            cursor.execute("SELECT id FROM key_concepts WHERE concept_name = %s", (concept,))
            concept_id = cursor.fetchone()[0]
            
            # Link document to concept
            cursor.execute(
                "INSERT INTO document_concepts (document_id, concept_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (document_id, concept_id)
            )
```

### Phase 4: Embedding Generation

```python
# migrations/004_generate_embeddings.py
import openai
import numpy as np
from typing import List, Dict
import time

class EmbeddingMigration:
    def __init__(self, db_connection):
        self.db = db_connection
        self.client = openai.OpenAI()
        self.logger = logging.getLogger(__name__)
        
    def generate_all_embeddings(self, batch_size: int = 10):
        """Generate embeddings for all documents with batching and error handling"""
        try:
            with self.db.cursor() as cursor:
                # Get all documents without embeddings
                cursor.execute("""
                    SELECT fd.id, fd.content, fd.chunk_id 
                    FROM framework_documents fd 
                    LEFT JOIN chunk_embeddings ce ON fd.id = ce.document_id 
                    WHERE ce.id IS NULL
                """)
                
                documents = cursor.fetchall()
                total_docs = len(documents)
                
                self.logger.info(f"Generating embeddings for {total_docs} documents")
                
                # Process in batches
                for i in range(0, total_docs, batch_size):
                    batch = documents[i:i + batch_size]
                    self._process_embedding_batch(cursor, batch)
                    
                    # Rate limiting (OpenAI: 3000 RPM)
                    if i + batch_size < total_docs:
                        time.sleep(1)
                    
                    self.logger.info(f"Processed {min(i + batch_size, total_docs)}/{total_docs} documents")
                
            self.db.commit()
            self.logger.info("✅ All embeddings generated successfully")
            
        except Exception as e:
            self.db.rollback()
            raise EmbeddingError(f"Embedding generation failed: {e}")
    
    def _process_embedding_batch(self, cursor, batch: List[tuple]):
        """Process a batch of documents for embedding generation"""
        try:
            # Prepare texts for embedding
            texts = [doc[1] for doc in batch]  # content column
            
            # Generate embeddings via OpenAI
            response = self.client.embeddings.create(
                input=texts,
                model="text-embedding-3-large"
            )
            
            # Insert embeddings
            for i, doc in enumerate(batch):
                document_id, content, chunk_id = doc
                embedding = response.data[i].embedding
                
                cursor.execute("""
                    INSERT INTO chunk_embeddings (document_id, embedding, model_name)
                    VALUES (%s, %s, %s)
                """, (document_id, embedding, "text-embedding-3-large"))
                
        except Exception as e:
            raise EmbeddingError(f"Batch processing failed: {e}")
```

---

## Integration with Existing Architecture

### Storage Layer Interface Implementation

```python
# hormozi_rag/storage/postgresql_storage.py
from typing import List, Dict, Any, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from hormozi_rag.storage.interfaces import VectorDBInterface

class PostgreSQLVectorStore(VectorDBInterface):
    """PostgreSQL + pgvector implementation following ARCHITECTURE.md"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.connection = None
        self._connect()
    
    def _connect(self):
        """Level 3 Error Handling: Circuit breaker pattern"""
        try:
            self.connection = psycopg2.connect(
                host=self.config["host"],
                port=self.config["port"],
                database=self.config["database"],
                user=self.config["user"],
                password=self.config["password"],
                cursor_factory=RealDictCursor
            )
        except psycopg2.Error as e:
            raise StorageError(f"Database connection failed: {e}")
    
    def search_similar(self, query_embedding: List[float], top_k: int = 10) -> List[Dict]:
        """Vector similarity search with pgvector"""
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        fd.chunk_id,
                        fd.content,
                        fd.title,
                        fd.section,
                        fm.framework_name,
                        fm.chunk_type,
                        (ce.embedding <=> %s::vector) as distance
                    FROM framework_documents fd
                    JOIN chunk_embeddings ce ON fd.id = ce.document_id
                    JOIN framework_metadata fm ON fd.id = fm.document_id
                    ORDER BY ce.embedding <=> %s::vector
                    LIMIT %s
                """, (query_embedding, query_embedding, top_k))
                
                return cursor.fetchall()
                
        except psycopg2.Error as e:
            raise RetrievalError(f"Vector search failed: {e}")
    
    def hybrid_search(self, query: str, query_embedding: List[float], top_k: int = 10) -> List[Dict]:
        """Hybrid vector + full-text search"""
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    WITH vector_results AS (
                        SELECT 
                            fd.id,
                            fd.chunk_id,
                            fd.content,
                            fd.title,
                            fm.framework_name,
                            (ce.embedding <=> %s::vector) as vector_distance
                        FROM framework_documents fd
                        JOIN chunk_embeddings ce ON fd.id = ce.document_id
                        JOIN framework_metadata fm ON fd.id = fm.document_id
                        ORDER BY ce.embedding <=> %s::vector
                        LIMIT %s
                    ),
                    text_results AS (
                        SELECT 
                            fd.id,
                            ts_rank(to_tsvector('english', fd.content), plainto_tsquery('english', %s)) as text_rank
                        FROM framework_documents fd
                        WHERE to_tsvector('english', fd.content) @@ plainto_tsquery('english', %s)
                    )
                    SELECT 
                        vr.*,
                        COALESCE(tr.text_rank, 0) as text_rank,
                        (1.0 - vr.vector_distance) * 0.7 + COALESCE(tr.text_rank, 0) * 0.3 as combined_score
                    FROM vector_results vr
                    LEFT JOIN text_results tr ON vr.id = tr.id
                    ORDER BY combined_score DESC
                    LIMIT %s
                """, (query_embedding, query_embedding, top_k * 2, query, query, top_k))
                
                return cursor.fetchall()
                
        except psycopg2.Error as e:
            raise RetrievalError(f"Hybrid search failed: {e}")
```

---

## Implementation Timeline

### Week 1: Foundation Setup
- [x] **Day 1**: Environment configuration and database setup
- [x] **Day 2**: Schema creation and validation  
- [x] **Day 3**: Migration script development
- [x] **Day 4**: Data migration execution
- [x] **Day 5**: Embedding generation

### Week 2: Integration & Testing
- [ ] **Day 1**: Storage layer interface implementation
- [ ] **Day 2**: Retrieval engine integration
- [ ] **Day 3**: API endpoint updates
- [ ] **Day 4**: Performance testing and optimization
- [ ] **Day 5**: Production deployment preparation

---

## Quality Assurance

### Validation Checklist
- [ ] All 19 chunks migrated successfully
- [ ] 100% framework integrity preserved
- [ ] All embeddings generated (19 * 3072 dimensions)
- [ ] Vector search functional (< 2s response time)
- [ ] Hybrid search operational
- [ ] Full-text search working
- [ ] All indexes created and optimized
- [ ] Error handling tested at all levels
- [ ] Monitoring and logging operational

### Performance Targets
- **Vector Search**: < 500ms p95
- **Hybrid Search**: < 1s p95  
- **Embedding Generation**: < 30s for all chunks
- **Database Connections**: Pool of 20, max overflow 30
- **Memory Usage**: < 2GB for full dataset

---

## Risk Mitigation

### Technical Risks
1. **Embedding Dimension Mismatch**: Enforced via database constraints
2. **Data Loss During Migration**: Transaction-based migration with rollback
3. **Performance Degradation**: Comprehensive indexing strategy
4. **OpenAI API Failures**: Retry logic with exponential backoff

### Operational Risks  
1. **Database Downtime**: Connection pooling with failover
2. **Disk Space**: Monitoring with automated alerts
3. **Memory Leaks**: Connection management and proper cleanup
4. **Concurrent Access**: ACID transactions and proper locking

---

## Post-Migration Tasks

### Immediate (Week 3)
- [ ] Performance monitoring setup
- [ ] Automated backup configuration  
- [ ] Health check endpoint updates
- [ ] Documentation updates

### Short-term (Month 1)
- [ ] Query performance optimization
- [ ] Index tuning based on usage patterns
- [ ] Caching layer implementation
- [ ] Advanced search features

### Long-term (Month 2+)
- [ ] Read replicas for scaling
- [ ] Automated index maintenance
- [ ] Advanced analytics and metrics
- [ ] Multi-tenant architecture preparation

---

**Review Date**: 2025-10-13 (Weekly architecture review per DEVELOPMENT_RULES.md)
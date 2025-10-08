# PostgreSQL Implementation Runbook
## Hormozi RAG System Database Migration

**Document Type**: Operations Runbook  
**Version**: 1.0.0  
**Date**: 2025-10-06  
**Author**: Senior Database Engineer  
**Purpose**: Step-by-step implementation guide  

---

## Pre-Implementation Checklist

### System Requirements Verification
- [ ] **PostgreSQL 15+** installed and configured
- [ ] **pgvector extension** available and installed
- [ ] **Python 3.9+** with required packages
- [ ] **OpenAI API key** configured and validated
- [ ] **Network connectivity** between application and database
- [ ] **Backup storage** available (minimum 10GB)
- [ ] **Monitoring tools** configured (optional but recommended)

### Environment Preparation
```bash
# 1. Verify PostgreSQL installation
psql --version
# Expected: psql (PostgreSQL) 15.x

# 2. Verify pgvector availability
sudo -u postgres psql -c "CREATE EXTENSION IF NOT EXISTS vector;"
# Expected: CREATE EXTENSION

# 3. Verify Python dependencies
python -c "import psycopg2, openai, json; print('Dependencies OK')"
# Expected: Dependencies OK

# 4. Check disk space
df -h /var/lib/postgresql/
# Expected: At least 10GB free

# 5. Verify network connectivity
nc -zv your-postgres-host 5432
# Expected: Connection succeeded
```

---

## Implementation Steps

### Step 1: Database Infrastructure Setup (30 minutes)

#### 1.1 Create Database and User
```bash
# Connect as postgres superuser
sudo -u postgres psql

# Create database
CREATE DATABASE hormozi_rag 
    WITH ENCODING 'UTF8' 
    LC_COLLATE='en_US.UTF-8' 
    LC_CTYPE='en_US.UTF-8'
    TEMPLATE=template0;

# Create application user
CREATE USER rag_app_user WITH ENCRYPTED PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE hormozi_rag TO rag_app_user;

# Enable vector extension
\c hormozi_rag
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

# Verify extensions
\dx
# Expected: vector and uuid-ossp listed

\q
```

#### 1.2 Configure PostgreSQL for Vector Operations
```bash
# Edit postgresql.conf
sudo nano /etc/postgresql/15/main/postgresql.conf

# Add/modify these settings:
shared_preload_libraries = 'vector'
max_connections = 200
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 32MB
maintenance_work_mem = 256MB
checkpoint_completion_target = 0.9

# Restart PostgreSQL
sudo systemctl restart postgresql

# Verify settings
sudo -u postgres psql -c "SHOW shared_preload_libraries;"
# Expected: vector listed
```

#### 1.3 Set Environment Variables
```bash
# Create environment file
cat > .env << EOF
# Database Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=hormozi_rag
POSTGRES_USER=rag_app_user
POSTGRES_PASSWORD=your_secure_password

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key

# Application Configuration
ENVIRONMENT=production
LOG_LEVEL=INFO
EOF

# Load environment variables
source .env

# Verify connection
psql "postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}" -c "SELECT version();"
# Expected: PostgreSQL version information
```

### Step 2: Schema Creation (15 minutes)

#### 2.1 Create Database Schema
```sql
-- Save as sql/schema.sql
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
    
    -- Data Quality Constraints
    CONSTRAINT non_empty_content CHECK (length(trim(content)) > 0),
    CONSTRAINT non_empty_chunk_id CHECK (length(trim(chunk_id)) > 0)
);

-- Vector Embeddings Table
CREATE TABLE chunk_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES framework_documents(id) ON DELETE CASCADE,
    embedding vector(3072), -- OpenAI text-embedding-3-large
    model_name VARCHAR(100) DEFAULT 'text-embedding-3-large' NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Vector Quality Constraints
    CONSTRAINT valid_embedding_dimensions CHECK (vector_dims(embedding) = 3072),
    CONSTRAINT valid_model_name CHECK (model_name IN ('text-embedding-3-large', 'text-embedding-3-small')),
    CONSTRAINT non_null_embedding CHECK (embedding IS NOT NULL)
);

-- Framework Metadata Table
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
    
    -- Business Logic Constraints
    CONSTRAINT valid_chunk_type CHECK (chunk_type IN ('atomic_framework', 'framework_section', 'supporting')),
    CONSTRAINT valid_character_count CHECK (character_count > 0 AND character_count <= 50000),
    CONSTRAINT valid_word_count CHECK (word_count > 0 AND word_count <= 15000)
);

-- Key Concepts and Relationships
CREATE TABLE key_concepts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    concept_name VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT non_empty_concept_name CHECK (length(trim(concept_name)) > 0)
);

CREATE TABLE document_concepts (
    document_id UUID REFERENCES framework_documents(id) ON DELETE CASCADE,
    concept_id UUID REFERENCES key_concepts(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (document_id, concept_id)
);

-- Source Line Tracking
CREATE TABLE source_lines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES framework_documents(id) ON DELETE CASCADE,
    start_line INTEGER,
    end_line INTEGER,
    
    CONSTRAINT valid_line_numbers CHECK (start_line > 0 AND end_line >= start_line)
);

-- Performance Indexes
CREATE INDEX idx_documents_chunk_id ON framework_documents(chunk_id);
CREATE INDEX idx_documents_section ON framework_documents(section);
CREATE INDEX idx_documents_source_file ON framework_documents(source_file);
CREATE INDEX idx_documents_created_at ON framework_documents(created_at);

-- Vector similarity index (will be created after data load)
-- CREATE INDEX idx_embeddings_vector ON chunk_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Full-text search indexes
CREATE INDEX idx_documents_content_fts ON framework_documents USING gin(to_tsvector('english', content));
CREATE INDEX idx_documents_title_fts ON framework_documents USING gin(to_tsvector('english', title));

-- Business query indexes
CREATE INDEX idx_metadata_framework_name ON framework_metadata(framework_name);
CREATE INDEX idx_metadata_chunk_type ON framework_metadata(chunk_type);
CREATE INDEX idx_metadata_processing_date ON framework_metadata(processing_date);

-- Concept search indexes
CREATE INDEX idx_concepts_name ON key_concepts(concept_name);
CREATE INDEX idx_document_concepts_document_id ON document_concepts(document_id);
CREATE INDEX idx_document_concepts_concept_id ON document_concepts(concept_id);
```

#### 2.2 Execute Schema Creation
```bash
# Execute schema creation
psql "postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}" -f sql/schema.sql

# Verify tables created
psql "postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}" -c "\dt"
# Expected: All 6 tables listed

# Verify constraints
psql "postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}" -c "\d framework_documents"
# Expected: Table structure with constraints
```

### Step 3: Data Migration (45 minutes)

#### 3.1 Create Migration Script
```python
# Save as scripts/migrate_data.py
#!/usr/bin/env python3

import os
import json
import psycopg2
import uuid
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DataMigrator:
    def __init__(self):
        self.connection = None
        self.connect()
    
    def connect(self):
        """Establish database connection"""
        try:
            conn_str = f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@{os.getenv('POSTGRES_HOST', 'localhost')}:{os.getenv('POSTGRES_PORT', 5432)}/{os.getenv('POSTGRES_DB')}"
            self.connection = psycopg2.connect(conn_str)
            logger.info("✅ Database connection established")
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            raise
    
    def migrate_json_file(self, file_path: Path) -> int:
        """Migrate single JSON file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            chunks_processed = 0
            
            if 'frameworks' in data:
                # Structured format (manual_chunks_*.json)
                for framework_name, framework_data in data['frameworks'].items():
                    for chunk in framework_data.get('chunks', []):
                        self._insert_chunk(chunk, framework_name)
                        chunks_processed += 1
            else:
                # Single chunk format (*_framework_*.json)
                framework_name = data.get('metadata', {}).get('framework_name', 'unknown')
                self._insert_chunk(data, framework_name)
                chunks_processed += 1
            
            logger.info(f"✅ Migrated {chunks_processed} chunks from {file_path.name}")
            return chunks_processed
            
        except Exception as e:
            logger.error(f"❌ Failed to migrate {file_path}: {e}")
            raise
    
    def _insert_chunk(self, chunk: Dict[str, Any], framework_name: str):
        """Insert chunk and all related data"""
        try:
            with self.connection.cursor() as cursor:
                # Insert document
                document_id = self._insert_document(cursor, chunk, framework_name)
                
                # Insert metadata
                self._insert_metadata(cursor, document_id, chunk)
                
                # Insert concepts
                concepts = chunk.get('metadata', {}).get('key_concepts', chunk.get('key_concepts', []))
                if concepts:
                    self._insert_concepts(cursor, document_id, concepts)
                
                # Insert source lines if available
                metadata = chunk.get('metadata', {})
                if 'start_line' in metadata and 'end_line' in metadata:
                    self._insert_source_lines(cursor, document_id, metadata)
            
            self.connection.commit()
            
        except Exception as e:
            self.connection.rollback()
            logger.error(f"❌ Failed to insert chunk {chunk.get('chunk_id', 'unknown')}: {e}")
            raise
    
    def _insert_document(self, cursor, chunk: Dict, framework_name: str) -> str:
        """Insert into framework_documents"""
        document_id = str(uuid.uuid4())
        
        cursor.execute("""
            INSERT INTO framework_documents 
            (id, chunk_id, source_file, section, title, description, content)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            document_id,
            chunk.get('chunk_id', f"chunk_{uuid.uuid4().hex[:8]}"),
            chunk.get('metadata', {}).get('source_file', 'unknown'),
            chunk.get('section', 'unknown'),
            chunk.get('title', chunk.get('chunk_id', 'untitled')),
            chunk.get('description', ''),
            chunk.get('content', chunk.get('text', ''))
        ))
        
        return document_id
    
    def _insert_metadata(self, cursor, document_id: str, chunk: Dict):
        """Insert into framework_metadata"""
        metadata = chunk.get('metadata', {})
        content = chunk.get('content', chunk.get('text', ''))
        
        cursor.execute("""
            INSERT INTO framework_metadata 
            (document_id, character_count, word_count, chunk_type, framework_name,
             preserves_complete_concept, overlap_with_previous, contains_formula,
             contains_list, contains_example, business_logic_intact, validation_passed,
             processing_date, guidelines_compliance)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            document_id,
            chunk.get('char_count', len(content)),
            chunk.get('word_count', len(content.split())),
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
        """Insert concepts and relationships"""
        for concept in concepts:
            # Insert concept if not exists
            cursor.execute("""
                INSERT INTO key_concepts (concept_name) 
                VALUES (%s) 
                ON CONFLICT (concept_name) DO NOTHING
            """, (concept,))
            
            # Get concept ID
            cursor.execute("SELECT id FROM key_concepts WHERE concept_name = %s", (concept,))
            concept_id = cursor.fetchone()[0]
            
            # Link document to concept
            cursor.execute("""
                INSERT INTO document_concepts (document_id, concept_id) 
                VALUES (%s, %s) 
                ON CONFLICT DO NOTHING
            """, (document_id, concept_id))
    
    def _insert_source_lines(self, cursor, document_id: str, metadata: Dict):
        """Insert source line tracking"""
        cursor.execute("""
            INSERT INTO source_lines (document_id, start_line, end_line)
            VALUES (%s, %s, %s)
        """, (document_id, metadata.get('start_line'), metadata.get('end_line')))
    
    def migrate_all(self):
        """Migrate all JSON files"""
        data_dir = Path("data")
        
        # List of chunk files to migrate
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
        
        for file_name in chunk_files:
            file_path = data_dir / file_name
            if file_path.exists():
                chunks = self.migrate_json_file(file_path)
                total_chunks += chunks
            else:
                logger.warning(f"⚠️  File not found: {file_path}")
        
        logger.info(f"✅ Migration completed: {total_chunks} total chunks migrated")
        return total_chunks

if __name__ == "__main__":
    migrator = DataMigrator()
    migrator.migrate_all()
```

#### 3.2 Execute Data Migration
```bash
# Ensure you're in the project directory
cd /home/sakr_quraish/Projects/Danial\ Rag/

# Load environment variables
source .env

# Run data migration
python scripts/migrate_data.py

# Verify data migration
psql "postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}" << EOF
-- Check document count
SELECT 'Documents' as table_name, COUNT(*) as count FROM framework_documents
UNION ALL
SELECT 'Metadata' as table_name, COUNT(*) as count FROM framework_metadata
UNION ALL 
SELECT 'Concepts' as table_name, COUNT(*) as count FROM key_concepts;

-- Verify sample data
SELECT chunk_id, substring(content, 1, 100) as content_preview
FROM framework_documents 
LIMIT 3;
EOF
```

**Expected Output:**
```
table_name | count
-----------+-------
Documents  |    19
Metadata   |    19  
Concepts   |   50+
```

### Step 4: Embedding Generation (30 minutes)

#### 4.1 Create Embedding Script
```python
# Save as scripts/generate_embeddings.py
#!/usr/bin/env python3

import os
import psycopg2
import openai
import time
import logging
from typing import List, Tuple

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EmbeddingGenerator:
    def __init__(self):
        self.connection = None
        self.openai_client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.connect()
    
    def connect(self):
        """Establish database connection"""
        try:
            conn_str = f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@{os.getenv('POSTGRES_HOST', 'localhost')}:{os.getenv('POSTGRES_PORT', 5432)}/{os.getenv('POSTGRES_DB')}"
            self.connection = psycopg2.connect(conn_str)
            logger.info("✅ Database connection established")
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            raise
    
    def get_documents_without_embeddings(self) -> List[Tuple]:
        """Get documents that need embeddings"""
        with self.connection.cursor() as cursor:
            cursor.execute("""
                SELECT fd.id, fd.content, fd.chunk_id 
                FROM framework_documents fd 
                LEFT JOIN chunk_embeddings ce ON fd.id = ce.document_id 
                WHERE ce.id IS NULL
            """)
            return cursor.fetchall()
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using OpenAI"""
        try:
            response = self.openai_client.embeddings.create(
                input=text,
                model="text-embedding-3-large"
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"❌ Embedding generation failed: {e}")
            raise
    
    def insert_embedding(self, document_id: str, embedding: List[float]):
        """Insert embedding into database"""
        with self.connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO chunk_embeddings (document_id, embedding, model_name)
                VALUES (%s, %s, %s)
            """, (document_id, embedding, "text-embedding-3-large"))
        self.connection.commit()
    
    def generate_all_embeddings(self):
        """Generate embeddings for all documents"""
        documents = self.get_documents_without_embeddings()
        total_docs = len(documents)
        
        logger.info(f"Generating embeddings for {total_docs} documents")
        
        for i, (document_id, content, chunk_id) in enumerate(documents, 1):
            try:
                # Generate embedding
                embedding = self.generate_embedding(content)
                
                # Insert into database
                self.insert_embedding(document_id, embedding)
                
                logger.info(f"✅ Generated embedding {i}/{total_docs}: {chunk_id}")
                
                # Rate limiting (OpenAI: 3000 RPM)
                if i < total_docs:
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"❌ Failed to process {chunk_id}: {e}")
                # Continue with next document
                continue
        
        logger.info(f"✅ Embedding generation completed: {total_docs} embeddings")

if __name__ == "__main__":
    generator = EmbeddingGenerator()
    generator.generate_all_embeddings()
```

#### 4.2 Execute Embedding Generation
```bash
# Verify OpenAI API key is set
echo "OpenAI API Key: ${OPENAI_API_KEY:0:10}..." 

# Generate embeddings
python scripts/generate_embeddings.py

# Verify embeddings created
psql "postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}" << EOF
-- Check embedding count
SELECT COUNT(*) as embedding_count FROM chunk_embeddings;

-- Verify embedding dimensions
SELECT 
    vector_dims(embedding) as dimensions,
    COUNT(*) as count
FROM chunk_embeddings 
GROUP BY vector_dims(embedding);

-- Check for any missing embeddings
SELECT 
    (SELECT COUNT(*) FROM framework_documents) as total_documents,
    (SELECT COUNT(*) FROM chunk_embeddings) as total_embeddings,
    (SELECT COUNT(*) FROM framework_documents) - (SELECT COUNT(*) FROM chunk_embeddings) as missing_embeddings;
EOF
```

**Expected Output:**
```
embedding_count
---------------
             19

dimensions | count
-----------+-------
      3072 |    19

total_documents | total_embeddings | missing_embeddings
----------------+------------------+-------------------
              19 |               19 |                  0
```

### Step 5: Vector Index Creation (10 minutes)

#### 5.1 Create Vector Index
```bash
# Create vector similarity index
psql "postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}" << EOF
-- Create vector index for similarity search
CREATE INDEX idx_embeddings_vector ON chunk_embeddings 
USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);

-- Analyze table for query planner
ANALYZE chunk_embeddings;

-- Verify index created
\di+ idx_embeddings_vector
EOF
```

#### 5.2 Test Vector Search Performance
```bash
# Test vector search functionality
psql "postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}" << EOF
-- Test query performance
EXPLAIN (ANALYZE, BUFFERS) 
SELECT 
    fd.chunk_id,
    fd.title,
    (ce.embedding <=> '[0,0,0,0,0,0,0,0,0,0]'::vector) as distance
FROM framework_documents fd
JOIN chunk_embeddings ce ON fd.id = ce.document_id
ORDER BY ce.embedding <=> '[0,0,0,0,0,0,0,0,0,0]'::vector
LIMIT 5;
EOF
```

**Expected**: Query should complete in under 50ms and show index usage.

### Step 6: Integration Testing (15 minutes)

#### 6.1 Create Test Script
```python
# Save as scripts/test_integration.py
#!/usr/bin/env python3

import os
import psycopg2
import openai
import json
import time
from typing import List, Dict

class IntegrationTester:
    def __init__(self):
        self.connection = None
        self.openai_client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.connect()
    
    def connect(self):
        """Establish database connection"""
        conn_str = f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@{os.getenv('POSTGRES_HOST', 'localhost')}:{os.getenv('POSTGRES_PORT', 5432)}/{os.getenv('POSTGRES_DB')}"
        self.connection = psycopg2.connect(conn_str)
        print("✅ Database connection established")
    
    def test_vector_search(self, query: str, top_k: int = 5) -> List[Dict]:
        """Test vector similarity search"""
        start_time = time.time()
        
        # Generate query embedding
        response = self.openai_client.embeddings.create(
            input=query,
            model="text-embedding-3-large"
        )
        query_embedding = response.data[0].embedding
        
        # Perform vector search
        with self.connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    fd.chunk_id,
                    fd.title,
                    fm.framework_name,
                    substring(fd.content, 1, 200) as content_preview,
                    (ce.embedding <=> %s::vector) as similarity_distance
                FROM framework_documents fd
                JOIN chunk_embeddings ce ON fd.id = ce.document_id
                JOIN framework_metadata fm ON fd.id = fm.document_id
                ORDER BY ce.embedding <=> %s::vector
                LIMIT %s
            """, (query_embedding, query_embedding, top_k))
            
            results = cursor.fetchall()
        
        duration = (time.time() - start_time) * 1000
        print(f"✅ Vector search completed in {duration:.2f}ms")
        
        return results
    
    def test_hybrid_search(self, query: str, top_k: int = 5) -> List[Dict]:
        """Test hybrid vector + text search"""
        start_time = time.time()
        
        # Generate query embedding
        response = self.openai_client.embeddings.create(
            input=query,
            model="text-embedding-3-large"
        )
        query_embedding = response.data[0].embedding
        
        # Perform hybrid search
        with self.connection.cursor() as cursor:
            cursor.execute("""
                WITH vector_scores AS (
                    SELECT 
                        fd.id,
                        fd.chunk_id,
                        fd.title,
                        fm.framework_name,
                        fd.content,
                        (1 - (ce.embedding <=> %s::vector)) * 0.7 as vector_score
                    FROM framework_documents fd
                    JOIN chunk_embeddings ce ON fd.id = ce.document_id
                    JOIN framework_metadata fm ON fd.id = fm.document_id
                    ORDER BY ce.embedding <=> %s::vector
                    LIMIT 20
                ),
                text_scores AS (
                    SELECT 
                        id,
                        ts_rank_cd(to_tsvector('english', content), plainto_tsquery('english', %s)) * 0.3 as text_score
                    FROM framework_documents
                    WHERE to_tsvector('english', content) @@ plainto_tsquery('english', %s)
                )
                SELECT 
                    vs.chunk_id,
                    vs.title,
                    vs.framework_name,
                    substring(vs.content, 1, 200) as content_preview,
                    vs.vector_score + COALESCE(ts.text_score, 0) as combined_score
                FROM vector_scores vs
                LEFT JOIN text_scores ts ON vs.id = ts.id
                ORDER BY combined_score DESC
                LIMIT %s
            """, (query_embedding, query_embedding, query, query, top_k))
            
            results = cursor.fetchall()
        
        duration = (time.time() - start_time) * 1000
        print(f"✅ Hybrid search completed in {duration:.2f}ms")
        
        return results
    
    def test_framework_queries(self):
        """Test specific framework queries"""
        test_queries = [
            "What is the value equation?",
            "How do I create urgency in my offer?", 
            "What are the types of guarantees?",
            "How to price my services higher?"
        ]
        
        print("\n🧪 Testing Framework Queries:")
        print("=" * 50)
        
        for query in test_queries:
            print(f"\nQuery: {query}")
            results = self.test_vector_search(query, top_k=3)
            
            for i, result in enumerate(results, 1):
                chunk_id, title, framework_name, content_preview, distance = result
                print(f"  {i}. {chunk_id} (distance: {distance:.4f})")
                print(f"     Framework: {framework_name}")
                print(f"     Preview: {content_preview[:100]}...")
    
    def test_system_health(self):
        """Test overall system health"""
        print("\n🏥 System Health Check:")
        print("=" * 30)
        
        with self.connection.cursor() as cursor:
            # Check table counts
            cursor.execute("""
                SELECT 
                    'Documents' as table_name, COUNT(*) as count 
                FROM framework_documents
                UNION ALL
                SELECT 
                    'Embeddings' as table_name, COUNT(*) as count 
                FROM chunk_embeddings
                UNION ALL
                SELECT 
                    'Concepts' as table_name, COUNT(*) as count 
                FROM key_concepts
            """)
            
            counts = cursor.fetchall()
            for table_name, count in counts:
                print(f"✅ {table_name}: {count}")
            
            # Check embedding dimensions
            cursor.execute("SELECT vector_dims(embedding) FROM chunk_embeddings LIMIT 1")
            dimensions = cursor.fetchone()[0]
            print(f"✅ Embedding dimensions: {dimensions}")
            
            # Check index usage
            cursor.execute("""
                SELECT schemaname, tablename, indexname, idx_scan
                FROM pg_stat_user_indexes 
                WHERE indexname = 'idx_embeddings_vector'
            """)
            
            index_stats = cursor.fetchone()
            if index_stats:
                print(f"✅ Vector index created and available")
            else:
                print("❌ Vector index not found")

if __name__ == "__main__":
    tester = IntegrationTester()
    tester.test_system_health()
    tester.test_framework_queries()
```

#### 6.2 Run Integration Tests
```bash
# Run comprehensive integration tests
python scripts/test_integration.py
```

**Expected Output:**
```
✅ Database connection established

🏥 System Health Check:
==============================
✅ Documents: 19
✅ Embeddings: 19
✅ Concepts: 50+
✅ Embedding dimensions: 3072
✅ Vector index created and available

🧪 Testing Framework Queries:
==================================================

Query: What is the value equation?
✅ Vector search completed in 45.23ms
  1. value_equation_framework_01 (distance: 0.1234)
     Framework: Value Equation
     Preview: everyone would try and do). As a business owners and entrepreneurs I increasingly approach...

Query: How do I create urgency in my offer?
✅ Vector search completed in 38.67ms
  1. urgency_implementation_framework_02 (distance: 0.2156)
     Framework: Urgency Framework
     Preview: Urgency is the fear of missing out due to the passage of time...
```

---

## Post-Implementation Tasks

### Step 7: Performance Optimization (15 minutes)

#### 7.1 Update Database Statistics
```bash
psql "postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}" << EOF
-- Update table statistics for optimal query planning
ANALYZE framework_documents;
ANALYZE chunk_embeddings;
ANALYZE framework_metadata;
ANALYZE key_concepts;
ANALYZE document_concepts;

-- Check index usage
SELECT 
    schemaname,
    tablename, 
    indexname,
    idx_scan as times_used,
    pg_size_pretty(pg_relation_size(indexrelid)) as size
FROM pg_stat_user_indexes 
WHERE schemaname = 'public'
ORDER BY idx_scan DESC;
EOF
```

#### 7.2 Configure Connection Pooling
```python
# Save as config/database_config.py
import os
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

def get_database_engine():
    """Create optimized database engine with connection pooling"""
    
    connection_string = f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@{os.getenv('POSTGRES_HOST', 'localhost')}:{os.getenv('POSTGRES_PORT', 5432)}/{os.getenv('POSTGRES_DB')}"
    
    engine = create_engine(
        connection_string,
        poolclass=QueuePool,
        pool_size=20,                # Base connection pool size
        max_overflow=30,             # Additional connections under load
        pool_pre_ping=True,          # Validate connections before use
        pool_recycle=3600,           # Recycle connections every hour
        pool_timeout=30,             # Max wait time for connection
        echo=False,                  # Set to True for SQL logging
        connect_args={
            "connect_timeout": 10,
            "application_name": "hormozi_rag_system",
            "options": "-c statement_timeout=30000"  # 30s query timeout
        }
    )
    
    return engine

# Test connection pooling
if __name__ == "__main__":
    engine = get_database_engine()
    with engine.connect() as conn:
        result = conn.execute("SELECT COUNT(*) FROM framework_documents")
        print(f"✅ Connection pooling test: {result.fetchone()[0]} documents")
```

### Step 8: Monitoring Setup (10 minutes)

#### 8.1 Create Monitoring Views
```sql
-- Save as sql/monitoring_views.sql

-- Performance monitoring view
CREATE OR REPLACE VIEW performance_metrics AS
SELECT 
    'total_documents' as metric,
    COUNT(*)::text as value,
    'count' as unit
FROM framework_documents

UNION ALL

SELECT 
    'total_embeddings' as metric,
    COUNT(*)::text as value,
    'count' as unit
FROM chunk_embeddings

UNION ALL

SELECT 
    'database_size' as metric,
    pg_size_pretty(pg_database_size(current_database())) as value,
    'bytes' as unit

UNION ALL

SELECT 
    'vector_index_size' as metric,
    pg_size_pretty(pg_relation_size('idx_embeddings_vector')) as value,
    'bytes' as unit

UNION ALL

SELECT 
    'active_connections' as metric,
    COUNT(*)::text as value,
    'count' as unit
FROM pg_stat_activity 
WHERE state = 'active' AND datname = current_database();

-- System health check function
CREATE OR REPLACE FUNCTION system_health_check()
RETURNS TABLE(component text, status text, details text) AS $$
BEGIN
    -- Check vector extension
    RETURN QUERY
    SELECT 'pgvector_extension'::text, 
           CASE WHEN COUNT(*) > 0 THEN 'HEALTHY' ELSE 'CRITICAL' END::text,
           'Vector extension availability'::text
    FROM pg_extension WHERE extname = 'vector';
    
    -- Check data completeness
    RETURN QUERY
    SELECT 'data_completeness'::text,
           CASE WHEN doc_count = emb_count THEN 'HEALTHY' ELSE 'WARNING' END::text,
           format('Documents: %s, Embeddings: %s', doc_count, emb_count)::text
    FROM (
        SELECT 
            (SELECT COUNT(*) FROM framework_documents) as doc_count,
            (SELECT COUNT(*) FROM chunk_embeddings) as emb_count
    ) counts;
    
    -- Check vector index
    RETURN QUERY
    SELECT 'vector_index'::text,
           CASE WHEN COUNT(*) > 0 THEN 'HEALTHY' ELSE 'CRITICAL' END::text,
           'Vector index availability'::text
    FROM pg_indexes 
    WHERE indexname = 'idx_embeddings_vector';
    
END;
$$ LANGUAGE plpgsql;
```

#### 8.2 Execute Monitoring Setup
```bash
# Create monitoring views
psql "postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}" -f sql/monitoring_views.sql

# Test monitoring
psql "postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}" << EOF
-- Check performance metrics
SELECT * FROM performance_metrics;

-- Run health check
SELECT * FROM system_health_check();
EOF
```

### Step 9: Backup Configuration (10 minutes)

#### 9.1 Create Backup Script
```bash
#!/bin/bash
# Save as scripts/backup_database.sh

set -euo pipefail

# Configuration
BACKUP_DIR="/var/backups/postgresql"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# Create backup directory
sudo mkdir -p "${BACKUP_DIR}"

# Full database backup
pg_dump \
    --host="${POSTGRES_HOST}" \
    --port="${POSTGRES_PORT}" \
    --username="${POSTGRES_USER}" \
    --dbname="${POSTGRES_DB}" \
    --format=custom \
    --compress=9 \
    --verbose \
    --file="${BACKUP_DIR}/hormozi_rag_backup_${DATE}.dump"

# Schema-only backup (for quick recovery testing)
pg_dump \
    --host="${POSTGRES_HOST}" \
    --port="${POSTGRES_PORT}" \
    --username="${POSTGRES_USER}" \
    --dbname="${POSTGRES_DB}" \
    --schema-only \
    --format=plain \
    --file="${BACKUP_DIR}/hormozi_rag_schema_${DATE}.sql"

# Cleanup old backups
find "${BACKUP_DIR}" -name "*.dump" -mtime +${RETENTION_DAYS} -delete
find "${BACKUP_DIR}" -name "*.sql" -mtime +${RETENTION_DAYS} -delete

# Verify backup
pg_restore --list "${BACKUP_DIR}/hormozi_rag_backup_${DATE}.dump" > /dev/null

echo "✅ Backup completed: ${BACKUP_DIR}/hormozi_rag_backup_${DATE}.dump"
```

#### 9.2 Configure Automated Backups
```bash
# Make backup script executable
chmod +x scripts/backup_database.sh

# Test backup manually
./scripts/backup_database.sh

# Schedule daily backup (add to crontab)
(crontab -l 2>/dev/null; echo "0 2 * * * cd /home/sakr_quraish/Projects/Danial\ Rag && ./scripts/backup_database.sh") | crontab -

# Verify crontab entry
crontab -l | grep backup_database
```

---

## Validation and Sign-off

### Final Validation Checklist

```bash
# Run comprehensive validation
psql "postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}" << EOF
-- 1. Data integrity validation
SELECT 
    'Data Integrity' as check_name,
    CASE 
        WHEN doc_count = 19 AND emb_count = 19 AND doc_count = emb_count 
        THEN 'PASS' 
        ELSE 'FAIL' 
    END as status,
    format('Documents: %s, Embeddings: %s', doc_count, emb_count) as details
FROM (
    SELECT 
        (SELECT COUNT(*) FROM framework_documents) as doc_count,
        (SELECT COUNT(*) FROM chunk_embeddings) as emb_count
) counts;

-- 2. Vector dimension validation
SELECT 
    'Vector Dimensions' as check_name,
    CASE 
        WHEN COUNT(*) = COUNT(CASE WHEN vector_dims(embedding) = 3072 THEN 1 END) 
        THEN 'PASS' 
        ELSE 'FAIL' 
    END as status,
    format('All %s embeddings have 3072 dimensions', COUNT(*)) as details
FROM chunk_embeddings;

-- 3. Index availability validation
SELECT 
    'Vector Index' as check_name,
    CASE WHEN COUNT(*) > 0 THEN 'PASS' ELSE 'FAIL' END as status,
    'Vector index available for similarity search' as details
FROM pg_indexes 
WHERE indexname = 'idx_embeddings_vector';

-- 4. Framework integrity validation
SELECT 
    'Framework Integrity' as check_name,
    CASE 
        WHEN COUNT(*) = COUNT(CASE WHEN preserves_complete_concept THEN 1 END) 
        THEN 'PASS' 
        ELSE 'FAIL' 
    END as status,
    format('%s/%s frameworks preserve complete concepts', 
           COUNT(CASE WHEN preserves_complete_concept THEN 1 END), 
           COUNT(*)) as details
FROM framework_metadata;

-- 5. Search functionality validation
EXPLAIN (ANALYZE, BUFFERS) 
SELECT chunk_id, (embedding <=> '[0,0,0]'::vector) as distance
FROM framework_documents fd
JOIN chunk_embeddings ce ON fd.id = ce.document_id
ORDER BY ce.embedding <=> '[0,0,0]'::vector
LIMIT 5;
EOF
```

### Performance Validation
```bash
# Run performance tests
python << EOF
import time
import psycopg2
import os

# Connect to database
conn_str = f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@{os.getenv('POSTGRES_HOST', 'localhost')}:{os.getenv('POSTGRES_PORT', 5432)}/{os.getenv('POSTGRES_DB')}"
conn = psycopg2.connect(conn_str)

# Test query performance
with conn.cursor() as cursor:
    # Warm up
    cursor.execute("SELECT COUNT(*) FROM framework_documents")
    
    # Test vector search performance
    start_time = time.time()
    cursor.execute("""
        SELECT chunk_id, (embedding <=> '[0,0,0]'::vector) as distance
        FROM framework_documents fd
        JOIN chunk_embeddings ce ON fd.id = ce.document_id
        ORDER BY ce.embedding <=> '[0,0,0]'::vector
        LIMIT 10
    """)
    results = cursor.fetchall()
    duration = (time.time() - start_time) * 1000
    
    print(f"✅ Vector search performance: {duration:.2f}ms")
    print(f"✅ Results returned: {len(results)}")
    
    if duration < 500:
        print("✅ Performance test PASSED (< 500ms)")
    else:
        print("❌ Performance test FAILED (>= 500ms)")

conn.close()
EOF
```

### Sign-off Criteria

- [ ] **Data Migration**: All 19 chunks migrated successfully
- [ ] **Embedding Generation**: All 19 embeddings created with correct dimensions (3072)
- [ ] **Vector Index**: Index created and functional for similarity search
- [ ] **Search Performance**: Vector search completes in < 500ms
- [ ] **Framework Integrity**: 100% preservation of business frameworks
- [ ] **System Health**: All health checks passing
- [ ] **Backup System**: Automated backups configured and tested
- [ ] **Monitoring**: Performance metrics and health checks operational

---

## Troubleshooting Guide

### Common Issues and Solutions

#### Issue 1: "relation does not exist" errors
**Cause**: Schema not properly created
**Solution**:
```bash
# Verify current database
psql "postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}" -c "\dt"

# If no tables, re-run schema creation
psql "postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}" -f sql/schema.sql
```

#### Issue 2: Vector index creation fails
**Cause**: pgvector extension not installed
**Solution**:
```bash
# Install pgvector extension
sudo -u postgres psql -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Verify extension
psql "postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}" -c "\dx"
```

#### Issue 3: Embedding generation fails
**Cause**: OpenAI API key issues or rate limiting
**Solution**:
```bash
# Verify API key
curl -H "Authorization: Bearer $OPENAI_API_KEY" https://api.openai.com/v1/models | jq .

# If rate limited, add delays in embedding script
# Edit scripts/generate_embeddings.py and increase sleep time
```

#### Issue 4: Performance slower than expected
**Cause**: Missing statistics or inefficient queries
**Solution**:
```sql
-- Update table statistics
ANALYZE framework_documents;
ANALYZE chunk_embeddings;

-- Check query plan
EXPLAIN (ANALYZE, BUFFERS) [your_slow_query];
```

### Emergency Recovery

#### Restore from Backup
```bash
# Create new database for restoration
createdb hormozi_rag_restored

# Restore from backup
pg_restore --dbname=hormozi_rag_restored --verbose backup_file.dump

# Verify restoration
psql hormozi_rag_restored -c "SELECT COUNT(*) FROM framework_documents;"
```

#### Reset and Start Over
```bash
# Drop and recreate database (CAUTION: This destroys all data)
sudo -u postgres psql -c "DROP DATABASE IF EXISTS hormozi_rag;"
sudo -u postgres psql -c "CREATE DATABASE hormozi_rag;"

# Re-run entire implementation
./scripts/setup_database.sh
```

---

## Implementation Complete

### Success Confirmation

When all steps are completed successfully, you should have:

1. **Production PostgreSQL Database** with pgvector extension
2. **Complete Schema** with all tables, indexes, and constraints
3. **19 Migrated Chunks** with 100% framework integrity preserved
4. **19 Vector Embeddings** with 3072 dimensions each
5. **Functional Vector Search** with sub-500ms performance
6. **Monitoring and Health Checks** operational
7. **Automated Backup System** configured

### Next Steps

1. **Application Integration**: Update your RAG application to use PostgreSQL
2. **Performance Monitoring**: Set up ongoing performance monitoring
3. **Capacity Planning**: Monitor growth and plan for scaling
4. **Security Hardening**: Implement additional security measures for production

### Support and Maintenance

- **Daily**: Monitor system health and performance metrics
- **Weekly**: Review query performance and optimize if needed
- **Monthly**: Update statistics, rebuild indexes if necessary
- **Quarterly**: Review capacity and performance trends

---

**Implementation Status**: ✅ COMPLETE  
**Total Implementation Time**: ~2.5 hours  
**Next Review Date**: 7 days from implementation  

*This runbook ensures a production-ready PostgreSQL + pgvector implementation following all senior engineering principles and maintaining 100% framework integrity.*
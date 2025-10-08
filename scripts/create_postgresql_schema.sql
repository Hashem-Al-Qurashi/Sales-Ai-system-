-- PostgreSQL Schema Creation Script
-- Following DATABASE_ENGINEERING_SPEC.md exactly
-- Generated from specification document

-- 1. framework_documents (Primary Entity)
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
    CONSTRAINT non_empty_chunk_id CHECK (length(trim(chunk_id)) > 0),
    CONSTRAINT valid_source_file CHECK (source_file ~ '^[A-Za-z0-9_.-]+$')
);

-- Indexes for Performance
CREATE INDEX idx_documents_chunk_id ON framework_documents(chunk_id);
CREATE INDEX idx_documents_section ON framework_documents(section);
CREATE INDEX idx_documents_source_file ON framework_documents(source_file);
CREATE INDEX idx_documents_created_at ON framework_documents(created_at);

-- Full-Text Search Indexes
CREATE INDEX idx_documents_content_fts ON framework_documents 
USING gin(to_tsvector('english', content));
CREATE INDEX idx_documents_title_fts ON framework_documents 
USING gin(to_tsvector('english', title));

-- 2. chunk_embeddings (Vector Storage)
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

-- Vector Similarity Index (Critical for Performance)
CREATE INDEX idx_embeddings_vector ON chunk_embeddings 
USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);

-- Operational Indexes
CREATE INDEX idx_embeddings_document_id ON chunk_embeddings(document_id);
CREATE INDEX idx_embeddings_model ON chunk_embeddings(model_name);
CREATE INDEX idx_embeddings_created_at ON chunk_embeddings(created_at);

-- 3. framework_metadata (Business Context)
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
    CONSTRAINT valid_word_count CHECK (word_count > 0 AND word_count <= 15000),
    CONSTRAINT logical_word_char_ratio CHECK (character_count >= word_count * 3)
);

-- Business Query Indexes
CREATE INDEX idx_metadata_framework_name ON framework_metadata(framework_name);
CREATE INDEX idx_metadata_chunk_type ON framework_metadata(chunk_type);
CREATE INDEX idx_metadata_processing_date ON framework_metadata(processing_date);
CREATE INDEX idx_metadata_validation ON framework_metadata(validation_passed);

-- 4. key_concepts & document_concepts (Semantic Relationships)
CREATE TABLE key_concepts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    concept_name VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT non_empty_concept_name CHECK (length(trim(concept_name)) > 0),
    CONSTRAINT valid_concept_format CHECK (concept_name ~ '^[A-Za-z0-9 &-]+$')
);

CREATE TABLE document_concepts (
    document_id UUID REFERENCES framework_documents(id) ON DELETE CASCADE,
    concept_id UUID REFERENCES key_concepts(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (document_id, concept_id)
);

-- Concept Search Indexes
CREATE INDEX idx_concepts_name ON key_concepts(concept_name);
CREATE INDEX idx_document_concepts_document_id ON document_concepts(document_id);
CREATE INDEX idx_document_concepts_concept_id ON document_concepts(concept_id);

-- 5. source_lines (Line Tracking)
CREATE TABLE source_lines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES framework_documents(id) ON DELETE CASCADE,
    start_line INTEGER,
    end_line INTEGER
);

CREATE INDEX idx_source_lines_document_id ON source_lines(document_id);
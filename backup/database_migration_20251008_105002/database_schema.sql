CREATE TABLE framework_documents (
                    id TEXT PRIMARY KEY,
                    chunk_id TEXT UNIQUE NOT NULL,
                    source_file TEXT NOT NULL,
                    section TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    -- Data Quality Constraints (SQLite equivalent)
                    CHECK (length(trim(content)) > 0),
                    CHECK (length(trim(chunk_id)) > 0)
                )

CREATE TABLE key_concepts (
                    id TEXT PRIMARY KEY,
                    concept_name TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    CHECK (length(trim(concept_name)) > 0)
                )

CREATE TABLE document_concepts (
                    document_id TEXT REFERENCES framework_documents(id) ON DELETE CASCADE,
                    concept_id TEXT REFERENCES key_concepts(id) ON DELETE CASCADE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (document_id, concept_id)
                )

CREATE TABLE chunk_embeddings (
                    id TEXT PRIMARY KEY,
                    document_id TEXT REFERENCES framework_documents(id) ON DELETE CASCADE,
                    embedding_data TEXT, -- JSON serialized vector for SQLite
                    model_name TEXT DEFAULT 'text-embedding-3-large' NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    CHECK (model_name IN ('text-embedding-3-large', 'text-embedding-3-small'))
                )

CREATE VIRTUAL TABLE documents_fts USING fts5(
                    chunk_id, title, content, 
                    content='framework_documents', content_rowid='id'
                )

CREATE TABLE 'documents_fts_data'(id INTEGER PRIMARY KEY, block BLOB)

CREATE TABLE 'documents_fts_idx'(segid, term, pgno, PRIMARY KEY(segid, term)) WITHOUT ROWID

CREATE TABLE 'documents_fts_docsize'(id INTEGER PRIMARY KEY, sz BLOB)

CREATE TABLE 'documents_fts_config'(k PRIMARY KEY, v) WITHOUT ROWID

CREATE TABLE framework_metadata (
                id TEXT PRIMARY KEY,
                document_id TEXT REFERENCES framework_documents(id) ON DELETE CASCADE,
                character_count INTEGER NOT NULL,
                word_count INTEGER NOT NULL,
                chunk_type TEXT NOT NULL,
                framework_name TEXT,
                preserves_complete_concept BOOLEAN DEFAULT TRUE,
                overlap_with_previous TEXT,
                contains_formula BOOLEAN DEFAULT FALSE,
                contains_list BOOLEAN DEFAULT FALSE,
                contains_example BOOLEAN DEFAULT FALSE,
                business_logic_intact BOOLEAN DEFAULT TRUE,
                validation_passed BOOLEAN DEFAULT FALSE,
                processing_date DATE,
                guidelines_compliance TEXT,
                
                -- Relaxed constraints
                CHECK (character_count > 0 AND character_count <= 50000),
                CHECK (word_count > 0 AND word_count <= 15000)
            )
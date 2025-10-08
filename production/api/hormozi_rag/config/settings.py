"""
Configuration management for Hormozi RAG System.

SENIOR ENGINEERING APPROACH:
- Simple environment-based configuration
- No complex dataclasses or hierarchies  
- Validation at runtime, not initialization
- Follows ARCHITECTURE.md "Configuration Over Code" principle
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
# Following ARCHITECTURE.md "Configuration Over Code" principle
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent  # Go up to main project root
ENV_FILE = PROJECT_ROOT / "production" / "config" / ".env"
load_dotenv(ENV_FILE)

# Project paths
DATA_DIR = PROJECT_ROOT / "data"


class Settings:
    """
    Simple, environment-driven configuration.
    
    Follows ARCHITECTURE.md principle: "Configuration Over Code"
    No complex dataclasses - just simple environment variable mapping.
    """
    
    # Project Paths
    DATA_DIR = DATA_DIR
    PROJECT_ROOT = PROJECT_ROOT
    
    # Environment
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # API Keys (Required)
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    COHERE_API_KEY = os.getenv("COHERE_API_KEY", "")
    
    # Embedding Configuration
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
    EMBEDDING_DIMENSIONS = 3072  # For text-embedding-3-large
    
    # Chunking Configuration
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1500"))
    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))
    
    # Vector Database
    VECTOR_DB_TYPE = os.getenv("VECTOR_DB_TYPE", "postgresql")
    
    # PostgreSQL Configuration (per DECISION_LOG.md 2025-10-06 PostgreSQL + pgvector decision)
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_DB = os.getenv("POSTGRES_DB", "hormozi_rag")
    POSTGRES_USER = os.getenv("POSTGRES_USER", "rag_app_user")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")
    
    # API Configuration
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("API_PORT", "8000"))
    
    # Performance Limits (from ARCHITECTURE.md)
    MAX_CHUNKS_PER_QUERY = int(os.getenv("MAX_CHUNKS_PER_QUERY", "20"))
    MAX_RESPONSE_TIME_SECONDS = int(os.getenv("MAX_RESPONSE_TIME_SECONDS", "5"))
    
    @classmethod
    def validate(cls) -> None:
        """
        Runtime validation as required by ARCHITECTURE.md.
        
        Follows DEVELOPMENT_RULES.md: "Fail fast, recover gracefully"
        """
        errors = []
        
        # Required API keys
        if not cls.OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY environment variable is required")
        
        # Logical constraints
        if cls.CHUNK_OVERLAP >= cls.CHUNK_SIZE:
            errors.append(f"CHUNK_OVERLAP ({cls.CHUNK_OVERLAP}) must be less than CHUNK_SIZE ({cls.CHUNK_SIZE})")
        
        # Supported configurations per DECISION_LOG.md
        if cls.VECTOR_DB_TYPE not in ["postgresql", "chroma", "pinecone", "weaviate"]:
            errors.append(f"VECTOR_DB_TYPE must be one of: postgresql, chroma, pinecone, weaviate. Got: {cls.VECTOR_DB_TYPE}")
        
        # PostgreSQL-specific validation (per DATABASE_ENGINEERING_SPEC.md)
        if cls.VECTOR_DB_TYPE == "postgresql":
            if not cls.POSTGRES_PASSWORD:
                errors.append("POSTGRES_PASSWORD environment variable is required for PostgreSQL")
            if not cls.POSTGRES_HOST:
                errors.append("POSTGRES_HOST environment variable is required for PostgreSQL")
            if not cls.POSTGRES_DB:
                errors.append("POSTGRES_DB environment variable is required for PostgreSQL")
        
        if errors:
            raise ValueError("Configuration validation failed:\n" + "\n".join(f"  - {error}" for error in errors))
    
    @classmethod
    def ensure_directories(cls) -> None:
        """Ensure required directories exist."""
        directories = [
            DATA_DIR / "raw",
            DATA_DIR / "processed", 
            DATA_DIR / "embeddings",
            DATA_DIR / "logs"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)


# Global settings instance - validated once on import
settings = Settings()
settings.validate()
settings.ensure_directories()
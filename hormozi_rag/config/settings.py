"""
Configuration management for Hormozi RAG System.

This module centralizes all configuration parameters for the production-grade
RAG system designed for Alex Hormozi's $100M Offers framework retrieval.
"""

import os
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"


@dataclass
class PDFConfig:
    """Configuration for PDF processing."""
    
    source_files: List[Path] = field(default_factory=lambda: [
        DATA_DIR / "raw" / "$100m Offers.pdf",
        DATA_DIR / "raw" / "The_Lost_Chapter-Your_First_Avatar.pdf"
    ])
    extraction_method: str = "pdfplumber"  # Options: pdfplumber, pypdf2, pymupdf
    preserve_formatting: bool = True
    extract_images: bool = False
    min_text_length: int = 50  # Minimum characters for valid text block


@dataclass
class ChunkingConfig:
    """Configuration for text chunking strategies."""
    
    # Framework preservation settings
    preserve_frameworks: bool = True
    framework_boundaries: Dict[str, int] = field(default_factory=lambda: {
        "value_equation": 2000,  # Max chars for Value Equation framework
        "offer_stack": 3000,      # Max chars for Offer Creation Stack
        "guarantee": 2500,        # Max chars for Guarantee Framework
        "pricing": 2500,          # Max chars for Pricing Psychology
        "scarcity": 2000,         # Max chars for Scarcity/Urgency
        "bonus": 2000            # Max chars for Bonus Strategy
    })
    
    # Standard chunking parameters
    default_chunk_size: int = 1500
    chunk_overlap: int = 200
    min_chunk_size: int = 500
    max_chunk_size: int = 4000
    
    # Hierarchical chunking
    enable_hierarchical: bool = True
    hierarchy_levels: List[str] = field(default_factory=lambda: [
        "chapter", "section", "subsection", "paragraph"
    ])


@dataclass
class EmbeddingConfig:
    """Configuration for embedding generation."""
    
    model_name: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
    dimensions: int = 3072  # For text-embedding-3-large
    batch_size: int = 100
    normalize_embeddings: bool = True
    
    # OpenAI API settings
    api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    max_retries: int = 3
    timeout: int = 30
    
    # Caching
    cache_embeddings: bool = True
    cache_dir: Path = field(default_factory=lambda: DATA_DIR / "embeddings")


@dataclass
class MetadataConfig:
    """Configuration for chunk metadata enrichment."""
    
    priority_levels: List[str] = field(default_factory=lambda: [
        "GOLD", "SILVER", "BRONZE"
    ])
    
    content_types: List[str] = field(default_factory=lambda: [
        "definition", "process", "example", "template"
    ])
    
    use_cases: List[str] = field(default_factory=lambda: [
        "offer_creation", "objection_handling", "pricing", 
        "guarantee_design", "bonus_creation", "urgency_creation"
    ])
    
    # Scoring parameters
    enable_importance_scoring: bool = True
    default_importance_score: float = 5.0
    manual_quality_rating: bool = True
    
    # Tracking
    track_usage: bool = True
    track_effectiveness: bool = True


@dataclass
class StorageConfig:
    """Configuration for data storage."""
    
    backend: str = "postgresql"  # Options: postgresql, chromadb, qdrant
    
    # PostgreSQL settings
    postgres_host: str = field(default_factory=lambda: os.getenv("POSTGRES_HOST", "localhost"))
    postgres_port: int = field(default_factory=lambda: int(os.getenv("POSTGRES_PORT", "5432")))
    postgres_db: str = field(default_factory=lambda: os.getenv("POSTGRES_DB", "hormozi_rag"))
    postgres_user: str = field(default_factory=lambda: os.getenv("POSTGRES_USER", "postgres"))
    postgres_password: str = field(default_factory=lambda: os.getenv("POSTGRES_PASSWORD", ""))
    
    # Vector storage settings
    vector_table_name: str = "framework_chunks"
    vector_dimension: int = 3072
    distance_metric: str = "cosine"  # Options: cosine, euclidean, manhattan
    
    # Index settings
    create_indexes: bool = True
    index_type: str = "ivfflat"  # Options: ivfflat, hnsw


@dataclass
class RetrievalConfig:
    """Configuration for retrieval strategies."""
    
    # Search strategies
    enable_hybrid_search: bool = True
    vector_weight: float = 0.7  # Weight for vector similarity (0-1)
    keyword_weight: float = 0.3  # Weight for keyword matching (0-1)
    
    # Retrieval parameters
    top_k: int = 10  # Number of candidates to retrieve
    similarity_threshold: float = 0.7  # Minimum similarity score
    
    # Reranking
    enable_reranking: bool = True
    reranker_model: str = "cohere"  # Options: cohere, cross-encoder, none
    reranker_top_k: int = 5  # Final number of results after reranking
    
    # Cohere settings
    cohere_api_key: str = field(default_factory=lambda: os.getenv("COHERE_API_KEY", ""))
    
    # Query processing
    enable_query_expansion: bool = True
    enable_spell_correction: bool = True
    enable_synonym_matching: bool = True


@dataclass
class FrameworkConfig:
    """Configuration for framework-specific settings."""
    
    # Core frameworks from $100M Offers
    core_frameworks: Dict[str, Dict] = field(default_factory=lambda: {
        "value_equation": {
            "name": "Value Equation",
            "priority": "GOLD",
            "components": [
                "dream_outcome", 
                "perceived_likelihood", 
                "time_delay", 
                "effort_sacrifice"
            ],
            "preserve_whole": True
        },
        "offer_stack": {
            "name": "Offer Creation Stack",
            "priority": "GOLD",
            "steps": 5,
            "preserve_sequence": True
        },
        "pricing_psychology": {
            "name": "Pricing Psychology",
            "priority": "GOLD",
            "subtopics": [
                "divergent_pricing", 
                "price_anchoring", 
                "premium_psychology"
            ]
        },
        "guarantee_framework": {
            "name": "Guarantee Framework",
            "priority": "GOLD",
            "types": [
                "unconditional", 
                "conditional", 
                "anti_guarantee", 
                "implied"
            ]
        },
        "scarcity_urgency": {
            "name": "Scarcity & Urgency",
            "priority": "SILVER",
            "models": [
                "limited_supply", 
                "limited_time", 
                "limited_bonus"
            ]
        },
        "bonus_strategy": {
            "name": "Bonus Strategy",
            "priority": "SILVER",
            "principles": [
                "worth_entire_price", 
                "named_products", 
                "10x_value_stack"
            ]
        }
    })
    
    # Framework detection patterns
    detection_patterns: Dict[str, List[str]] = field(default_factory=lambda: {
        "value_equation": [
            "Value =", "Dream Outcome", "Perceived Likelihood",
            "Time Delay", "Effort & Sacrifice", "value equation"
        ],
        "offer_stack": [
            "offer creation", "identify dream outcome", "list all problems",
            "turn problems into solutions", "delivery vehicles"
        ],
        "pricing_psychology": [
            "divergent pricing", "price anchor", "premium pricing",
            "charge different people", "value-based pricing"
        ],
        "guarantee_framework": [
            "unconditional guarantee", "conditional guarantee",
            "anti-guarantee", "implied guarantee", "risk reversal"
        ]
    })


@dataclass
class APIConfig:
    """Configuration for API settings."""
    
    # Flask settings
    host: str = "0.0.0.0"
    port: int = 5000
    debug: bool = field(default_factory=lambda: os.getenv("FLASK_DEBUG", "False").lower() == "true")
    
    # API settings
    rate_limit: str = "100/hour"
    enable_cors: bool = True
    cors_origins: List[str] = field(default_factory=lambda: ["*"])
    
    # Authentication
    enable_auth: bool = False
    api_key_header: str = "X-API-Key"
    
    # Response settings
    max_response_chunks: int = 10
    include_metadata: bool = True
    include_sources: bool = True


@dataclass
class LoggingConfig:
    """Configuration for logging and monitoring."""
    
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_file: Optional[Path] = field(default_factory=lambda: DATA_DIR / "logs" / "hormozi_rag.log")
    
    # Monitoring
    enable_metrics: bool = True
    metrics_backend: str = "prometheus"  # Options: prometheus, datadog, none
    
    # Performance tracking
    track_query_latency: bool = True
    track_retrieval_quality: bool = True
    track_user_feedback: bool = True


@dataclass
class ValidationConfig:
    """Configuration for quality validation."""
    
    # Test queries that must work perfectly
    core_test_queries: List[Dict[str, str]] = field(default_factory=lambda: [
        {
            "query": "What's the value equation?",
            "expected_framework": "value_equation",
            "expected_components": ["formula", "dream_outcome", "perceived_likelihood"]
        },
        {
            "query": "How do I create an irresistible offer for web design?",
            "expected_framework": "offer_stack",
            "expected_process": True
        },
        {
            "query": "Give me examples of guarantees for service businesses",
            "expected_framework": "guarantee_framework",
            "expected_types": 4
        },
        {
            "query": "How do I justify charging $10k instead of $5k?",
            "expected_frameworks": ["value_equation", "pricing_psychology"],
            "expected_tactics": True
        }
    ])
    
    # Quality thresholds
    min_precision: float = 0.9
    min_recall: float = 0.85
    min_framework_completeness: float = 1.0  # 100% - frameworks must be complete
    
    # Validation frequency
    run_validation_on_startup: bool = True
    periodic_validation_hours: int = 24


@dataclass
class CohesionConfig:
    """Configuration for cohesion preservation system."""
    
    # Main settings
    enable_cohesion_detection: bool = True
    framework_detection_confidence: float = 0.8
    list_min_items: int = 2
    sequence_min_steps: int = 2
    max_atomic_chunk_size: int = 4000  # chars
    validation_strictness: str = "high"  # "low", "medium", "high"
    
    # Performance settings
    enable_pattern_caching: bool = True
    batch_size_for_large_docs: int = 50000
    max_processing_time_seconds: int = 300
    
    # Quality thresholds
    min_cohesion_score: float = 0.5
    min_framework_integrity: float = 0.95
    min_list_completeness: float = 0.90
    min_example_coherence: float = 0.85


@dataclass
class Settings:
    """Master configuration container."""
    
    pdf: PDFConfig = field(default_factory=PDFConfig)
    chunking: ChunkingConfig = field(default_factory=ChunkingConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    metadata: MetadataConfig = field(default_factory=MetadataConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)
    framework: FrameworkConfig = field(default_factory=FrameworkConfig)
    api: APIConfig = field(default_factory=APIConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    validation: ValidationConfig = field(default_factory=ValidationConfig)
    cohesion: CohesionConfig = field(default_factory=CohesionConfig)
    
    # Environment
    environment: str = field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    
    def __post_init__(self):
        """Post-initialization validation and setup."""
        # Create necessary directories
        self.pdf.source_files[0].parent.mkdir(parents=True, exist_ok=True)
        self.embedding.cache_dir.mkdir(parents=True, exist_ok=True)
        
        if self.logging.log_file:
            self.logging.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Validate API keys
        if not self.embedding.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        if self.retrieval.enable_reranking and self.retrieval.reranker_model == "cohere":
            if not self.retrieval.cohere_api_key:
                # Only warn in development, disable reranking
                if self.environment == "development":
                    print("⚠️  COHERE_API_KEY not set, disabling reranking for development")
                    self.retrieval.enable_reranking = False
                else:
                    raise ValueError("COHERE_API_KEY is required for Cohere reranking in production")
    
    @classmethod
    def load_from_env(cls) -> "Settings":
        """Load settings from environment variables."""
        return cls()


# Global settings instance
settings = Settings.load_from_env()
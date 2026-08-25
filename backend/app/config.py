"""Configuration management using Pydantic Settings."""

from pathlib import Path
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ==========================================================================
    # Project
    # ==========================================================================
    PROJECT_NAME: str = Field(default="Insight Engine", description="Project name")
    PROJECT_PREFIX: str = Field(
        default="ie", description="Project prefix for container names"
    )

    # ==========================================================================
    # API
    # ==========================================================================
    API_HOST: str = Field(default="0.0.0.0", description="API host")
    BACKEND_PORT: int = Field(default=8000, description="Backend API port")
    API_RELOAD: bool = Field(default=True, description="Enable auto-reload")
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:5173", "http://localhost:8000"],
        description="Allowed CORS origins",
    )

    # ==========================================================================
    # Database
    # ==========================================================================
    SQLITE_PATH: str = Field(default="./app.db", description="SQLite database path")
    SQLITE_ECHO: bool = Field(default=False, description="Echo SQL queries")

    # ==========================================================================
    # ChromaDB
    # ==========================================================================
    CHROMA_PATH: str = Field(
        default="./chroma_data", description="ChromaDB persistence directory"
    )
    CHROMA_COLLECTION: str = Field(
        default="events", description="ChromaDB collection name"
    )

    # ==========================================================================
    # Ollama
    # ==========================================================================
    OLLAMA_HOST: str = Field(default="ollama", description="Ollama service host")
    OLLAMA_PORT: int = Field(default=11434, description="Ollama service port")
    OLLAMA_EMBED_MODEL: str = Field(
        default="mxbai-embed-large:335m",
        description="Ollama embedding model name",
    )
    OLLAMA_LLM_MODEL: str = Field(
        default="llama3.2:3b",
        description="Ollama LLM model name",
    )
    OLLAMA_TIMEOUT: int = Field(
        default=60, description="Ollama request timeout in seconds"
    )
    OLLAMA_EMBED_BATCH_SIZE: int = Field(
        default=10, description="Batch size for embeddings"
    )
    OLLAMA_EMBED_DELAY: float = Field(
        default=0.1, description="Delay between embedding requests"
    )

    # ==========================================================================
    # Logging
    # ==========================================================================
    LOG_LEVEL: str = Field(default="INFO", description="Log level")
    LOG_FILE: str = Field(default="./logs/pipeline.log", description="Log file path")
    LOG_JSON: bool = Field(default=True, description="Output logs in JSON format")

    # ==========================================================================
    # Pipeline
    # ==========================================================================
    PIPELINE_MAX_EVENTS: int = Field(
        default=10000, description="Maximum events to process"
    )
    DUPLICATE_THRESHOLD: float = Field(
        default=0.92,
        description="Cosine similarity threshold for duplicate detection",
    )
    INSIGHT_TOP_K: int = Field(
        default=5,
        description="Number of top events to use for insight generation",
    )

    # ==========================================================================
    # Validators
    # ==========================================================================
    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v = v.upper()
        if v not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of {valid_levels}")
        return v

    @field_validator("DUPLICATE_THRESHOLD")
    @classmethod
    def validate_duplicate_threshold(cls, v: float) -> float:
        """Validate duplicate threshold is between 0 and 1."""
        if not 0 <= v <= 1:
            raise ValueError("DUPLICATE_THRESHOLD must be between 0 and 1")
        return v

    @property
    def ollama_base_url(self) -> str:
        """Get Ollama base URL."""
        return f"http://{self.OLLAMA_HOST}:{self.OLLAMA_PORT}"

    @property
    def chroma_persist_directory(self) -> Path:
        """Get ChromaDB persist directory as Path."""
        return Path(self.CHROMA_PATH)

    @property
    def sqlite_db_path(self) -> Path:
        """Get SQLite database path as Path."""
        return Path(self.SQLITE_PATH)

    @property
    def log_file_path(self) -> Path:
        """Get log file path as Path."""
        return Path(self.LOG_FILE)

    def setup_directories(self) -> None:
        """Create necessary directories."""
        dirs = [
            self.chroma_persist_directory,
            self.log_file_path.parent,
            self.sqlite_db_path.parent,
        ]
        for d in dirs:
            if str(d) != "." and not d.exists():
                d.mkdir(parents=True, exist_ok=True)

    def to_dict(self) -> dict:
        """Convert settings to dictionary (exclude sensitive info)."""
        return {
            "project_name": self.PROJECT_NAME,
            "api_host": self.API_HOST,
            "backend_port": self.BACKEND_PORT,
            "sqlite_path": str(self.sqlite_db_path),
            "chroma_path": str(self.chroma_persist_directory),
            "chroma_collection": self.CHROMA_COLLECTION,
            "ollama_host": self.OLLAMA_HOST,
            "ollama_port": self.OLLAMA_PORT,
            "ollama_embed_model": self.OLLAMA_EMBED_MODEL,
            "ollama_llm_model": self.OLLAMA_LLM_MODEL,
            "ollama_timeout": self.OLLAMA_TIMEOUT,
            "log_level": self.LOG_LEVEL,
            "log_file": str(self.log_file_path),
            "duplicate_threshold": self.DUPLICATE_THRESHOLD,
            "insight_top_k": self.INSIGHT_TOP_K,
        }


# Global settings instance
settings = Settings()

# Setup directories on import
settings.setup_directories()

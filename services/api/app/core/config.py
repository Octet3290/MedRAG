from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Centralized Application Configuration.
    Loads from environment variables or .env file with type validation.
    """

    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    PROJECT_NAME: str = "MedRAG - AI Knowledge Assistant"
    API_V1_PREFIX: str = "/api/v1"

    # Security
    SECRET_KEY: str = "insecure-default-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ALGORITHM: str = "HS256"

    # Database
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/medrag"

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # AI Model Configuration
    EMBEDDING_PROVIDER: str = "mock"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS: int = 1536
    EMBEDDING_API_KEY: str = ""

    LLM_PROVIDER: str = "mock"
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_API_KEY: str = ""

    # Document Ingestion
    MAX_UPLOAD_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB
    UPLOAD_DIR: str = "storage/uploads"
    CHUNK_SIZE_TOKENS: int = 500
    CHUNK_OVERLAP_TOKENS: int = 50

    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

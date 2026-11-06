from pathlib import Path
from uuid import UUID

from pydantic import SecretStr
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # General settings
    PROJECT_NAME: str = "lecture-ai"

    # Database settings
    DATABASE_URL: str

    # Authentication settings
    DEV_USER_ID: UUID | None = None
    SECRET_KEY: SecretStr | None = None
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Where ingested documents are stored
    DOCUMENTS_DIR: Path = Path("/data/documents")

    # AI settings
    OPENAI_API_KEY: str | None = None
    EMBEDDING_PROVIDER: str = "openai"  # or "local" / "hf"
    EMBEDDING_MODEL: str = "text-embedding-3-small"  # local:"BAAI/bge-m3"
    EMBEDDING_DIMENSIONS: int = 1024
    EMBEDDING_BATCH_SIZE: int = 256


settings = Settings()

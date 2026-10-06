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

    # AI settings
    OPENAI_API_KEY: str | None = None


settings = Settings()

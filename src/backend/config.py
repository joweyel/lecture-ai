from pydantic import SecretStr
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # General settings
    PROJECT_NAME: str = "learnbase"

    # Database settings
    DATABASE_URL: str

    # Authentication settings
    SECRET_KEY: SecretStr | None = None
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # AI settings
    OPENAI_API_KEY: str | None = None


settings = Settings()

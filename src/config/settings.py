from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    PROJECT_NAME: str
    PROJECT_VERSION: str
    PROJECT_DESCRIPTION: str
    DATABASE_URL: str
    API_PREFIX: str
    ALLOWED_HOSTS: List[str] = ["*"]
    SECRET_KEY: str
    ALGORITHM: str = "H256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    KAFKA_BOOTSTRAP_SERVERS: str
    KAFKA_TOPIC: str
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str
    SMTP_SERVER: str
    SMTP_PORT: int
    SMTP_USERNAME: str
    SMTP_PASSWORD: str
    GOOGLE_CLIENT_ID: int
    GOOGLE_CLIENT_SECRET: str
    FRONTEND_URL: str
    CELEREY_BROKER_URL: str

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()

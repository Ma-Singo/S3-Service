from functools import lru_cache
from pathlib import Path
from typing import Literal, List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env", case_sensitive=False, extra="ignore"
    )
    ##########################################
    # Application
    ##########################################
    APP_NAME: str = "Image Service"
    APP_ENV: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = False
    ALLOWED_HOSTS: List[str] = ["*"]
    API_V1_PREFIX: str = "/api/v1"

    ##########################################
    # Database
    ##########################################
    DATABASE_URL: str = "postgresql+asyncpg://joker:joker123@localhost:5432/jdb"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    ##########################################
    # AUTH / JWT
    ##########################################
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_ALGORITHM: str = "HS256"

    ##########################################
    # AWS
    ##########################################
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "us-east-1"
    AWS_ENDPOINT_URL: Optional[str] = None
    AWS_S3_BUCKET: Optional[str] = None

    MAX_IMAGE_SIZE_MB: int = 20
    MAX_IMAGE_DIMENSION: int = 8000

    MULTIPART_THRESHOLD: int = 50 * 1024 * 1024
    PART_SIZE: int = 50 * 1024 * 1024
    MAX_CONCURRENCY: int = 4

    # Upload limits - Documents
    MAX_PDF_SIZE_MB: int = 50
    MAX_DOC_SIZE_MB: int = 50
    MAX_DOC_PAGES: int = 1000
    MAX_PDF_PAGES: int = 1000


    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def max_image_size_bytes(self) -> int:
        return self.MAX_IMAGE_SIZE_MB * 1024 * 1024


    @property
    def max_pdf_size_bytes(self) -> int:
        return self.MAX_PDF_SIZE_MB * 1024 * 1024

    @property
    def max_doc_size_bytes(self) -> int:
        return self.MAX_DOC_SIZE_MB * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

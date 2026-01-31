from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Service
    SERVICE_NAME: str = "image-service"
    DEBUG: bool = False

    # JWT
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"

    # Nano Banana API
    NANO_BANANA_API_KEY: str = ""
    NANO_BANANA_API_URL: str = "https://api.nanobanana.ai/v1"

    # Local Storage (default - works without external services)
    STORAGE_PATH: str = "/app/storage"
    STORAGE_URL: str = "/storage"  # Served by FastAPI static files mount
    
    # Cloudflare R2 (optional - for production)
    R2_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY: str = ""
    R2_SECRET_KEY: str = ""
    R2_BUCKET_NAME: str = "keroxio-images"
    R2_PUBLIC_URL: str = ""

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # Upload limits
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS: list[str] = ["jpg", "jpeg", "png", "webp"]

    # CORS - Configure for production
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173,http://localhost:19006"

    class Config:
        env_file = ".env"
        extra = "ignore"

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins from string to list."""
        if self.CORS_ORIGINS == "*":
            return ["*"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

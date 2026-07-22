import os
from pathlib import Path
from pydantic_settings import BaseSettings

ROOT_DIR = Path(__file__).resolve().parents[3]

class Settings(BaseSettings):
    PROJECT_NAME: str = "Rover Enterprise API"
    VERSION: str = "2.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Security & Tokens
    SECRET_KEY: str = os.getenv("SECRET_KEY", "rover-super-secret-key-change-in-production-32bytes!")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # GitHub App & OAuth Credentials
    USE_GITHUB_APP: bool = os.getenv("USE_GITHUB_APP", "true").lower() == "true"
    GITHUB_APP_ID: str = os.getenv("GITHUB_APP_ID", "")
    GITHUB_CLIENT_ID: str = os.getenv("GITHUB_CLIENT_ID", "")
    GITHUB_CLIENT_SECRET: str = os.getenv("GITHUB_CLIENT_SECRET", "")
    GITHUB_PRIVATE_KEY: str = os.getenv("GITHUB_PRIVATE_KEY", "")
    WEBHOOK_SECRET: str = os.getenv("WEBHOOK_SECRET", "")
    
    # Environment-driven Domain URLs
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")
    BACKEND_URL: str = os.getenv("BACKEND_URL", "http://localhost:8000")
    GITHUB_REDIRECT_URI: str = os.getenv("GITHUB_REDIRECT_URI", "")

    @property
    def computed_redirect_uri(self) -> str:
        if self.GITHUB_REDIRECT_URI:
            return self.GITHUB_REDIRECT_URI
        base = self.FRONTEND_URL.rstrip('/')
        return f"{base}/auth/callback"


    
    # Bot identity for auto-commits
    ROVER_BOT_NAME: str = os.getenv("ROVER_BOT_NAME", "Rover Agent")
    ROVER_BOT_EMAIL: str = os.getenv("ROVER_BOT_EMAIL", "rover@internal.ai")
    
    # Databases & Caches
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./rover.db")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    
    # AI Models
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "qwen/qwen3-coder:free")
    
    # Extra fields from legacy .env
    LLM_PROVIDER: str = "gemini"
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GITHUB_TOKEN: str = ""
    GITHUB_INSTALLATION_ID: str = ""
    
    class Config:
        case_sensitive = True
        env_file = ".env"
        extra = "ignore"

settings = Settings()

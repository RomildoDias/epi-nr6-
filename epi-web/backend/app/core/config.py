# backend/app/core/config.py
from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    APP_NAME: str = "Controle EPI NR-6"
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 horas

    DATABASE_URL: str = "postgresql://epi_user:epi_pass@db:5432/epi_db"

    BASE_DIR: Path = Path(__file__).parent.parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    ASSETS_DIR: Path = BASE_DIR / "assets"
    FICHAS_DIR: Path = BASE_DIR / "data" / "fichas"
    QRCODES_DIR: Path = BASE_DIR / "assets" / "qrcodes"

    class Config:
        env_file = ".env"

settings = Settings()

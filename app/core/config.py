# app/core/config.py
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    APP_NAME: str = "Controle EPI NR-6"
    SECRET_KEY: str = ""
    ALGORITHM:  str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    # SQLite — caminho no disco persistente do Render (/data é o mountPath)
    DATABASE_URL: str = "sqlite:////data/epi.db"

    @property
    def BASE_DIR(self) -> Path:
        return Path(__file__).parent.parent.parent

    @property
    def DATA_DIR(self) -> Path:
        # Render monta o disco persistente em /data
        # Se não existir (local/dev), usa pasta data/ relativa
        render_disk = Path("/data")
        if render_disk.exists() and render_disk.is_dir():
            d = render_disk / "app_data"
        else:
            d = self.BASE_DIR / "data"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def FICHAS_DIR(self) -> Path:
        d = self.DATA_DIR / "fichas"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def QRCODES_DIR(self) -> Path:
        d = self.DATA_DIR / "qrcodes"
        d.mkdir(parents=True, exist_ok=True)
        return d

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()

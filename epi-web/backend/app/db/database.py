# backend/app/db/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Cria todas as tabelas e superadmin padrão."""
    from app.db import models_db  # noqa — registra os models
    Base.metadata.create_all(bind=engine)
    _seed_superadmin()


def _seed_superadmin():
    import os
    from app.db.models_db import Usuario
    from app.core.security import hash_password
    db = SessionLocal()
    try:
        if db.query(Usuario).filter(Usuario.login == "admin").first():
            return
        admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
        admin = Usuario(
            nome       = "Administrador",
            login      = "admin",
            senha_hash = hash_password(admin_password),
            perfil     = "superadmin",
            tenant_id  = None,
            ativo      = True,
            precisa_trocar_senha=True,
        )
        db.add(admin)
        db.commit()
        import logging
        logging.getLogger(__name__).info(
            f"Superadmin criado: login=admin (troque a senha o quanto antes)")
    finally:
        db.close()

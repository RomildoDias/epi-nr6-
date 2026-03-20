from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# SQLite precisa de connect_args especial; PostgreSQL não
_is_sqlite = settings.DATABASE_URL.startswith("sqlite")

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
    pool_pre_ping=True,
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
    from app.db import models_db  # noqa
    Base.metadata.create_all(bind=engine)
    _seed_initial_data()


def _seed_initial_data():
    from app.db.models_db import Usuario, Tenant, Config
    from app.core.security import hash_password
    db = SessionLocal()
    try:
        # Superadmin
        if not db.query(Usuario).filter(Usuario.login == "admin").first():
            db.add(Usuario(
                nome="Administrador", login="admin",
                senha_hash=hash_password("admin123"),
                perfil="superadmin", tenant_id=None, ativo=True,
            ))
            db.commit()
            print("✓ Superadmin criado: admin / admin123")

        # Tenants de exemplo (Norte/Nordeste)
        if db.query(Tenant).count() == 0:
            import uuid
            from datetime import datetime
            tenants_demo = [
                ("PA", "Filial Pará"),
                ("MA", "Filial Maranhão"),
                ("CE", "Filial Ceará"),
                ("BA", "Filial Bahia"),
            ]
            tenant_ids = {}
            for uf, nome in tenants_demo:
                t = Tenant(id=str(uuid.uuid4()), nome=nome,
                           estado_uf=uf, ativo=True)
                db.add(t)
                db.flush()
                tenant_ids[uf] = t.id

            # Admin para o Pará
            db.add(Usuario(
                nome="Admin Pará", login="admin.pa",
                senha_hash=hash_password("senha123"),
                perfil="admin", tenant_id=tenant_ids["PA"], ativo=True,
            ))
            # Operador para o Pará
            db.add(Usuario(
                nome="Operador Pará", login="op.pa",
                senha_hash=hash_password("senha123"),
                perfil="operador", tenant_id=tenant_ids["PA"], ativo=True,
            ))
            db.commit()
            print("✓ 4 estados de exemplo criados")
            print("✓ Usuários demo: admin.pa / senha123 | op.pa / senha123")

        # Config global padrão
        if db.query(Config).count() == 0:
            import uuid
            defaults = [
                ("empresa_nome",     "Minha Empresa Ltda"),
                ("empresa_cnpj",     "00.000.000/0001-00"),
                ("empresa_endereco", ""),
                ("dias_alerta_ca",   "30"),
            ]
            for chave, valor in defaults:
                db.add(Config(id=str(uuid.uuid4()),
                               tenant_id=None, chave=chave, valor=valor))
            db.commit()

    except Exception as e:
        db.rollback()
        print(f"Seed erro: {e}")
    finally:
        db.close()

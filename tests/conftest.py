import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base, get_db
from app.db.models_db import Usuario, Tenant, Config, EPI, Colaborador, Setor

TEST_DB_URL = "sqlite://"

engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Registra os modelos no metadata do Base (feito no módulo, antes de create_all)
_ = [Usuario, Tenant, Config, EPI, Colaborador, Setor]


def _seed_test_data():
    from datetime import datetime, date, timedelta
    import uuid
    from app.core.security import hash_password

    db = TestingSession()
    try:
        if db.query(Usuario).count() > 0:
            return

        db.add(Usuario(
            id=str(uuid.uuid4()), nome="Admin Teste",
            login="admin", senha_hash=hash_password("admin123"),
            perfil="superadmin", tenant_id=None, ativo=True,
            precisa_trocar_senha=True,
        ))

        t1 = Tenant(id=str(uuid.uuid4()), nome="Filial Teste 1", estado_uf="TF", ativo=True)
        t2 = Tenant(id=str(uuid.uuid4()), nome="Filial Teste 2", estado_uf="TS", ativo=True)
        db.add_all([t1, t2])
        db.flush()

        for nome, login, perfil, tid in [
            ("Admin TF", "admin.tf", "admin", t1.id),
            ("Operador TF", "op.tf", "operador", t1.id),
            ("Admin TS", "admin.ts", "admin", t2.id),
        ]:
            db.add(Usuario(
                id=str(uuid.uuid4()), nome=nome,
                login=login, senha_hash=hash_password("senha123"),
                perfil=perfil, tenant_id=tid, ativo=True,
                precisa_trocar_senha=True,
            ))

        db.add(Colaborador(
            id="colab-tf-1", tenant_id=t1.id,
            nome="Colaborador TF 1", matricula="TF001",
            setor="Producao", funcao="Operador", ativo=True,
            consentimento_dados=True, data_consentimento=datetime.utcnow(),
        ))
        db.add(Colaborador(
            id="colab-ts-1", tenant_id=t2.id,
            nome="Colaborador TS 1", matricula="TS001",
            setor="Producao", funcao="Operador", ativo=True,
            consentimento_dados=True, data_consentimento=datetime.utcnow(),
        ))

        hoje = date.today()
        db.add(EPI(
            id="epi-tf-1", tenant_id=t1.id,
            nome="Capacete Teste", ca="12345", fabricante="3M",
            tipo_protecao="Impacto", vida_util_dias=365,
            validade_ca=hoje + timedelta(days=365),
            estoque_minimo=5, quantidade=10, ativo=True,
        ))

        db.add_all([
            Setor(id=str(uuid.uuid4()), tenant_id=t1.id, nome="Producao"),
            Setor(id=str(uuid.uuid4()), tenant_id=t1.id, nome="Manutencao"),
            Setor(id=str(uuid.uuid4()), tenant_id=t2.id, nome="Producao"),
        ])

        db.add(Config(id=str(uuid.uuid4()), tenant_id=None,
                       chave="retencao_dias", valor="1825"))
        db.add(Config(id=str(uuid.uuid4()), tenant_id=None,
                       chave="empresa_nome", valor="Empresa Teste"))

        db.commit()
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_db(monkeypatch):
    """Cria tabelas, seed dados, desliga init_db() e rate limiter."""
    Base.metadata.create_all(bind=engine)
    _seed_test_data()

    monkeypatch.setattr("app.db.database.init_db", lambda: None)

    yield
    Base.metadata.drop_all(bind=engine)


def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def client():
    from app.main import app

    app.dependency_overrides[get_db] = override_get_db
    app.state.limiter.enabled = False

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def admin_headers(client):
    """Retorna headers de autenticação do superadmin."""
    r = client.post("/api/auth/login", json={"login": "admin", "senha": "admin123"})
    assert r.status_code == 200, f"Login admin falhou: {r.json()}"
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def user_headers(client):
    """Retorna headers de um admin de tenant (TF)."""
    r = client.post("/api/auth/login", json={"login": "admin.tf", "senha": "senha123"})
    assert r.status_code == 200, f"Login admin.tf falhou: {r.json()}"
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

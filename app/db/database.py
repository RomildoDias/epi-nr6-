# app/db/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from app.core.config import settings

_is_sqlite = settings.DATABASE_URL.startswith("sqlite")

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
    poolclass=NullPool if _is_sqlite else None,
    pool_size=5,
    max_overflow=3,
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
    from app.db.models_db import Usuario, Tenant, Config, EPI, Colaborador, Setor
    from app.core.security import hash_password
    from datetime import date, timedelta
    import uuid

    db = SessionLocal()
    try:
        # ── Superadmin ────────────────────────────────────────────────────
        if not db.query(Usuario).filter(Usuario.login == "admin").first():
            db.add(Usuario(
                id=str(uuid.uuid4()), nome="Administrador",
                login="admin", senha_hash=hash_password("admin123"),
                perfil="superadmin", tenant_id=None, ativo=True,
                precisa_trocar_senha=True,
            ))
            db.commit()
            print("✓ Superadmin criado: admin / admin123")

        # ── Tenants (estados) ─────────────────────────────────────────────
        if db.query(Tenant).count() > 0:
            return  # Já tem dados, não repete seed

        ESTADOS = [
            ("PA", "Filial Pará"),
            ("MA", "Filial Maranhão"),
            ("CE", "Filial Ceará"),
            ("BA", "Filial Bahia"),
            ("AM", "Filial Amazonas"),
            ("PE", "Filial Pernambuco"),
        ]

        tenant_ids = {}
        for uf, nome in ESTADOS:
            t = Tenant(id=str(uuid.uuid4()), nome=nome, estado_uf=uf, ativo=True)
            db.add(t)
            db.flush()
            tenant_ids[uf] = t.id

        db.commit()
        print(f"✓ {len(ESTADOS)} estados criados")

        # ── Usuários por estado ───────────────────────────────────────────
        usuarios_demo = [
            ("Admin Pará",       "admin.pa",  "admin",       "PA"),
            ("Operador Pará",    "op.pa",     "operador",    "PA"),
            ("Admin Maranhão",   "admin.ma",  "admin",       "MA"),
            ("Operador Maranhão","op.ma",     "operador",    "MA"),
            ("Admin Ceará",      "admin.ce",  "admin",       "CE"),
            ("Admin Bahia",      "admin.ba",  "admin",       "BA"),
            ("Admin Amazonas",   "admin.am",  "admin",       "AM"),
            ("Admin Pernambuco", "admin.pe",  "admin",       "PE"),
        ]
        for nome, login, perfil, uf in usuarios_demo:
            db.add(Usuario(
                id=str(uuid.uuid4()), nome=nome, login=login,
                senha_hash=hash_password("senha123"),
                perfil=perfil, tenant_id=tenant_ids[uf], ativo=True,
                precisa_trocar_senha=True,
            ))
        db.commit()
        print("✓ Usuários demo criados (senha: senha123)")

        # ── Setores por estado ────────────────────────────────────────────
        SETORES = ["Produção", "Manutenção", "Logística", "Administrativo", "Obras"]
        setor_map = {}  # (uf, nome) -> setor_id
        for uf in tenant_ids:
            for nome_setor in SETORES:
                s = Setor(id=str(uuid.uuid4()),
                          tenant_id=tenant_ids[uf], nome=nome_setor)
                db.add(s)
                db.flush()
                setor_map[(uf, nome_setor)] = nome_setor
        db.commit()

        # ── EPIs por estado ───────────────────────────────────────────────
        EPIS_BASE = [
            ("Capacete de Segurança",  "31148", "3M",        "Impacto",     730, 60,  10, 25),
            ("Luva de Raspa",          "10578", "Kalipso",   "Mãos",        180, 15,  20, 8),
            ("Protetor Auditivo",      "25853", "MSA",       "Auditiva",    365, 90,  15, 12),
            ("Óculos de Proteção",     "15920", "Uvex",      "Óptico",      365, 45,  10, 20),
            ("Bota de Segurança",      "37590", "Marluvas",  "Pés",         730, 90,  8,  15),
            ("Cinto de Segurança",     "28471", "Plastcor",  "Queda",       365, 30,  5,  7),
            ("Respirador PFF2",        "12345", "3M",        "Respiratória",90,  20,  30, 45),
            ("Luva de Borracha",       "54321", "Volk",      "Químico",     180, 60,  10, 18),
        ]

        hoje = date.today()
        # Validades variadas para demo (alguns vencidos, alguns a vencer)
        validades = [
            hoje + timedelta(days=365),   # OK
            hoje - timedelta(days=10),    # VENCIDO
            hoje + timedelta(days=20),    # ALERTA
            hoje + timedelta(days=300),   # OK
            hoje + timedelta(days=400),   # OK
            hoje + timedelta(days=15),    # ALERTA
            hoje + timedelta(days=180),   # OK
            hoje + timedelta(days=250),   # OK
        ]

        # Quantidades variadas (alguns abaixo do mínimo)
        qtd_override = {
            "PA": [25, 8, 8, 20, 15, 3, 45, 18],   # Luva e Protetor abaixo do mín
            "MA": [18, 22, 12, 15, 10, 6, 30, 14],
            "CE": [30, 15, 20, 25, 12, 4, 50, 20],
            "BA": [20, 18, 9, 18, 8,  5, 35, 16],
            "AM": [12, 10, 15, 10, 6, 2, 20, 10],
            "PE": [22, 20, 18, 22, 14, 7, 40, 18],
        }

        for uf, tid in tenant_ids.items():
            qtds = qtd_override.get(uf, [20]*8)
            for i, (nome, ca, fab, tipo, vida, _dummy, minimo, _qtd) in enumerate(EPIS_BASE):
                # CA único por tenant: sufixo do UF
                ca_tenant = f"{ca}"
                epi = EPI(
                    id=str(uuid.uuid4()), tenant_id=tid,
                    nome=nome, ca=ca_tenant, fabricante=fab,
                    tipo_protecao=tipo, vida_util_dias=vida,
                    validade_ca=validades[i % len(validades)],
                    estoque_minimo=minimo, quantidade=qtds[i],
                    ativo=True,
                )
                db.add(epi)
        db.commit()
        print("✓ EPIs demo criados para todos os estados")

        # ── Colaboradores por estado ──────────────────────────────────────
        NOMES = [
            ("João da Silva",    "001", "Produção",     "Operador"),
            ("Maria Souza",      "002", "Manutenção",   "Técnico"),
            ("Pedro Oliveira",   "003", "Logística",    "Motorista"),
            ("Ana Lima",         "004", "Produção",     "Operadora"),
            ("Carlos Mendes",    "005", "Obras",        "Pedreiro"),
            ("Fernanda Costa",   "006", "Administrativo","Assistente"),
        ]
        for uf, tid in tenant_ids.items():
            for nome, mat, setor, funcao in NOMES:
                c = Colaborador(
                    id=str(uuid.uuid4()), tenant_id=tid,
                    nome=nome, matricula=mat,
                    setor=setor, funcao=funcao, ativo=True,
                )
                db.add(c)
        db.commit()
        print("✓ Colaboradores demo criados para todos os estados")

        # ── Config global ─────────────────────────────────────────────────
        if db.query(Config).count() == 0:
            defaults = [
                ("empresa_nome",     "Transpetro Norte/Nordeste"),
                ("empresa_cnpj",     "00.000.000/0001-00"),
                ("empresa_endereco", "Av. Presidente Vargas, 328 - Belém/PA"),
                ("dias_alerta_ca",   "30"),
            ]
            for chave, valor in defaults:
                db.add(Config(id=str(uuid.uuid4()),
                               tenant_id=None, chave=chave, valor=valor))
            db.commit()

        print("✓ Dados demo inseridos com sucesso!")
        print("✓ Logins: admin/admin123 | admin.pa/senha123 | op.pa/senha123")

    except Exception as e:
        db.rollback()
        print(f"Seed erro (pode ser normal se dados já existem): {e}")
    finally:
        db.close()

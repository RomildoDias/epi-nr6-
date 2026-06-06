# app/db/database.py
import logging
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from app.core.config import settings

logger = logging.getLogger(__name__)

_is_sqlite = settings.DATABASE_URL.startswith("sqlite")

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
    poolclass=NullPool,
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
    _run_migrations()
    _seed_initial_data()


def _run_migrations():
    """Aplica alterações em tabelas existentes (create_all não adiciona colunas)."""
    import sqlalchemy as sa
    db = SessionLocal()
    try:
        conn = db.connection()
        inspector = sa.inspect(engine)
        cols = [c["name"] for c in inspector.get_columns("colaboradores")]
        if "consentimento_dados" not in cols:
            conn.execute(sa.text(
                "ALTER TABLE colaboradores ADD COLUMN consentimento_dados BOOLEAN DEFAULT 0"
            ))
        if "data_consentimento" not in cols:
            conn.execute(sa.text(
                "ALTER TABLE colaboradores ADD COLUMN data_consentimento TIMESTAMP"
            ))
        db.commit()
        logger.info("✓ Migrações aplicadas com sucesso")
    except Exception as e:
        logger.warning(f"Migrações: {e} (ignorado — provavelmente já existem)")
        db.rollback()
    finally:
        db.close()


def _seed_initial_data():
    from app.db.models_db import Usuario, Tenant, Config, EPI, Colaborador, Setor
    from app.core.security import hash_password
    from datetime import date, timedelta, datetime
    import uuid

    db = SessionLocal()
    try:
        admin = db.query(Usuario).filter(Usuario.login == "admin").first()
        if not admin:
            db.add(Usuario(
                id=str(uuid.uuid4()), nome="Administrador",
                login="admin", senha_hash=hash_password("admin123"),
                perfil="superadmin", tenant_id=None, ativo=True,
                precisa_trocar_senha=True,
            ))
            db.commit()
            logger.info("Superadmin criado: admin / admin123")

        if db.query(Tenant).count() > 0:
            logger.info("Dados demo já existem — seed pulado")
            return

        ESTADOS = [
            ("PA", "Filial Pará"),
            ("MA", "Filial Maranhão"),
            ("PI", "Filial Piauí"),
            ("CE", "Filial Ceará"),
            ("RN", "Filial Rio Grande do Norte"),
            ("PB", "Filial Paraíba"),
            ("PE", "Filial Pernambuco"),
            ("AL", "Filial Alagoas"),
            ("SE", "Filial Sergipe"),
            ("BA", "Filial Bahia"),
        ]

        tenant_ids = {}
        for uf, nome in ESTADOS:
            t = Tenant(id=str(uuid.uuid4()), nome=nome, estado_uf=uf, ativo=True)
            db.add(t)
            db.flush()
            tenant_ids[uf] = t.id

        db.commit()
        logger.info(f"{len(ESTADOS)} estados criados")

        usuarios_demo = [
            ("Admin Pará",        "admin.pa",  "admin",    "PA"),
            ("Operador Pará",     "op.pa",     "operador", "PA"),
            ("Admin Maranhão",    "admin.ma",  "admin",    "MA"),
            ("Operador Maranhão", "op.ma",     "operador", "MA"),
            ("Admin Piauí",       "admin.pi",  "admin",    "PI"),
            ("Operador Piauí",    "op.pi",     "operador", "PI"),
            ("Admin Ceará",       "admin.ce",  "admin",    "CE"),
            ("Operador Ceará",    "op.ce",     "operador", "CE"),
            ("Admin RN",          "admin.rn",  "admin",    "RN"),
            ("Operador RN",       "op.rn",     "operador", "RN"),
            ("Admin Paraíba",     "admin.pb",  "admin",    "PB"),
            ("Operador Paraíba",  "op.pb",     "operador", "PB"),
            ("Admin Pernambuco",  "admin.pe",  "admin",    "PE"),
            ("Operador PE",       "op.pe",     "operador", "PE"),
            ("Admin Alagoas",     "admin.al",  "admin",    "AL"),
            ("Operador Alagoas",  "op.al",     "operador", "AL"),
            ("Admin Sergipe",     "admin.se",  "admin",    "SE"),
            ("Operador Sergipe",  "op.se",     "operador", "SE"),
            ("Admin Bahia",       "admin.ba",  "admin",    "BA"),
            ("Operador Bahia",    "op.ba",     "operador", "BA"),
        ]
        for nome, login, perfil, uf in usuarios_demo:
            db.add(Usuario(
                id=str(uuid.uuid4()), nome=nome, login=login,
                senha_hash=hash_password("senha123"),
                perfil=perfil, tenant_id=tenant_ids[uf], ativo=True,
                precisa_trocar_senha=True,
            ))
        db.commit()
        logger.info("Usuários demo criados (senha: senha123)")

        SETORES = ["Produção", "Manutenção", "Logística", "Administrativo", "Obras"]
        for uf in tenant_ids:
            for nome_setor in SETORES:
                db.add(Setor(id=str(uuid.uuid4()),
                             tenant_id=tenant_ids[uf], nome=nome_setor))
        db.commit()

        EPIS_BASE = [
            ("Capacete de Segurança",  "31148", "3M",        "Impacto",     730, 10),
            ("Luva de Raspa",          "10578", "Kalipso",   "Mãos",        180, 20),
            ("Protetor Auditivo",      "25853", "MSA",       "Auditiva",    365, 15),
            ("Óculos de Proteção",     "15920", "Uvex",      "Óptico",      365, 10),
            ("Bota de Segurança",      "37590", "Marluvas",  "Pés",         730, 8),
            ("Cinto de Segurança",     "28471", "Plastcor",  "Queda",       365, 5),
            ("Respirador PFF2",        "12345", "3M",        "Respiratória",90,  30),
            ("Luva de Borracha",       "54321", "Volk",      "Químico",     180, 10),
        ]

        hoje = date.today()
        validades = [
            hoje + timedelta(days=365),
            hoje - timedelta(days=10),
            hoje + timedelta(days=20),
            hoje + timedelta(days=300),
            hoje + timedelta(days=400),
            hoje + timedelta(days=15),
            hoje + timedelta(days=180),
            hoje + timedelta(days=250),
        ]

        qtd_override = {
            "PA": [25, 8,  8,  20, 15, 3,  45, 18],
            "MA": [18, 22, 12, 15, 10, 6,  30, 14],
            "PI": [5,  30, 4,  25, 8,  2,  25, 10],
            "CE": [30, 15, 20, 25, 12, 4,  50, 20],
            "RN": [12, 10, 6,  10, 18, 7,  20, 12],
            "PB": [8,  25, 14, 18, 20, 5,  35, 22],
            "PE": [22, 20, 18, 22, 14, 7,  40, 18],
            "AL": [15, 12, 10, 14, 9,  11, 28, 16],
            "SE": [10, 18, 3,  8,  5,  9,  15, 8],
            "BA": [20, 9,  15, 18, 22, 6,  55, 10],
        }

        for uf, tid in tenant_ids.items():
            qtds = qtd_override.get(uf, [20]*8)
            for i, (nome, ca, fab, tipo, vida, minimo) in enumerate(EPIS_BASE):
                epi = EPI(
                    id=str(uuid.uuid4()), tenant_id=tid,
                    nome=nome, ca=ca, fabricante=fab,
                    tipo_protecao=tipo, vida_util_dias=vida,
                    validade_ca=validades[i % len(validades)],
                    estoque_minimo=minimo, quantidade=qtds[i],
                    ativo=True,
                )
                db.add(epi)
        db.commit()
        logger.info("EPIs demo criados para todos os estados")

        COLAB_POR_ESTADO = {
            "PA": [
                ("João Silva",      "PA001", "Produção",      "Operador"),
                ("Maria Santos",    "PA002", "Manutenção",    "Técnica"),
                ("Pedro Oliveira",  "PA003", "Logística",     "Motorista"),
                ("Ana Costa",       "PA004", "Produção",      "Operadora"),
                ("Carlos Souza",    "PA005", "Obras",         "Pedreiro"),
                ("Fernanda Lima",   "PA006", "Administrativo", "Assistente"),
            ],
            "MA": [
                ("Raimundo Alves",   "MA001", "Produção",     "Operador"),
                ("Francisca Pereira","MA002", "Manutenção",   "Técnica"),
                ("José Sousa",       "MA003", "Logística",    "Motorista"),
                ("Maria José",       "MA004", "Produção",     "Operadora"),
                ("Antonio Costa",    "MA005", "Obras",        "Pedreiro"),
                ("Luzia Santos",     "MA006", "Administrativo","Assistente"),
            ],
            "PI": [
                ("Francisco Oliveira","PI001", "Produção",    "Operador"),
                ("Rita Carvalho",    "PI002", "Manutenção",  "Técnica"),
                ("Manoel Silva",     "PI003", "Logística",   "Motorista"),
                ("Tereza Costa",     "PI004", "Produção",    "Operadora"),
                ("João Pedro",       "PI005", "Obras",       "Pedreiro"),
                ("Carmen Lúcia",     "PI006", "Administrativo","Assistente"),
            ],
            "CE": [
                ("Luiz Gonzaga",     "CE001", "Produção",     "Operador"),
                ("Socorro Almeida",  "CE002", "Manutenção",   "Técnica"),
                ("Vicente Leite",    "CE003", "Logística",    "Motorista"),
                ("Celeste Campos",   "CE004", "Produção",     "Operadora"),
                ("Raimundo Neto",    "CE005", "Obras",        "Pedreiro"),
                ("Helena Ferreira",  "CE006", "Administrativo","Assistente"),
            ],
            "RN": [
                ("Severino Ramos",   "RN001", "Produção",     "Operador"),
                ("Maria do Carmo",   "RN002", "Manutenção",   "Técnica"),
                ("José Ferreira",    "RN003", "Logística",    "Motorista"),
                ("Lúcia Batista",    "RN004", "Produção",     "Operadora"),
                ("Josefa Silva",     "RN005", "Obras",        "Pedreira"),
                ("João Eudes",       "RN006", "Administrativo","Assistente"),
            ],
            "PB": [
                ("Antônio Silva",    "PB001", "Produção",     "Operador"),
                ("Maria das Dores",  "PB002", "Manutenção",   "Técnica"),
                ("Carlos Alberto",   "PB003", "Logística",    "Motorista"),
                ("Rita de Cássia",   "PB004", "Produção",     "Operadora"),
                ("Ednaldo Pereira",  "PB005", "Obras",        "Pedreiro"),
                ("Socorro Lima",     "PB006", "Administrativo","Assistente"),
            ],
            "PE": [
                ("Joaquim Neto",     "PE001", "Produção",     "Operador"),
                ("Severina Oliveira","PE002", "Manutenção",   "Técnica"),
                ("Manoel Germano",   "PE003", "Logística",    "Motorista"),
                ("Maria Aparecida",  "PE004", "Produção",     "Operadora"),
                ("Ricardo Melo",     "PE005", "Obras",        "Pedreiro"),
                ("Ivone Alves",      "PE006", "Administrativo","Assistente"),
            ],
            "AL": [
                ("José Leandro",     "AL001", "Produção",     "Operador"),
                ("Maria Helena",     "AL002", "Manutenção",   "Técnica"),
                ("Pedro Paulo",      "AL003", "Logística",    "Motorista"),
                ("Ana Lúcia",        "AL004", "Produção",     "Operadora"),
                ("Mário Jorge",      "AL005", "Obras",        "Pedreiro"),
                ("Tânia Barros",     "AL006", "Administrativo","Assistente"),
            ],
            "SE": [
                ("Jorge Santos",     "SE001", "Produção",     "Operador"),
                ("Maria José",       "SE002", "Manutenção",   "Técnica"),
                ("Carlos Eduardo",   "SE003", "Logística",    "Motorista"),
                ("Adriana Menezes",  "SE004", "Produção",     "Operadora"),
                ("Luciano Souza",    "SE005", "Obras",        "Pedreiro"),
                ("Renata Oliveira",  "SE006", "Administrativo","Assistente"),
            ],
            "BA": [
                ("João de Deus",     "BA001", "Produção",     "Operador"),
                ("Maria Conceição",  "BA002", "Manutenção",   "Técnica"),
                ("Antônio Carlos",   "BA003", "Logística",    "Motorista"),
                ("Rita de Jesus",    "BA004", "Produção",     "Operadora"),
                ("José Raimundo",    "BA005", "Obras",        "Pedreiro"),
                ("Ana Paula",        "BA006", "Administrativo","Assistente"),
            ],
        }
        for uf, tid in tenant_ids.items():
            for nome, mat, setor, funcao in COLAB_POR_ESTADO[uf]:
                db.add(Colaborador(
                    id=str(uuid.uuid4()), tenant_id=tid,
                    nome=nome, matricula=mat,
                    setor=setor, funcao=funcao, ativo=True,
                    consentimento_dados=True,
                    data_consentimento=datetime.utcnow(),
                ))
        db.commit()
        logger.info("Colaboradores demo criados para todos os estados")

        if db.query(Config).count() == 0:
            defaults = [
                ("empresa_nome",     "Transpetro Norte/Nordeste"),
                ("empresa_cnpj",     "00.000.000/0001-00"),
                ("empresa_endereco", "Av. Presidente Vargas, 328 - Belém/PA"),
                ("dias_alerta_ca",   "30"),
                ("retencao_dias",    "1825"),
            ]
            for chave, valor in defaults:
                db.add(Config(id=str(uuid.uuid4()),
                               tenant_id=None, chave=chave, valor=valor))
            db.commit()

        logger.info("Dados demo inseridos com sucesso")
        logger.info("admin/admin123 | admin.{uf}/senha123 | op.{uf}/senha123")

    except Exception as e:
        db.rollback()
        logger.warning(f"Seed ignorado (dados já existem?): {e}")
    finally:
        db.close()

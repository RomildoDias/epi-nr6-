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
            # Remove dados demo antigos e recria com nova estrutura
            from app.db.models_db import Movimentacao, Entrega
            db.query(Movimentacao).delete()
            db.query(Entrega).delete()
            db.query(EPI).delete()
            db.query(Colaborador).delete()
            db.query(Setor).delete()
            db.query(Usuario).filter(Usuario.tenant_id != None).delete()
            db.query(Tenant).delete()
            db.commit()

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
        print(f"✓ {len(ESTADOS)} estados criados")

        # ── Usuários por estado ───────────────────────────────────────────
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
        print("✓ Usuários demo criados (senha: senha123)")

        # ── Setores por estado ────────────────────────────────────────────
        SETORES = ["Produção", "Manutenção", "Logística", "Administrativo", "Obras"]
        for uf in tenant_ids:
            for nome_setor in SETORES:
                db.add(Setor(id=str(uuid.uuid4()),
                             tenant_id=tenant_ids[uf], nome=nome_setor))
        db.commit()

        # ── EPIs por estado ───────────────────────────────────────────────
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
            hoje + timedelta(days=365),   # OK
            hoje - timedelta(days=10),    # VENCIDO
            hoje + timedelta(days=20),    # ALERTA
            hoje + timedelta(days=300),   # OK
            hoje + timedelta(days=400),   # OK
            hoje + timedelta(days=15),    # ALERTA
            hoje + timedelta(days=180),   # OK
            hoje + timedelta(days=250),   # OK (respirador vence em 90d, mas a validade CA é independente)
        ]

        # Cada estado com quantidades distintas para gerar alertas variados
        qtd_override = {
            "PA": [25, 8,  8,  20, 15, 3,  45, 18],   # alertas: luva(8<20), prot(8<15), cinto(3<5)
            "MA": [18, 22, 12, 15, 10, 6,  30, 14],   # alertas: cinto(6>5 ok), prot(12<15)
            "PI": [5,  30, 4,  25, 8,  2,  25, 10],   # alertas: capacete(5<10), prot(4<15), cinto(2<5), luvaB(10=ok)
            "CE": [30, 15, 20, 25, 12, 4,  50, 20],   # alertas: cinto(4<5)
            "RN": [12, 10, 6,  10, 18, 7,  20, 12],   # alertas: capacete(12>10 ok), luva(10<20), prot(6<15), oculos(10=ok)
            "PB": [8,  25, 14, 18, 20, 5,  35, 22],   # alertas: capacete(8<10)
            "PE": [22, 20, 18, 22, 14, 7,  40, 18],   # OK (tudo acima do minimo)
            "AL": [15, 12, 10, 14, 9,  11, 28, 16],   # alertas: luva(12<20), prot(10<15), bota(9>8 ok)
            "SE": [10, 18, 3,  8,  5,  9,  15, 8],    # alertas: prot(3<15), oculos(8<10), bota(5<8), resp(15<30), luvaB(8<10)
            "BA": [20, 9,  15, 18, 22, 6,  55, 10],   # alertas: luva(9<20), cinto(6>5 ok)
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
        print("✓ EPIs demo criados para todos os estados")

        # ── Colaboradores por estado ──────────────────────────────────────
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
                ))
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
        print("✓ Logins: admin/admin123 | admin.{uf}/senha123 | op.{uf}/senha123 (uf = pa,ma,pi,ce,rn,pb,pe,al,se,ba)")

    except Exception as e:
        db.rollback()
        print(f"Seed erro (pode ser normal se dados já existem): {e}")
    finally:
        db.close()

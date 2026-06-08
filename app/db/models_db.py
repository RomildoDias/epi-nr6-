# app/db/models_db.py
import uuid
from datetime import datetime
from sqlalchemy import (Column, String, Integer, Boolean, DateTime,
                        Date, ForeignKey, Text, UniqueConstraint, Index)
from sqlalchemy.orm import relationship
from app.db.database import Base


def new_uuid():
    return str(uuid.uuid4())


class Tenant(Base):
    __tablename__ = "tenants"
    id         = Column(String, primary_key=True, default=new_uuid)
    nome       = Column(String(120), nullable=False)
    estado_uf  = Column(String(2),   nullable=False)
    ativo      = Column(Boolean,     default=True)
    created_at = Column(DateTime,    default=datetime.utcnow)

    usuarios      = relationship("Usuario",      back_populates="tenant", lazy="select")
    epis          = relationship("EPI",          back_populates="tenant", lazy="select")
    colaboradores = relationship("Colaborador",  back_populates="tenant", lazy="select")
    setores       = relationship("Setor",        back_populates="tenant", lazy="select")


class Usuario(Base):
    __tablename__ = "usuarios"
    id          = Column(String,      primary_key=True, default=new_uuid)
    nome        = Column(String(120), nullable=False)
    login       = Column(String(60),  nullable=False, unique=True, index=True)
    senha_hash  = Column(String(200), nullable=False)
    perfil      = Column(String(20),  nullable=False, default="operador")
    tenant_id   = Column(String,      ForeignKey("tenants.id"), nullable=True, index=True)
    ativo       = Column(Boolean,     default=True)
    created_at  = Column(DateTime,    default=datetime.utcnow)
    ultimo_acesso = Column(DateTime,  nullable=True)  # rastreio de acesso
    precisa_trocar_senha = Column(Boolean, default=False)

    tenant = relationship("Tenant", back_populates="usuarios", lazy="select")


class EPI(Base):
    __tablename__ = "epis"
    # BUG FIX: índice composto para busca rápida por tenant+ativo
    __table_args__ = (
        Index("ix_epis_tenant_ativo", "tenant_id", "ativo"),
    )
    id             = Column(String,      primary_key=True, default=new_uuid)
    tenant_id      = Column(String,      ForeignKey("tenants.id"), nullable=True)
    nome           = Column(String(200), nullable=False)
    ca             = Column(String(20),  nullable=False)
    fabricante     = Column(String(120), nullable=False)
    tipo_protecao  = Column(String(60),  nullable=False)
    vida_util_dias = Column(Integer,     default=365)
    validade_ca    = Column(Date,        nullable=False)
    estoque_minimo = Column(Integer,     default=5)
    quantidade     = Column(Integer,     default=0)
    foto_path      = Column(String(300), nullable=True)
    ativo          = Column(Boolean,     default=True)
    created_at     = Column(DateTime,    default=datetime.utcnow)
    updated_at     = Column(DateTime,    default=datetime.utcnow, onupdate=datetime.utcnow)

    tenant        = relationship("Tenant",       back_populates="epis",     lazy="select")
    entregas      = relationship("Entrega",      back_populates="epi",      lazy="select")
    movimentacoes = relationship("Movimentacao", back_populates="epi",      lazy="select")


class Colaborador(Base):
    __tablename__ = "colaboradores"
    __table_args__ = (
        # BUG FIX: matrícula única por tenant (antes podia duplicar entre tenants)
        UniqueConstraint("tenant_id", "matricula", name="uq_colab_tenant_matricula"),
        Index("ix_colab_tenant_ativo", "tenant_id", "ativo"),
    )
    id         = Column(String,     primary_key=True, default=new_uuid)
    tenant_id  = Column(String,     ForeignKey("tenants.id"), nullable=True)
    nome       = Column(String(120), nullable=False)
    matricula  = Column(String(40),  nullable=False)
    setor      = Column(String(80),  nullable=False)
    funcao     = Column(String(80),  nullable=False)
    ativo      = Column(Boolean,     default=True)
    created_at = Column(DateTime,    default=datetime.utcnow)

    tenant   = relationship("Tenant",  back_populates="colaboradores", lazy="select")
    entregas = relationship("Entrega", back_populates="colaborador",   lazy="select")


class Setor(Base):
    __tablename__ = "setores"
    __table_args__ = (
        # BUG FIX: setor único por tenant
        UniqueConstraint("tenant_id", "nome", name="uq_setor_tenant_nome"),
    )
    id        = Column(String,    primary_key=True, default=new_uuid)
    tenant_id = Column(String,    ForeignKey("tenants.id"), nullable=True, index=True)
    nome      = Column(String(80), nullable=False)

    tenant = relationship("Tenant", back_populates="setores", lazy="select")


class Entrega(Base):
    __tablename__ = "entregas"
    __table_args__ = (
        Index("ix_entregas_tenant_data", "tenant_id", "data"),
    )
    id                = Column(String,   primary_key=True, default=new_uuid)
    tenant_id         = Column(String,   ForeignKey("tenants.id"), nullable=True)
    data              = Column(DateTime, default=datetime.utcnow,  nullable=False)
    colaborador_id    = Column(String,   ForeignKey("colaboradores.id"), nullable=False)
    epi_id            = Column(String,   ForeignKey("epis.id"),          nullable=False)
    quantidade        = Column(Integer,  nullable=False)
    validade_prevista = Column(Date,     nullable=True)
    observacao        = Column(Text,     nullable=True)
    responsavel       = Column(String(120), nullable=True)   # NOVO: quem fez a entrega
    pdf_path          = Column(String(300), nullable=True)

    colaborador = relationship("Colaborador", back_populates="entregas", lazy="select")
    epi         = relationship("EPI",         back_populates="entregas", lazy="select")


class Movimentacao(Base):
    __tablename__ = "movimentacoes"
    __table_args__ = (
        Index("ix_mov_tenant_data", "tenant_id", "data"),
        Index("ix_mov_epi",         "epi_id"),
    )
    id           = Column(String,      primary_key=True, default=new_uuid)
    tenant_id    = Column(String,      ForeignKey("tenants.id"), nullable=True)
    data         = Column(DateTime,    default=datetime.utcnow, nullable=False)
    tipo         = Column(String(20),  nullable=False)   # entrada|saida|ajuste
    epi_id       = Column(String,      ForeignKey("epis.id"), nullable=False)
    quantidade   = Column(Integer,     nullable=False)
    motivo       = Column(String(300), nullable=False)
    documento_nf = Column(String(80),  nullable=True)
    responsavel  = Column(String(120), nullable=False)

    epi = relationship("EPI", back_populates="movimentacoes", lazy="select")


class Config(Base):
    __tablename__ = "configs"
    __table_args__ = (
        # BUG FIX: chave única por tenant — antes podia criar configs duplicadas
        UniqueConstraint("tenant_id", "chave", name="uq_config_tenant_chave"),
    )
    id        = Column(String,      primary_key=True, default=new_uuid)
    tenant_id = Column(String,      nullable=True)
    chave     = Column(String(60),  nullable=False)
    valor     = Column(String(300), nullable=False)

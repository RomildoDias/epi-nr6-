# backend/app/db/models_db.py
import uuid
from datetime import datetime
from sqlalchemy import (Column, String, Integer, Boolean, DateTime,
                        Date, ForeignKey, Text, Float, UniqueConstraint)
from sqlalchemy.orm import relationship
from app.db.database import Base


def new_uuid():
    return str(uuid.uuid4())


class Tenant(Base):
    __tablename__ = "tenants"
    id         = Column(String, primary_key=True, default=new_uuid)
    nome       = Column(String(120), nullable=False)
    estado_uf  = Column(String(2),  nullable=False)
    ativo      = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    usuarios      = relationship("Usuario",      back_populates="tenant")
    epis          = relationship("EPI",          back_populates="tenant")
    colaboradores = relationship("Colaborador",  back_populates="tenant")
    setores       = relationship("Setor",        back_populates="tenant")


class Usuario(Base):
    __tablename__ = "usuarios"
    id          = Column(String, primary_key=True, default=new_uuid)
    nome        = Column(String(120), nullable=False)
    login       = Column(String(60),  nullable=False, unique=True, index=True)
    senha_hash  = Column(String(200), nullable=False)
    perfil      = Column(String(20),  nullable=False, default="operador")
    tenant_id   = Column(String, ForeignKey("tenants.id"), nullable=True)
    ativo       = Column(Boolean, default=True)
    created_at  = Column(DateTime, default=datetime.utcnow)
    ultimo_acesso = Column(DateTime, nullable=True)
    precisa_trocar_senha = Column(Boolean, default=False)

    tenant = relationship("Tenant", back_populates="usuarios")


class EPI(Base):
    __tablename__ = "epis"
    id             = Column(String, primary_key=True, default=new_uuid)
    tenant_id      = Column(String, ForeignKey("tenants.id"), nullable=True, index=True)
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

    tenant        = relationship("Tenant", back_populates="epis")
    entregas      = relationship("Entrega",      back_populates="epi")
    movimentacoes = relationship("Movimentacao", back_populates="epi")


class Colaborador(Base):
    __tablename__ = "colaboradores"
    id         = Column(String, primary_key=True, default=new_uuid)
    tenant_id  = Column(String, ForeignKey("tenants.id"), nullable=True, index=True)
    nome       = Column(String(120), nullable=False)
    matricula  = Column(String(40),  nullable=False)
    setor      = Column(String(80),  nullable=False)
    funcao     = Column(String(80),  nullable=False)
    ativo      = Column(Boolean, default=True)

    tenant   = relationship("Tenant", back_populates="colaboradores")
    entregas = relationship("Entrega", back_populates="colaborador")


class Setor(Base):
    __tablename__ = "setores"
    id        = Column(String, primary_key=True, default=new_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=True, index=True)
    nome      = Column(String(80), nullable=False)

    tenant = relationship("Tenant", back_populates="setores")


class Entrega(Base):
    __tablename__ = "entregas"
    id                = Column(String, primary_key=True, default=new_uuid)
    tenant_id         = Column(String, ForeignKey("tenants.id"), nullable=True, index=True)
    data              = Column(DateTime, default=datetime.utcnow)
    colaborador_id    = Column(String, ForeignKey("colaboradores.id"), nullable=False)
    epi_id            = Column(String, ForeignKey("epis.id"),          nullable=False)
    quantidade        = Column(Integer, nullable=False)
    validade_prevista = Column(Date,    nullable=True)
    observacao        = Column(Text,    nullable=True)
    pdf_path          = Column(String(300), nullable=True)
    responsavel       = Column(String(120), nullable=False, default="Sistema")

    colaborador = relationship("Colaborador", back_populates="entregas")
    epi         = relationship("EPI",         back_populates="entregas")


class Movimentacao(Base):
    __tablename__ = "movimentacoes"
    id           = Column(String, primary_key=True, default=new_uuid)
    tenant_id    = Column(String, ForeignKey("tenants.id"), nullable=True, index=True)
    data         = Column(DateTime, default=datetime.utcnow)
    tipo         = Column(String(20), nullable=False)   # entrada|saida|ajuste
    epi_id       = Column(String, ForeignKey("epis.id"), nullable=False)
    quantidade   = Column(Integer, nullable=False)
    motivo       = Column(String(300), nullable=False)
    documento_nf = Column(String(80),  nullable=True)
    responsavel  = Column(String(120), nullable=False)

    epi = relationship("EPI", back_populates="movimentacoes")


class Config(Base):
    __tablename__ = "configs"
    __table_args__ = (
        UniqueConstraint('tenant_id', 'chave', name='uq_tenant_config'),
    )
    id        = Column(String, primary_key=True, default=new_uuid)
    tenant_id = Column(String, nullable=True)
    chave     = Column(String(60),  nullable=False)
    valor     = Column(String(300), nullable=False)

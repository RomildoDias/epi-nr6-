# backend/app/db/schemas.py
from pydantic import BaseModel, field_validator
from datetime import date, datetime
from typing import Optional, List


# ── AUTH ────────────────────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    login: str
    senha: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    perfil: str
    nome: str
    tenant_id: Optional[str]
    tenant_nome: Optional[str]
    precisa_trocar_senha: bool = False


# ── TENANT ──────────────────────────────────────────────────────────────────
class TenantCreate(BaseModel):
    nome: str
    estado_uf: str

class TenantOut(BaseModel):
    id: str
    nome: str
    estado_uf: str
    ativo: bool
    model_config = {"from_attributes": True}


# ── USUARIO ─────────────────────────────────────────────────────────────────
class UsuarioCreate(BaseModel):
    nome: str
    login: str
    senha: str
    perfil: str = "operador"
    tenant_id: Optional[str] = None

class UsuarioUpdate(BaseModel):
    nome: Optional[str] = None
    perfil: Optional[str] = None
    tenant_id: Optional[str] = None
    ativo: Optional[bool] = None
    nova_senha: Optional[str] = None

class UsuarioOut(BaseModel):
    id: str
    nome: str
    login: str
    perfil: str
    tenant_id: Optional[str]
    ativo: bool
    model_config = {"from_attributes": True}


# ── EPI ─────────────────────────────────────────────────────────────────────
class EPICreate(BaseModel):
    nome: str
    ca: str
    fabricante: str
    tipo_protecao: str
    vida_util_dias: int = 365
    validade_ca: date
    estoque_minimo: int = 5
    quantidade: int = 0
    foto_path: Optional[str] = None

    @field_validator("ca")
    @classmethod
    def ca_digits(cls, v):
        if not str(v).strip().isdigit():
            raise ValueError("CA deve conter apenas dígitos")
        return v

    @field_validator("validade_ca")
    @classmethod
    def ca_nao_vencido(cls, v):
        if v < date.today():
            raise ValueError("Não é permitido cadastrar EPI com CA vencido")
        return v

class EPIUpdate(BaseModel):
    nome: Optional[str] = None
    ca: Optional[str] = None
    fabricante: Optional[str] = None
    tipo_protecao: Optional[str] = None
    vida_util_dias: Optional[int] = None
    validade_ca: Optional[date] = None
    estoque_minimo: Optional[int] = None
    quantidade: Optional[int] = None
    foto_path: Optional[str] = None

class EPIOut(BaseModel):
    id: str
    tenant_id: Optional[str]
    nome: str
    ca: str
    fabricante: str
    tipo_protecao: str
    vida_util_dias: int
    validade_ca: date
    estoque_minimo: int
    quantidade: int
    ativo: bool
    status: Optional[str] = None   # calculado
    model_config = {"from_attributes": True}


# ── COLABORADOR ─────────────────────────────────────────────────────────────
class ColaboradorCreate(BaseModel):
    nome: str
    matricula: str
    setor: str
    funcao: str

class ColaboradorOut(BaseModel):
    id: str
    nome: str
    matricula: str
    setor: str
    funcao: str
    ativo: bool
    model_config = {"from_attributes": True}


# ── ENTREGA ─────────────────────────────────────────────────────────────────
class EntregaCreate(BaseModel):
    colaborador_id: str
    epi_id: str
    quantidade: int
    observacao: Optional[str] = None
    responsavel: Optional[str] = "Sistema"

class EntregaOut(BaseModel):
    id: str
    data: datetime
    colaborador_id: str
    epi_id: str
    quantidade: int
    validade_prevista: Optional[date]
    observacao: Optional[str]
    pdf_path: Optional[str]
    colaborador_nome: Optional[str] = None
    epi_nome: Optional[str] = None
    model_config = {"from_attributes": True}


# ── MOVIMENTACAO ─────────────────────────────────────────────────────────────
class MovCreate(BaseModel):
    epi_id: str
    quantidade: int
    motivo: str
    documento_nf: Optional[str] = None
    responsavel: Optional[str] = "Sistema"

class MovOut(BaseModel):
    id: str
    data: datetime
    tipo: str
    epi_id: str
    quantidade: int
    motivo: str
    responsavel: str
    model_config = {"from_attributes": True}


class TrocarSenhaRequest(BaseModel):
    senha_atual: str
    nova_senha: str

class ResetAdminRequest(BaseModel):
    reset_key: str
    nova_senha: str = "admin123"


# ── CONFIG ───────────────────────────────────────────────────────────────────
class ConfigUpdate(BaseModel):
    empresa_nome: Optional[str] = None
    empresa_cnpj: Optional[str] = None
    empresa_endereco: Optional[str] = None
    dias_alerta_ca: Optional[int] = None


# ── DASHBOARD ────────────────────────────────────────────────────────────────
class DashboardKPIs(BaseModel):
    total_itens: int
    abaixo_minimo: int
    ca_alertas: int
    colaboradores_7d: int
    alertas: List[str]

class ConsumoSetor(BaseModel):
    setor: str
    quantidade: int

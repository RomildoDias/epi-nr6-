# backend/app/api/routes.py
"""
Todos os endpoints da API em um único arquivo para simplicidade.
"""
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db import models_db, schemas
from app.core.security import (
    get_current_user, require_permission, tenant_filter,
    hash_password, verify_password, create_access_token,
)
from app.core.config import settings
from app.services import rules

router = APIRouter()


# ════════════════════════════════════════════════════════════════════════════
# AUTH
# ════════════════════════════════════════════════════════════════════════════
@router.post("/auth/login", response_model=schemas.TokenResponse)
def login(body: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models_db.Usuario).filter(
        models_db.Usuario.login == body.login.lower().strip(),
        models_db.Usuario.ativo == True,
    ).first()
    if not user or not verify_password(body.senha, user.senha_hash):
        raise HTTPException(status_code=401, detail="Usuário ou senha incorretos")

    token = create_access_token({"sub": user.id})
    tenant_nome = ""
    if user.tenant_id:
        t = db.query(models_db.Tenant).filter(
            models_db.Tenant.id == user.tenant_id).first()
        tenant_nome = t.nome if t else ""

    return schemas.TokenResponse(
        access_token=token, perfil=user.perfil,
        nome=user.nome, tenant_id=user.tenant_id,
        tenant_nome=tenant_nome,
    )


@router.get("/auth/me")
def me(current_user=Depends(get_current_user)):
    return {"id": current_user.id, "nome": current_user.nome,
            "perfil": current_user.perfil, "tenant_id": current_user.tenant_id}


# ════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ════════════════════════════════════════════════════════════════════════════
@router.get("/dashboard/kpis", response_model=schemas.DashboardKPIs)
def dashboard_kpis(db: Session = Depends(get_db),
                   current_user=Depends(require_permission("ver_dashboard"))):
    return rules.get_dashboard_kpis(db, current_user)


@router.get("/dashboard/consumo-setor")
def consumo_setor(dias: int = 30, db: Session = Depends(get_db),
                  current_user=Depends(require_permission("ver_dashboard"))):
    return rules.get_consumo_por_setor(db, current_user, dias)


# ════════════════════════════════════════════════════════════════════════════
# TENANTS
# ════════════════════════════════════════════════════════════════════════════
@router.get("/tenants", response_model=List[schemas.TenantOut])
def list_tenants(db: Session = Depends(get_db),
                 current_user=Depends(require_permission("gerenciar_tenants"))):
    return db.query(models_db.Tenant).all()


@router.post("/tenants", response_model=schemas.TenantOut, status_code=201)
def create_tenant(body: schemas.TenantCreate, db: Session = Depends(get_db),
                  current_user=Depends(require_permission("gerenciar_tenants"))):
    t = models_db.Tenant(id=str(uuid.uuid4()), **body.model_dump())
    db.add(t); db.commit(); db.refresh(t)
    return t


@router.put("/tenants/{tid}", response_model=schemas.TenantOut)
def update_tenant(tid: str, body: schemas.TenantCreate,
                  db: Session = Depends(get_db),
                  current_user=Depends(require_permission("gerenciar_tenants"))):
    t = db.query(models_db.Tenant).filter(models_db.Tenant.id == tid).first()
    if not t: raise HTTPException(404, "Tenant não encontrado")
    for k, v in body.model_dump().items(): setattr(t, k, v)
    db.commit(); db.refresh(t); return t


# ════════════════════════════════════════════════════════════════════════════
# USUÁRIOS
# ════════════════════════════════════════════════════════════════════════════
@router.get("/usuarios", response_model=List[schemas.UsuarioOut])
def list_usuarios(db: Session = Depends(get_db),
                  current_user=Depends(require_permission("gerenciar_usuarios"))):
    q = db.query(models_db.Usuario)
    if current_user.perfil != "superadmin":
        q = q.filter(models_db.Usuario.tenant_id == current_user.tenant_id)
    return q.all()


@router.post("/usuarios", response_model=schemas.UsuarioOut, status_code=201)
def create_usuario(body: schemas.UsuarioCreate, db: Session = Depends(get_db),
                   current_user=Depends(require_permission("gerenciar_usuarios"))):
    if db.query(models_db.Usuario).filter(
            models_db.Usuario.login == body.login.lower()).first():
        raise HTTPException(400, f"Login '{body.login}' já existe")
    u = models_db.Usuario(
        id=str(uuid.uuid4()), nome=body.nome,
        login=body.login.lower(), senha_hash=hash_password(body.senha),
        perfil=body.perfil, tenant_id=body.tenant_id,
    )
    db.add(u); db.commit(); db.refresh(u); return u


@router.put("/usuarios/{uid}", response_model=schemas.UsuarioOut)
def update_usuario(uid: str, body: schemas.UsuarioUpdate,
                   db: Session = Depends(get_db),
                   current_user=Depends(require_permission("gerenciar_usuarios"))):
    u = db.query(models_db.Usuario).filter(models_db.Usuario.id == uid).first()
    if not u: raise HTTPException(404, "Usuário não encontrado")
    if body.nome:       u.nome      = body.nome
    if body.perfil:     u.perfil    = body.perfil
    if body.tenant_id is not None: u.tenant_id = body.tenant_id
    if body.ativo is not None:     u.ativo     = body.ativo
    if body.nova_senha: u.senha_hash = hash_password(body.nova_senha)
    db.commit(); db.refresh(u); return u


# ════════════════════════════════════════════════════════════════════════════
# EPIs
# ════════════════════════════════════════════════════════════════════════════
def _epi_with_status(epi, dias_alerta=30) -> dict:
    d = {c.name: getattr(epi, c.name) for c in epi.__table__.columns}
    d["status"] = rules.get_epi_status(epi, dias_alerta)
    return d


@router.get("/epis")
def list_epis(busca: str = "", db: Session = Depends(get_db),
              current_user=Depends(require_permission("ver_dashboard"))):
    q = db.query(models_db.EPI).filter(models_db.EPI.ativo == True)
    q = tenant_filter(q, models_db.EPI, current_user)
    if busca:
        q = q.filter(
            models_db.EPI.nome.ilike(f"%{busca}%") |
            models_db.EPI.ca.ilike(f"%{busca}%") |
            models_db.EPI.fabricante.ilike(f"%{busca}%")
        )
    return [_epi_with_status(e) for e in q.all()]


@router.post("/epis", status_code=201)
def create_epi(body: schemas.EPICreate, db: Session = Depends(get_db),
               current_user=Depends(require_permission("cadastrar_epi"))):
    epi = models_db.EPI(id=str(uuid.uuid4()),
                         tenant_id=current_user.tenant_id,
                         **body.model_dump())
    db.add(epi); db.commit(); db.refresh(epi)
    _gerar_qrcode(epi.id)
    return _epi_with_status(epi)


@router.put("/epis/{eid}")
def update_epi(eid: str, body: schemas.EPIUpdate, db: Session = Depends(get_db),
               current_user=Depends(require_permission("editar_epi"))):
    epi = db.query(models_db.EPI).filter(models_db.EPI.id == eid).first()
    if not epi: raise HTTPException(404, "EPI não encontrado")
    for k, v in body.model_dump(exclude_none=True).items(): setattr(epi, k, v)
    epi.updated_at = datetime.utcnow()
    db.commit(); db.refresh(epi)
    return _epi_with_status(epi)


@router.delete("/epis/{eid}", status_code=204)
def inativar_epi(eid: str, db: Session = Depends(get_db),
                 current_user=Depends(require_permission("inativar_epi"))):
    epi = db.query(models_db.EPI).filter(models_db.EPI.id == eid).first()
    if not epi: raise HTTPException(404)
    epi.ativo = False; db.commit()


# ════════════════════════════════════════════════════════════════════════════
# COLABORADORES
# ════════════════════════════════════════════════════════════════════════════
@router.get("/colaboradores", response_model=List[schemas.ColaboradorOut])
def list_colaboradores(db: Session = Depends(get_db),
                       current_user=Depends(require_permission("ver_dashboard"))):
    q = db.query(models_db.Colaborador).filter(models_db.Colaborador.ativo == True)
    return tenant_filter(q, models_db.Colaborador, current_user).all()


@router.post("/colaboradores", response_model=schemas.ColaboradorOut, status_code=201)
def create_colaborador(body: schemas.ColaboradorCreate,
                       db: Session = Depends(get_db),
                       current_user=Depends(require_permission("cadastrar_epi"))):
    c = models_db.Colaborador(id=str(uuid.uuid4()),
                                tenant_id=current_user.tenant_id,
                                **body.model_dump())
    db.add(c); db.commit(); db.refresh(c); return c


@router.get("/setores")
def list_setores(db: Session = Depends(get_db),
                 current_user=Depends(require_permission("ver_dashboard"))):
    q = db.query(models_db.Setor)
    return [r.nome for r in tenant_filter(q, models_db.Setor, current_user).all()]


@router.post("/setores", status_code=201)
def create_setor(nome: str, db: Session = Depends(get_db),
                 current_user=Depends(require_permission("cadastrar_epi"))):
    s = models_db.Setor(id=str(uuid.uuid4()),
                         tenant_id=current_user.tenant_id, nome=nome)
    db.add(s); db.commit(); return {"nome": nome}


# ════════════════════════════════════════════════════════════════════════════
# ENTREGAS
# ════════════════════════════════════════════════════════════════════════════
@router.get("/entregas")
def list_entregas(limit: int = 50, db: Session = Depends(get_db),
                  current_user=Depends(require_permission("ver_dashboard"))):
    q = db.query(models_db.Entrega).order_by(models_db.Entrega.data.desc())
    q = tenant_filter(q, models_db.Entrega, current_user)
    result = []
    for e in q.limit(limit).all():
        d = {c.name: getattr(e, c.name) for c in e.__table__.columns}
        d["colaborador_nome"] = e.colaborador.nome if e.colaborador else ""
        d["epi_nome"]         = e.epi.nome         if e.epi         else ""
        result.append(d)
    return result


@router.post("/entregas", status_code=201)
def create_entrega(body: schemas.EntregaCreate,
                   db: Session = Depends(get_db),
                   current_user=Depends(require_permission("registrar_entrega"))):
    entrega, erros = rules.registrar_entrega(
        db, current_user,
        body.colaborador_id, body.epi_id,
        body.quantidade, body.observacao or "",
        body.responsavel or current_user.nome,
    )
    if erros:
        raise HTTPException(400, detail=erros)

    # Gera PDF da ficha
    try:
        pdf_path = _gerar_ficha_pdf(entrega, db, current_user)
        entrega.pdf_path = pdf_path
        db.commit()
    except Exception as e:
        pass  # Entrega salva; PDF é secundário

    return {"id": entrega.id, "pdf_url": f"/api/entregas/{entrega.id}/ficha"}


@router.get("/entregas/{eid}/ficha")
def download_ficha(eid: str, db: Session = Depends(get_db),
                   current_user=Depends(require_permission("ver_relatorios"))):
    entrega = db.query(models_db.Entrega).filter(
        models_db.Entrega.id == eid).first()
    if not entrega: raise HTTPException(404)
    if not entrega.pdf_path or not Path(entrega.pdf_path).exists():
        raise HTTPException(404, "PDF não encontrado")
    return FileResponse(entrega.pdf_path, media_type="application/pdf",
                         filename=f"ficha-{eid[:8]}.pdf")


# ════════════════════════════════════════════════════════════════════════════
# ESTOQUE — ENTRADAS E AJUSTES
# ════════════════════════════════════════════════════════════════════════════
@router.post("/estoque/{epi_id}/entrada")
def entrada_estoque(epi_id: str, body: schemas.MovCreate,
                    db: Session = Depends(get_db),
                    current_user=Depends(require_permission("entrada_estoque"))):
    epi = db.query(models_db.EPI).filter(models_db.EPI.id == epi_id).first()
    if not epi: raise HTTPException(404)
    if body.quantidade <= 0: raise HTTPException(400, "Quantidade deve ser > 0")
    epi.quantidade += body.quantidade
    mov = models_db.Movimentacao(
        id=str(uuid.uuid4()), tenant_id=current_user.tenant_id,
        tipo="entrada", epi_id=epi_id,
        quantidade=body.quantidade, motivo=body.motivo,
        documento_nf=body.documento_nf or "",
        responsavel=body.responsavel or current_user.nome,
    )
    db.add(mov); db.commit()
    return {"quantidade_atual": epi.quantidade}


@router.post("/estoque/{epi_id}/ajuste")
def ajuste_estoque(epi_id: str, body: schemas.MovCreate,
                   db: Session = Depends(get_db),
                   current_user=Depends(require_permission("ajuste_estoque"))):
    epi = db.query(models_db.EPI).filter(models_db.EPI.id == epi_id).first()
    if not epi: raise HTTPException(404)
    nova_qtd = epi.quantidade + body.quantidade
    if nova_qtd < 0: raise HTTPException(400, f"Ajuste resultaria em estoque negativo ({nova_qtd})")
    epi.quantidade = nova_qtd
    mov = models_db.Movimentacao(
        id=str(uuid.uuid4()), tenant_id=current_user.tenant_id,
        tipo="ajuste", epi_id=epi_id,
        quantidade=body.quantidade, motivo=body.motivo,
        responsavel=body.responsavel or current_user.nome,
    )
    db.add(mov); db.commit()
    return {"quantidade_atual": nova_qtd}


@router.get("/estoque/movimentacoes")
def movimentacoes(epi_id: str = None, db: Session = Depends(get_db),
                  current_user=Depends(require_permission("entrada_estoque"))):
    q = db.query(models_db.Movimentacao).order_by(
        models_db.Movimentacao.data.desc())
    q = tenant_filter(q, models_db.Movimentacao, current_user)
    if epi_id: q = q.filter(models_db.Movimentacao.epi_id == epi_id)
    return q.limit(100).all()


# ════════════════════════════════════════════════════════════════════════════
# RELATÓRIOS
# ════════════════════════════════════════════════════════════════════════════
@router.get("/relatorios/estoque")
def relatorio_estoque(db: Session = Depends(get_db),
                      current_user=Depends(require_permission("ver_relatorios"))):
    from app.services.pdf_report import gerar_relatorio_estoque
    config = _get_config_dict(db, current_user.tenant_id)
    import time
    path = str(settings.DATA_DIR / "relatorios" /
               f"estoque_{int(time.time())}.pdf")
    Path(path).parent.mkdir(exist_ok=True)

    # Carrega EPIs filtrados
    q = db.query(models_db.EPI).filter(models_db.EPI.ativo == True)
    q = tenant_filter(q, models_db.EPI, current_user)
    epis = q.all()
    gerar_relatorio_estoque(config, path, epis)
    return FileResponse(path, media_type="application/pdf",
                         filename="estoque.pdf")


@router.get("/relatorios/ca-alertas")
def relatorio_ca(db: Session = Depends(get_db),
                 current_user=Depends(require_permission("ver_relatorios"))):
    from app.services.pdf_report import gerar_relatorio_ca
    config = _get_config_dict(db, current_user.tenant_id)
    import time
    path = str(settings.DATA_DIR / "relatorios" /
               f"ca_{int(time.time())}.pdf")
    Path(path).parent.mkdir(exist_ok=True)
    q = db.query(models_db.EPI).filter(models_db.EPI.ativo == True)
    q = tenant_filter(q, models_db.EPI, current_user)
    epis = q.all()
    gerar_relatorio_ca(config, path, epis)
    return FileResponse(path, media_type="application/pdf", filename="ca_alertas.pdf")


# ════════════════════════════════════════════════════════════════════════════
# CONFIG
# ════════════════════════════════════════════════════════════════════════════
@router.get("/config")
def get_config(db: Session = Depends(get_db),
               current_user=Depends(require_permission("ver_config"))):
    return _get_config_dict(db, current_user.tenant_id)


@router.put("/config")
def set_config(body: dict, db: Session = Depends(get_db),
               current_user=Depends(require_permission("editar_config"))):
    tid = current_user.tenant_id
    for chave, valor in body.items():
        row = db.query(models_db.Config).filter(
            models_db.Config.chave == chave,
            models_db.Config.tenant_id == tid
        ).first()
        if row: row.valor = str(valor)
        else:
            db.add(models_db.Config(id=str(uuid.uuid4()),
                                     tenant_id=tid, chave=chave, valor=str(valor)))
    db.commit()
    return {"ok": True}


# ════════════════════════════════════════════════════════════════════════════
# HELPERS INTERNOS
# ════════════════════════════════════════════════════════════════════════════
def _get_config_dict(db: Session, tenant_id: Optional[str]) -> dict:
    defaults = {
        "dias_alerta_ca": "30",
        "empresa_nome":   "Minha Empresa Ltda",
        "empresa_cnpj":   "00.000.000/0001-00",
        "empresa_endereco":"",
    }
    rows = db.query(models_db.Config).filter(
        models_db.Config.tenant_id.in_([tenant_id, None, ""])
    ).all()
    result = dict(defaults)
    for r in rows:
        result[r.chave] = r.valor
    return result


def _gerar_qrcode(epi_id: str):
    try:
        import qrcode
        settings.QRCODES_DIR.mkdir(parents=True, exist_ok=True)
        qr = qrcode.QRCode(version=1, box_size=6, border=2)
        qr.add_data(epi_id)
        qr.make(fit=True)
        img = qr.make_image()
        img.save(str(settings.QRCODES_DIR / f"epi-{epi_id}.png"))
    except Exception:
        pass


def _gerar_ficha_pdf(entrega: models_db.Entrega, db: Session, current_user) -> str:
    from app.services.pdf_ficha import gerar_ficha_epi
    config  = _get_config_dict(db, current_user.tenant_id)
    colab   = entrega.colaborador
    epi_obj = entrega.epi
    colab_d = {"nome": colab.nome, "matricula": colab.matricula,
               "setor": colab.setor, "funcao": colab.funcao}
    epi_d   = {"id": epi_obj.id, "nome": epi_obj.nome, "ca": epi_obj.ca,
               "tipo_protecao": epi_obj.tipo_protecao,
               "validade_ca": str(epi_obj.validade_ca)}
    ent_d   = {"data": str(entrega.data),
               "validade_prevista": str(entrega.validade_prevista or ""),
               "quantidade": entrega.quantidade,
               "observacao": entrega.observacao or ""}
    qr = str(settings.QRCODES_DIR / f"epi-{epi_obj.id}.png")
    import os
    if not os.path.exists(qr): qr = ""
    settings.FICHAS_DIR.mkdir(parents=True, exist_ok=True)
    return gerar_ficha_epi(
        entrega.id, colab_d, epi_d, ent_d,
        config, settings.FICHAS_DIR, qr
    )

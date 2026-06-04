# app/services/rules.py
from datetime import date, datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db import models_db
from app.core.security import tenant_filter

TIPOS_PROTECAO = [
    "Impacto","Químico","Óptico","Queda","Auditiva",
    "Respiratória","Térmica","Soldagem","Mãos","Pés","Cabeça","Outros"
]

ESTADOS_NORTE_NORDESTE = [
    ("AC","Acre"),("AM","Amazonas"),("AP","Amapá"),("PA","Pará"),
    ("RO","Rondônia"),("RR","Roraima"),("TO","Tocantins"),
    ("AL","Alagoas"),("BA","Bahia"),("CE","Ceará"),("MA","Maranhão"),
    ("PB","Paraíba"),("PE","Pernambuco"),("PI","Piauí"),
    ("RN","Rio Grande do Norte"),("SE","Sergipe"),
]


def get_epi_status(epi: models_db.EPI, dias_alerta: int = 30) -> str:
    today = date.today()
    if epi.validade_ca < today:
        return "CA_VENCIDO"
    if (epi.validade_ca - today).days <= dias_alerta:
        return "CA_ALERTA"
    if epi.quantidade < epi.estoque_minimo:
        return "ABAIXO_MINIMO"
    return "OK"


def get_config_value(db: Session, chave: str, tenant_id: Optional[str],
                     default: str = "") -> str:
    for tid in [tenant_id, None, ""]:
        row = db.query(models_db.Config).filter(
            models_db.Config.chave == chave,
            models_db.Config.tenant_id == tid,
        ).first()
        if row:
            return row.valor
    return default


def get_dashboard_kpis(db: Session, current_user, _tenant: str = '') -> dict:
    dias_alerta = int(get_config_value(
        db, "dias_alerta_ca", current_user.tenant_id, "30"))

    q_epis = db.query(models_db.EPI).filter(models_db.EPI.ativo == True)
    q_epis = tenant_filter(q_epis, models_db.EPI, current_user, _tenant=_tenant)
    epis   = q_epis.all()

    total_itens   = sum(e.quantidade for e in epis)
    abaixo_minimo = 0
    ca_alertas    = 0
    alertas       = []

    for epi in epis:
        status = get_epi_status(epi, dias_alerta)
        if status == "CA_VENCIDO":
            ca_alertas += 1
            alertas.append(f"CA VENCIDO: {epi.nome} (CA: {epi.ca}, Validade: {epi.validade_ca})")
        elif status == "CA_ALERTA":
            ca_alertas += 1
            dias_rest = (epi.validade_ca - date.today()).days
            alertas.append(f"CA vence em {dias_rest} dias: {epi.nome} (CA: {epi.ca})")
        elif status == "ABAIXO_MINIMO":
            abaixo_minimo += 1
            alertas.append(f"Estoque baixo: {epi.nome} (Qtd: {epi.quantidade}, Mín: {epi.estoque_minimo})")

    cutoff   = datetime.utcnow() - timedelta(days=7)
    q_colab  = db.query(models_db.Entrega.colaborador_id).filter(
        models_db.Entrega.data >= cutoff)
    q_colab  = tenant_filter(q_colab, models_db.Entrega, current_user, _tenant=_tenant)
    colab_7d = q_colab.distinct().count()

    return {
        "total_itens":      total_itens,
        "abaixo_minimo":    abaixo_minimo,
        "ca_alertas":       ca_alertas,
        "colaboradores_7d": colab_7d,
        "alertas":          alertas,
    }


def get_consumo_por_setor(db: Session, current_user, dias: int = 30, _tenant: str = '') -> list:
    cutoff = datetime.utcnow() - timedelta(days=dias)

    result = db.query(
        models_db.Colaborador.setor,
        func.sum(models_db.Entrega.quantidade).label("total")
    ).join(
        models_db.Entrega,
        models_db.Entrega.colaborador_id == models_db.Colaborador.id
    ).filter(models_db.Entrega.data >= cutoff)

    result = tenant_filter(result, models_db.Entrega, current_user, _tenant=_tenant)

    return [
        {"setor": r.setor, "quantidade": int(r.total)}
        for r in result.group_by(models_db.Colaborador.setor)
                       .order_by(func.sum(models_db.Entrega.quantidade).desc())
                       .all()
    ]


def registrar_entrega(db: Session, current_user,
                      colaborador_id: str, epi_id: str,
                      quantidade: int, observacao: str,
                      responsavel: str,
                      tenant_id: str = None) -> tuple:
    import uuid

    if quantidade <= 0:
        return None, ["Quantidade deve ser maior que zero."]

    tid = tenant_id or current_user.tenant_id
    epi = db.query(models_db.EPI).filter(
        models_db.EPI.id == epi_id,
        models_db.EPI.ativo == True,
        models_db.EPI.tenant_id == tid,
    ).first()
    if not epi:
        return None, ["EPI não encontrado ou inativo neste estado."]

    colab = db.query(models_db.Colaborador).filter(
        models_db.Colaborador.id == colaborador_id,
        models_db.Colaborador.ativo == True,
        models_db.Colaborador.tenant_id == tid,
    ).first()
    if not colab:
        return None, ["Colaborador não encontrado ou inativo neste estado."]

    erros = []
    if epi.validade_ca < date.today():
        erros.append(f"CA do EPI '{epi.nome}' está vencido. Entrega bloqueada pela NR-6.")
    if quantidade > epi.quantidade:
        erros.append(f"Saldo insuficiente. Disponível: {epi.quantidade}, solicitado: {quantidade}.")
    if erros:
        return None, erros

    validade_prev = (
        date.today() + timedelta(days=epi.vida_util_dias)
        if epi.vida_util_dias > 0 else None
    )

    entrega = models_db.Entrega(
        id                = str(uuid.uuid4()),
        tenant_id         = tid,
        colaborador_id    = colaborador_id,
        epi_id            = epi_id,
        quantidade        = quantidade,
        validade_prevista = validade_prev,
        observacao        = observacao,
    )
    db.add(entrega)

    mov = models_db.Movimentacao(
        id          = str(uuid.uuid4()),
        tenant_id   = tid,
        tipo        = "saida",
        epi_id      = epi_id,
        quantidade  = -quantidade,
        motivo      = f"Entrega para: {colab.nome} ({colab.matricula})",
        responsavel = responsavel,
    )
    db.add(mov)

    epi.quantidade -= quantidade
    db.commit()
    db.refresh(entrega)
    return entrega, []

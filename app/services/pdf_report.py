# backend/app/services/pdf_report.py
from datetime import datetime
from pathlib import Path
from app.services.rules import get_epi_status

_COL_WEIGHTS = {
    "EPI":4.0,"Fabricante":3.0,"Tipo":2.0,"CA":1.0,"Qtd":0.7,
    "Mín":0.7,"Validade CA":1.5,"Status":1.8,"Colaborador":3.0,
    "Matrícula":1.2,"Setor":2.0,"Data":1.8,"Val. Prevista":1.5,
}


def _available():
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    return A4[0] - 4*cm


def _col_widths(cols):
    w = [_COL_WEIGHTS.get(c, 2.0) for c in cols]
    t = sum(w); av = _available()
    return [av * (x/t) for x in w]


def _header(config, title, period=""):
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER
    from reportlab.platypus import Paragraph, HRFlowable, Spacer
    styles = getSampleStyleSheet()
    s9c = ParagraphStyle("s9c", parent=styles["Normal"], fontSize=9, alignment=TA_CENTER)
    s9b = ParagraphStyle("s9b", parent=styles["Normal"], fontSize=9, fontName="Helvetica-Bold")
    empresa = config.get("empresa_nome","Empresa")
    cnpj    = config.get("empresa_cnpj","")
    elems = [
        Paragraph(f"<b>{empresa}</b> | CNPJ: {cnpj}", s9c),
        Paragraph(f"<b>{title}</b>", s9b),
    ]
    if period: elems.append(Paragraph(f"Período: {period}", s9c))
    elems.append(Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", s9c))
    elems.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#2c3e50")))
    elems.append(Spacer(1, .3*cm))
    return elems


def _make_table(rows, cols):
    from reportlab.lib import colors
    from reportlab.platypus import Table, TableStyle, Paragraph
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    styles = getSampleStyleSheet()
    cell_s = ParagraphStyle("c", parent=styles["Normal"], fontSize=7, leading=9)
    hdr_s  = ParagraphStyle("h", parent=styles["Normal"], fontSize=7, leading=9,
                              fontName="Helvetica-Bold", textColor=colors.white)
    widths = _col_widths(cols)
    data = [[Paragraph(c, hdr_s) for c in cols]]
    for row in rows:
        data.append([Paragraph(str(v) if v else "", cell_s) for v in row])
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),  colors.HexColor("#2c3e50")),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#f4f6f8")]),
        ("GRID",(0,0),(-1,-1),.3,colors.HexColor("#d1d5db")),
        ("LINEBELOW",(0,0),(-1,0),.8,colors.HexColor("#2c3e50")),
        ("VALIGN",(0,0),(-1,-1),"TOP"),
        ("TOPPADDING",(0,0),(-1,-1),4),
        ("BOTTOMPADDING",(0,0),(-1,-1),4),
        ("LEFTPADDING",(0,0),(-1,-1),5),
    ]))
    return t


def _build_doc(path, elems):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate
    doc = SimpleDocTemplate(path, pagesize=A4,
                             leftMargin=2*cm, rightMargin=2*cm,
                             topMargin=2*cm, bottomMargin=2*cm)
    doc.build(elems)


def gerar_relatorio_estoque(config, path, epis, dias_alerta=30):
    from reportlab.platypus import Paragraph, Spacer
    from reportlab.lib.units import cm
    from reportlab.lib.styles import getSampleStyleSheet
    s = getSampleStyleSheet()["Normal"]
    s.fontSize = 8
    elems = _header(config, "RELATÓRIO DE ESTOQUE ATUAL")
    if not epis:
        elems.append(Paragraph("Nenhum EPI cadastrado.", s)); _build_doc(path, elems); return

    cols = ["EPI","CA","Fabricante","Tipo","Qtd","Mín","Validade CA","Status"]
    rows = []
    for e in epis:
        rows.append([
            e.nome, e.ca, e.fabricante, e.tipo_protecao,
            str(e.quantidade), str(e.estoque_minimo),
            e.validade_ca.strftime("%d/%m/%Y") if e.validade_ca else "",
            get_epi_status(e, dias_alerta),
        ])
    elems.append(_make_table(rows, cols))
    elems.append(Spacer(1,.3*cm))
    elems.append(Paragraph(f"Total: {sum(e.quantidade for e in epis)} unidades", s))
    _build_doc(path, elems)


def gerar_relatorio_ca(config, path, epis, dias_alerta=30):
    from reportlab.platypus import Paragraph, Spacer
    from reportlab.lib.units import cm
    from reportlab.lib.styles import getSampleStyleSheet
    s = getSampleStyleSheet()["Normal"]; s.fontSize = 8
    elems = _header(config, "RELATÓRIO DE CA VENCIDO / A VENCER")
    alertas = [e for e in epis if get_epi_status(e, dias_alerta) in ("CA_VENCIDO","CA_ALERTA")]
    if not alertas:
        elems.append(Paragraph("Nenhum alerta de CA.", s)); _build_doc(path, elems); return
    cols = ["EPI","CA","Fabricante","Validade CA","Qtd","Status"]
    rows = [[e.nome, e.ca, e.fabricante,
             e.validade_ca.strftime("%d/%m/%Y") if e.validade_ca else "",
             str(e.quantidade), get_epi_status(e, dias_alerta)]
            for e in alertas]
    elems.append(_make_table(rows, cols))
    elems.append(Spacer(1,.3*cm))
    elems.append(Paragraph(f"Total: {len(alertas)} EPI(s) com atenção.", s))
    _build_doc(path, elems)


def gerar_relatorio_entregas_pdf(config, path, entregas, dias_alerta=30):
    from reportlab.platypus import Paragraph, Spacer
    from reportlab.lib.units import cm
    from reportlab.lib.styles import getSampleStyleSheet
    s = getSampleStyleSheet()["Normal"]; s.fontSize = 8
    elems = _header(config, "RELATÓRIO DE ENTREGAS")
    if not entregas:
        elems.append(Paragraph("Nenhuma entrega no período.", s))
        _build_doc(path, elems); return
    cols = ["Data","Colaborador","EPI","Qtd","Val. Prevista","Responsável"]
    rows = []
    for e in entregas:
        colab_nome = e.colaborador.nome if e.colaborador else "—"
        epi_nome   = e.epi.nome         if e.epi         else "—"
        resp       = getattr(e, "responsavel", "") or "—"
        val_prev   = e.validade_prevista.strftime("%d/%m/%Y") if e.validade_prevista else "—"
        rows.append([
            e.data.strftime("%d/%m/%Y %H:%M") if e.data else "—",
            colab_nome, epi_nome, str(e.quantidade), val_prev, resp,
        ])
    elems.append(_make_table(rows, cols))
    elems.append(Spacer(1,.3*cm))
    from reportlab.lib.styles import getSampleStyleSheet
    ns = getSampleStyleSheet()["Normal"]; ns.fontSize = 8
    elems.append(Paragraph(f"Total de entregas: {len(entregas)}", ns))
    _build_doc(path, elems)

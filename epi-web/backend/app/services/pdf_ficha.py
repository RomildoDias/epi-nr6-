# backend/app/services/pdf_ficha.py
# Reaproveitado do app desktop — gera Ficha de Entrega NR-6
import os
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

TERMO_NR6 = (
    "Declaro ter recebido o(s) Equipamento(s) de Proteção Individual (EPI) acima relacionado(s), "
    "estando ciente da obrigatoriedade do uso conforme a NR-6 da Portaria MTE nº 3.214/78 e suas "
    "atualizações, responsabilizando-me pela sua guarda e conservação, comprometendo-me a utilizá-lo(s) "
    "sempre que necessário, a comunicar qualquer dano ou extravio e a devolvê-lo(s) quando solicitado."
)


def format_date(val) -> str:
    if not val or str(val).strip() in ("", "nan", "NaT", "None"): return ""
    try:
        from datetime import datetime as dt
        d = dt.fromisoformat(str(val).split("T")[0])
        return d.strftime("%d/%m/%Y")
    except Exception:
        return str(val)


def gerar_ficha_epi(entrega_id: str, colaborador: dict, epi: dict,
                    entrega: dict, config: dict, fichas_dir: Path,
                    qr_path: str = "") -> str:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                     Table, TableStyle, HRFlowable, Image)

    fichas_dir = Path(fichas_dir)
    fichas_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = fichas_dir / f"ficha-{entrega_id}.pdf"

    doc = SimpleDocTemplate(str(pdf_path), pagesize=A4,
                             leftMargin=2*cm, rightMargin=2*cm,
                             topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    s_title   = ParagraphStyle("t",  parent=styles["Heading1"],  fontSize=13, alignment=TA_CENTER)
    s_sub     = ParagraphStyle("s",  parent=styles["Normal"],    fontSize=9,  alignment=TA_CENTER)
    s_bold    = ParagraphStyle("b",  parent=styles["Normal"],    fontSize=9,  fontName="Helvetica-Bold")
    s_just    = ParagraphStyle("j",  parent=styles["Normal"],    fontSize=8,  alignment=TA_JUSTIFY, leading=12)
    s_small   = ParagraphStyle("sm", parent=styles["Normal"],    fontSize=7,  alignment=TA_CENTER)

    empresa  = config.get("empresa_nome","Empresa")
    cnpj     = config.get("empresa_cnpj","")
    elements = [
        Paragraph(f"<b>{empresa}</b> | CNPJ: {cnpj}", s_sub),
        HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2c3e50")),
        Spacer(1,.2*cm),
        Paragraph("FICHA DE ENTREGA DE EPI – NR-6", s_title),
        HRFlowable(width="100%", thickness=0.5, color=colors.grey),
        Spacer(1,.3*cm),
        Paragraph("1. DADOS DO COLABORADOR", s_bold),
    ]

    def table2(data, widths):
        t = Table(data, colWidths=widths)
        t.setStyle(TableStyle([
            ("FONTNAME",(0,0),(0,-1),"Helvetica-Bold"),
            ("FONTNAME",(2,0),(2,-1),"Helvetica-Bold"),
            ("FONTSIZE",(0,0),(-1,-1),9),
            ("GRID",(0,0),(-1,-1),.3,colors.grey),
            ("BACKGROUND",(0,0),(0,-1),colors.HexColor("#ecf0f1")),
            ("BACKGROUND",(2,0),(2,-1),colors.HexColor("#ecf0f1")),
            ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
            ("TOPPADDING",(0,0),(-1,-1),4),
            ("BOTTOMPADDING",(0,0),(-1,-1),4),
        ]))
        return t

    elements.append(table2([
        ["Nome:",   colaborador.get("nome",""), "Matrícula:", colaborador.get("matricula","")],
        ["Setor:",  colaborador.get("setor",""),"Função:",    colaborador.get("funcao","")],
    ], [2.5*cm, 6*cm, 2.5*cm, 6*cm]))

    elements += [Spacer(1,.3*cm), Paragraph("2. DADOS DO EPI", s_bold)]
    elements.append(table2([
        ["EPI:",           epi.get("nome",""),          "CA Nº:",         epi.get("ca","")],
        ["Tipo Proteção:", epi.get("tipo_protecao",""), "Validade CA:",    format_date(epi.get("validade_ca",""))],
        ["Quantidade:",    str(entrega.get("quantidade","")), "Data Entrega:", format_date(entrega.get("data",""))],
        ["Val. Prevista:", format_date(entrega.get("validade_prevista","")), "ID EPI:", str(epi.get("id",""))[:20]],
    ], [3*cm, 6*cm, 3*cm, 5*cm]))

    if qr_path and os.path.exists(qr_path):
        try:
            qr_img = Image(qr_path, width=2.5*cm, height=2.5*cm)
            elements.append(Table([[Paragraph("QR Code do EPI:", s_small), qr_img]],
                                   colWidths=[14*cm, 3*cm]))
        except Exception: pass

    elements += [
        Spacer(1,.3*cm),
        Paragraph("3. TERMO DE RESPONSABILIDADE – NR-6", s_bold),
        Paragraph(TERMO_NR6, s_just),
        Spacer(1,.5*cm),
        Paragraph("4. ASSINATURAS", s_bold),
        Paragraph(f"Local e Data: ____________________, {datetime.now().strftime('%d/%m/%Y')}", s_sub),
        Spacer(1,1.2*cm),
    ]

    ass = Table([
        ["_"*40, "   ", "_"*40],
        [Paragraph(f"<b>{colaborador.get('nome','')}</b><br/>Colaborador", s_small),
         "",
         Paragraph("<b>Responsável pela Entrega</b>", s_small)],
    ], colWidths=[8*cm, 1*cm, 8*cm])
    ass.setStyle(TableStyle([("ALIGN",(0,0),(-1,-1),"CENTER"),("TOPPADDING",(0,1),(-1,1),2)]))
    elements.append(ass)
    elements += [
        Spacer(1,.4*cm),
        HRFlowable(width="100%", thickness=.5, color=colors.grey),
        Paragraph(f"Entrega ID: {entrega_id} | Gerado: {datetime.now().strftime('%d/%m/%Y %H:%M')}", s_small),
    ]
    doc.build(elements)
    return str(pdf_path)

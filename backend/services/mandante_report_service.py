"""Report PDF riepilogativo delle provvigioni per un singolo mandante, su
un intervallo di date — pensato per essere mandato al mandante stesso
("ecco gli ordini/provvigioni di questo trimestre"). Costruito interamente
in memoria con reportlab (nessuna libreria di sistema richiesta, a
differenza di alternative come weasyprint — scelta pensata per restare
sicura su Railway/Railpack senza configurazione aggiuntiva), stesso
principio di services/attendance_xlsx_export.py (build) +
export_service.pdf_response (risposta).

IMPORTANTE — non è un documento fiscale: è un riepilogo informativo. Vedi
il disclaimer nel footer, coerente con la decisione di non costruire
fatturazione nativa (rischio di compliance sproporzionato per un CRM,
non un gestionale fiscale)."""

import io
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from core.utils import local_date_str
from services.fiscal_calc import compute_fiscal_breakdown


def _format_euro(n: float) -> str:
    """Formato italiano (punto migliaia, virgola decimali) senza dipendere
    dal modulo locale — instabile tra ambienti (locale di sistema diverso
    tra sviluppo locale e container Railway) per un'unica stringa formattata
    su due punti di codice."""
    s = f"{n:,.2f}"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{s} €"


def build_mandante_report_pdf(
    user: dict,
    mandante: dict,
    commissions: list,
    clients: dict,
    date_from: str,
    date_to: str,
) -> bytes:
    """clients: dict {client_id: client_doc}, stesso pattern di join già
    usato in export_service.export_commissions. commissions: lista già
    filtrata per mandante_id e per data (vedi
    ExportService.export_mandante_report)."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        title=f"Report provvigioni — {mandante.get('name', '')}",
    )
    styles = getSampleStyleSheet()
    small = ParagraphStyle(
        "small", parent=styles["Normal"], fontSize=9, textColor=colors.grey
    )
    footer_style = ParagraphStyle(
        "footer", parent=styles["Normal"], fontSize=8, textColor=colors.grey
    )

    story = []

    # --- Intestazione: chi manda il report e a chi si riferisce ---
    story.append(
        Paragraph(f"Report provvigioni — {mandante.get('name', '')}", styles["Title"])
    )
    story.append(Paragraph(f"Periodo: {date_from} — {date_to}", styles["Normal"]))
    story.append(Spacer(1, 4 * mm))

    sender_lines = [user.get("name") or user.get("email", "")]
    vat_number: Optional[str] = user.get("company_vat_number")
    if vat_number:
        sender_lines.append(f"Partita IVA: {vat_number}")
    story.append(Paragraph("<br/>".join(sender_lines), small))
    story.append(Spacer(1, 8 * mm))

    # --- Riepilogo fiscale, stessa formula di Commissions.jsx "Netto stimato" ---
    lordo_totale = sum(c.get("amount", 0) for c in commissions)
    regime_fiscale = user.get("regime_fiscale", "ordinario")
    base_ritenuta = user.get("base_ritenuta", "50")
    breakdown = compute_fiscal_breakdown(lordo_totale, regime_fiscale, base_ritenuta)

    summary_data = [
        ["Provvigioni lorde", _format_euro(breakdown["lordo"])],
        ["Ritenuta d'acconto", _format_euro(breakdown["ritenuta_acconto"])],
        ["Contributo ENASARCO", _format_euro(breakdown["contributo_enasarco"])],
        ["Netto stimato", _format_euro(breakdown["netto"])],
    ]
    summary_table = Table(summary_data, colWidths=[70 * mm, 40 * mm])
    summary_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("LINEABOVE", (0, -1), (-1, -1), 0.5, colors.grey),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(summary_table)
    story.append(Spacer(1, 8 * mm))

    # --- Dettaglio, una riga per provvigione ---
    if commissions:
        rows = [["Data", "Cliente", "Importo", "Aliquota", "Origine"]]
        for c in sorted(commissions, key=lambda c: c.get("created_at", "")):
            client_name = clients.get(c.get("client_id"), {}).get("company_name", "—")
            rate = c.get("rate")
            rows.append(
                [
                    local_date_str(c.get("created_at")) or "—",
                    client_name,
                    _format_euro(c.get("amount", 0)),
                    f"{rate:.2f}%" if rate is not None else "—",
                    "Manuale" if c.get("source") == "manual" else "Ordine",
                ]
            )
        detail_table = Table(
            rows, colWidths=[22 * mm, 60 * mm, 30 * mm, 22 * mm, 25 * mm], repeatRows=1
        )
        detail_table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0A192F")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("ALIGN", (2, 0), (3, -1), "RIGHT"),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, colors.HexColor("#F5F5F4")],
                    ),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.grey),
                ]
            )
        )
        story.append(detail_table)
    else:
        story.append(
            Paragraph("Nessuna provvigione nel periodo selezionato.", styles["Normal"])
        )

    story.append(Spacer(1, 12 * mm))
    story.append(
        Paragraph(
            "Documento riepilogativo generato da SalesFly — non sostituisce fattura "
            "o altro documento fiscale.",
            footer_style,
        )
    )

    doc.build(story)
    return buf.getvalue()

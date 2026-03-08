"""VAT export: PDF format."""

from __future__ import annotations

import os
from datetime import datetime
from decimal import Decimal
from typing import Dict

from app.vat_reports.schemas.vat_client_summary_schema import VatPeriodRow


def _fmt(amount: Decimal | None) -> str:
    if amount is None:
        return "—"
    return f"{amount:.2f}"


def export_vat_to_pdf(
    client_name: str,
    client_id: int,
    year: int,
    periods: list[VatPeriodRow],
    export_dir: str,
) -> Dict[str, object]:
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError:
        raise ImportError("הספרייה reportlab נדרשת. יש להתקין באמצעות: pip install reportlab")

    filename = f"vat_{client_id}_{year}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    filepath = os.path.join(export_dir, filename)

    doc = SimpleDocTemplate(filepath, pagesize=landscape(A4))
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph(f"<b>{client_name} — מע״מ {year}</b>", styles["Title"]))
    elements.append(Spacer(1, 0.4 * cm))

    table_data = [["תקופה", "סטטוס", "עסקאות", "תשומות", "נטו", "סופי", "הוגש"]]
    totals = {"output": Decimal(0), "input": Decimal(0), "net": Decimal(0)}

    for p in periods:
        status_str = p.status.value if hasattr(p.status, "value") else str(p.status)
        filed = p.filed_at.strftime("%d/%m/%Y") if p.filed_at else "—"
        final = _fmt(p.final_vat_amount)
        table_data.append([
            p.period, status_str,
            _fmt(p.total_output_vat), _fmt(p.total_input_vat),
            _fmt(p.net_vat), final, filed,
        ])
        totals["output"] += p.total_output_vat
        totals["input"] += p.total_input_vat
        totals["net"] += p.net_vat

    table_data.append([
        "סה״כ", "",
        _fmt(totals["output"]), _fmt(totals["input"]),
        _fmt(totals["net"]), "", "",
    ])

    table = Table(table_data)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#366092")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 11),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
        ("BACKGROUND", (0, -1), (-1, -1), colors.lightgrey),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 0.5 * cm))
    elements.append(Paragraph(
        f"נוצר: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        styles["Normal"],
    ))

    doc.build(elements)
    return {"filepath": filepath, "filename": filename, "format": "pdf", "generated_at": datetime.now()}

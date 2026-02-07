from __future__ import annotations

from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from db.models import Client, Product, Quote
from db.session import get_session
from sqlalchemy.orm import selectinload
from paths import get_portable_dir, get_base_dir
from settings import Settings
from ui.i18n import t


def export_quote_pdf(path: Path, quote_id: int, include_costs: bool = False) -> Path:
    exports_dir = get_portable_dir("exports")
    if path.is_dir():
        path = exports_dir / f"presupuesto_{quote_id}.pdf"
    elif not path.is_absolute():
        path = exports_dir / path

    with get_session() as session:
        quote = (
            session.query(Quote)
            .options(selectinload(Quote.lines))
            .filter(Quote.id == quote_id)
            .first()
        )
        if quote is None:
            raise ValueError(t("quote_not_found"))
        client = session.get(Client, quote.client_id)
        lines = list(quote.lines)

    settings = Settings.load()
    company = settings.data

    doc = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "QuoteTitle",
        parent=styles["Title"],
        alignment=1,
        spaceAfter=6,
    )
    story = []

    # Header: logo + company data
    logo_path = company.get("logo_path")
    logo_file = None
    if logo_path:
        candidate = Path(logo_path)
        if candidate.exists():
            logo_file = candidate
    if logo_file is None:
        default_logo = get_base_dir() / "assets" / "logo_orzalan.png"
        if default_logo.exists():
            logo_file = default_logo

    logo_cell = ""
    if logo_file is not None:
        logo_cell = Image(str(logo_file), width=40 * mm, height=20 * mm)

    company_lines = [
        company.get("company_name", ""),
        company.get("company_tax_id", ""),
        company.get("company_address", ""),
        company.get("company_phone", ""),
        company.get("company_email", ""),
        company.get("company_web", ""),
    ]
    company_text = "<br/>".join([line for line in company_lines if line])
    company_cell = Paragraph(company_text, styles["Normal"]) if company_text else ""

    header_table = Table(
        [[logo_cell, company_cell]],
        colWidths=[50 * mm, 130 * mm],
        hAlign="LEFT",
    )
    header_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOX", (1, 0), (1, 0), 0.25, colors.grey),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    story.append(header_table)
    story.append(Spacer(1, 4 * mm))

    # Title row
    story.append(Paragraph(f"<b>{t('quote').upper()}</b>", title_style))
    story.append(Spacer(1, 4 * mm))

    # Quote info + client box
    info_lines = [
        f"{t('number')}: {quote.number}",
        f"{t('date')}: {quote.date}",
        f"{t('status')}: {_display_status(quote.status)}",
        f"{t('valid_days')}: {quote.valid_days}",
    ]
    info_text = "<br/>".join([line for line in info_lines if line])
    info_cell = Paragraph(info_text, styles["Normal"])

    client_lines = [
        client.name if client else "",
        client.tax_id if client else "",
        client.address if client else "",
        client.phone if client else "",
        client.email if client else "",
    ]
    client_text = "<br/>".join([line for line in client_lines if line])
    client_box = Paragraph(f"<b>{t('client').upper()}</b><br/>{client_text}", styles["Normal"])

    info_table = Table(
        [[info_cell, client_box]],
        colWidths=[100 * mm, 80 * mm],
        hAlign="LEFT",
    )
    info_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOX", (1, 0), (1, 0), 0.25, colors.grey),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(info_table)
    story.append(Spacer(1, 6 * mm))

    data = [
        [
            t("ref"),
            t("description"),
            t("unit"),
            t("quantity"),
            t("sale_price"),
            t("subtotal"),
            f"{t('vat')} %",
            t("total"),
        ]
    ]
    for line in lines:
        data.append(
            [
                line.ref_snapshot,
                line.desc_snapshot,
                line.unit_snapshot,
                f"{line.qty:.2f}",
                f"{line.unit_price_snapshot:.2f}",
                f"{line.line_subtotal:.2f}",
                f"{line.vat:.2f}%",
                f"{line.line_total:.2f}",
            ]
        )

    table = Table(data, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (3, 1), (-1, -1), "RIGHT"),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 6 * mm))

    totals = [
        [t("subtotal"), f"{quote.subtotal:.2f}"],
        [f"{t('vat')} %", f"{float(quote.global_vat or 0):.2f}%"],
        [t("vat"), f"{quote.vat_total:.2f}"],
        [t("total"), f"{quote.total:.2f}"],
    ]
    totals_table = Table(totals, colWidths=[60 * mm, 30 * mm], hAlign="RIGHT")
    totals_table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("BACKGROUND", (0, -1), (-1, -1), colors.whitesmoke),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ]
        )
    )
    story.append(totals_table)
    story.append(Spacer(1, 6 * mm))

    conditions = company.get("conditions") or company.get("notes") or ""
    if conditions:
        story.append(Paragraph(f"<b>{t('conditions')}</b><br/>{conditions}", styles["Normal"]))

    if include_costs and settings.get("mostrar_costes", False):
        story.append(Spacer(1, 8 * mm))
        story.append(Paragraph(f"<b>{t('internal_annex')}</b>", styles["Heading3"]))
        internal = [[t("ref"), t("description"), t("cost"), t("margin")]]
        with get_session() as session:
            for line in lines:
                cost = ""
                margin = ""
                if line.product_id:
                    product = session.get(Product, line.product_id)
                    if product:
                        cost = f"{float(product.cost or 0):.2f}"
                        margin = f"{float(product.margin or 0) * 100:.2f}"
                internal.append([line.ref_snapshot, line.desc_snapshot, cost, margin])
        internal_table = Table(internal, hAlign="LEFT")
        internal_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ]
            )
        )
        story.append(internal_table)

    doc.build(story, onFirstPage=_watermark_if_draft(quote), onLaterPages=_watermark_if_draft(quote))
    return path


def _watermark_if_draft(quote: Quote):
    def _apply(canvas_: canvas.Canvas, _doc) -> None:
        status = (quote.status or "").upper()
        if status not in {t("draft").upper(), "BORRADOR", "DRAFT"}:
            return
        canvas_.saveState()
        canvas_.setFont("Helvetica-Bold", 72)
        canvas_.setFillColorRGB(0.8, 0.8, 0.8)
        canvas_.translate(300, 400)
        canvas_.rotate(45)
        canvas_.drawCentredString(0, 0, t("draft").upper())
        canvas_.restoreState()

    return _apply


def _display_status(status: str | None) -> str:
    if not status:
        return ""
    lower = status.lower()
    map_en_to_local = {
        "draft": t("draft"),
        "borrador": t("draft"),
        "sent": t("sent"),
        "enviado": t("sent"),
        "accepted": t("accepted"),
        "aceptado": t("accepted"),
        "rejected": t("rejected"),
        "rechazado": t("rejected"),
    }
    return map_en_to_local.get(lower, status)

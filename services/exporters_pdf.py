from __future__ import annotations

from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    Image,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

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

    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "QuoteTitle",
        parent=styles["Title"],
        alignment=1,
        spaceAfter=6,
    )
    small_style = ParagraphStyle("Small", parent=styles["Normal"], fontSize=8.5, leading=10)
    tiny_style = ParagraphStyle("Tiny", parent=styles["Normal"], fontSize=8, leading=9.5)
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
    company_cell = Paragraph(company_text, small_style) if company_text else ""
    usable_width = doc.width

    header_table = Table(
        [[logo_cell, company_cell]],
        colWidths=[46 * mm, usable_width - (46 * mm)],
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
    info_cell = Paragraph(info_text, small_style)

    client_lines = [
        client.name if client else "",
        client.tax_id if client else "",
        client.address if client else "",
        client.phone if client else "",
        client.email if client else "",
    ]
    client_text = "<br/>".join([line for line in client_lines if line])
    client_box = Paragraph(f"<b>{t('client').upper()}</b><br/>{client_text}", small_style)

    info_table = Table(
        [[info_cell, client_box]],
        colWidths=[usable_width * 0.56, usable_width * 0.44],
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
                Paragraph(str(line.ref_snapshot or ""), tiny_style),
                Paragraph(str(line.desc_snapshot or ""), tiny_style),
                Paragraph(str(line.unit_snapshot or ""), tiny_style),
                f"{line.qty:.2f}",
                f"{line.unit_price_snapshot:.2f}",
                f"{line.line_subtotal:.2f}",
                f"{line.vat:.2f}%",
                f"{line.line_total:.2f}",
            ]
        )

    line_col_widths = [
        usable_width * 0.11,  # ref
        usable_width * 0.37,  # description
        usable_width * 0.07,  # unit
        usable_width * 0.08,  # qty
        usable_width * 0.11,  # unit price
        usable_width * 0.11,  # subtotal
        usable_width * 0.07,  # vat %
        usable_width * 0.08,  # total
    ]
    table = Table(data, colWidths=line_col_widths, hAlign="LEFT", repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (3, 1), (-1, -1), "RIGHT"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("LEADING", (0, 0), (-1, -1), 9.5),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
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
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ]
        )
    )
    footer_blocks = [totals_table, Spacer(1, 5 * mm)]

    conditions = company.get("conditions") or company.get("notes") or ""
    if conditions:
        footer_blocks.append(Paragraph(f"<b>{t('conditions')}</b><br/>{conditions}", small_style))
        footer_blocks.append(Spacer(1, 5 * mm))

    signatures_table = Table(
        [[
            Paragraph("<b>Conforme empresa</b><br/><br/><br/>", small_style),
            Paragraph("<b>Conforme cliente</b><br/><br/><br/>", small_style),
        ]],
        colWidths=[usable_width * 0.48, usable_width * 0.48],
        hAlign="CENTER",
    )
    signatures_table.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (0, 0), 0.5, colors.grey),
                ("BOX", (1, 0), (1, 0), 0.5, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
            ]
        )
    )
    footer_blocks.append(signatures_table)

    story.append(KeepTogether(footer_blocks))

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
        internal_table = Table(internal, hAlign="LEFT", colWidths=[usable_width * 0.15, usable_width * 0.55, usable_width * 0.15, usable_width * 0.15], repeatRows=1)
        internal_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                ]
            )
        )
        story.append(internal_table)

    page_decorator = _page_decorator(quote)
    doc.build(story, onFirstPage=page_decorator, onLaterPages=page_decorator)
    return path


def _page_decorator(quote: Quote):
    def _apply(canvas_: canvas.Canvas, doc) -> None:
        status = (quote.status or "").upper()
        if status not in {t("draft").upper(), "BORRADOR", "DRAFT"}:
            pass
        else:
            canvas_.saveState()
            canvas_.setFont("Helvetica-Bold", 72)
            canvas_.setFillColorRGB(0.8, 0.8, 0.8)
            canvas_.translate(300, 400)
            canvas_.rotate(45)
            canvas_.drawCentredString(0, 0, t("draft").upper())
            canvas_.restoreState()

        canvas_.saveState()
        canvas_.setFont("Helvetica", 8)
        canvas_.setFillColor(colors.grey)
        canvas_.drawRightString(doc.pagesize[0] - doc.rightMargin, 8 * mm, f"Página {canvas_.getPageNumber()}")
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

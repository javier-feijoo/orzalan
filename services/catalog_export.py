from __future__ import annotations

import csv
from pathlib import Path

from openpyxl import Workbook

from db.models import Product
from db.session import get_session
from paths import get_portable_dir

HEADERS = [
    "Referencia",
    "Código categoría",
    "Categoría",
    "Nombre",
    "Descripción",
    "Unidad",
    "Precio coste",
    "Beneficio",
    "Precio venta",
    "Precio fijo",
]


def export_catalog_template_csv(path: Path, include_data: bool = True) -> Path:
    exports_dir = get_portable_dir("exports")
    if path.is_dir():
        path = exports_dir / "catalogo_template.csv"
    elif not path.is_absolute():
        path = exports_dir / path

    rows = _load_rows() if include_data else []
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(HEADERS)
        for row in rows:
            writer.writerow(row)
    return path


def export_catalog_template_xlsx(path: Path, include_data: bool = True) -> Path:
    exports_dir = get_portable_dir("exports")
    if path.is_dir():
        path = exports_dir / "catalogo_template.xlsx"
    elif not path.is_absolute():
        path = exports_dir / path

    rows = _load_rows() if include_data else []
    wb = Workbook()
    ws = wb.active
    ws.title = "Catalogo"
    ws.append(HEADERS)
    for row in rows:
        ws.append(row)
    wb.save(path)
    return path


def _load_rows() -> list[list]:
    rows: list[list] = []
    with get_session() as session:
        products = session.query(Product).order_by(Product.ref.asc()).all()
        for p in products:
            rows.append(
                [
                    p.ref or "",
                    p.category.code if p.category else "",
                    p.category.name if p.category else "",
                    p.short_desc or "",
                    p.long_desc or "",
                    p.unit or "",
                    float(p.cost or 0),
                    float(p.margin or 0),
                    float(p.sale_price or 0),
                    "fixed" if p.fixed_price else "",
                ]
            )
    return rows

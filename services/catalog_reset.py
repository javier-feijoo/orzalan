from __future__ import annotations

import csv
from pathlib import Path

from db.models import Product, ProductCategory
from db.session import get_session


def reset_catalog(use_base: bool = True) -> tuple[int, int]:
    """Delete all products and categories, then optionally load base catalog.

    Returns (products_count, categories_count) after reset.
    """
    with get_session() as session:
        session.query(Product).delete()
        session.query(ProductCategory).delete()
        session.commit()

        # Always keep default category
        session.add(ProductCategory(code="SIN", name="Sin categoria"))
        session.commit()

        if use_base:
            base_csv = Path(__file__).resolve().parent.parent / "assets" / "catalogo_base.csv"
            if base_csv.exists():
                _load_catalog_csv(session, base_csv)

        products = session.query(Product).count()
        categories = session.query(ProductCategory).count()
        return products, categories


def reset_all(use_base: bool = True) -> tuple[int, int, int, int]:
    """Delete all catalog, categories, clients and quotes. Optionally load base catalog.

    Returns (products_count, categories_count, clients_count, quotes_count) after reset.
    """
    from db.models import Client, Quote, QuoteLine

    with get_session() as session:
        session.query(QuoteLine).delete()
        session.query(Quote).delete()
        session.query(Client).delete()
        session.query(Product).delete()
        session.query(ProductCategory).delete()
        session.commit()

        session.add(ProductCategory(code="SIN", name="Sin categoria"))
        session.commit()

        if use_base:
            base_csv = Path(__file__).resolve().parent.parent / "assets" / "catalogo_base.csv"
            if base_csv.exists():
                _load_catalog_csv(session, base_csv)

        products = session.query(Product).count()
        categories = session.query(ProductCategory).count()
        clients = session.query(Client).count()
        quotes = session.query(Quote).count()
        return products, categories, clients, quotes

    # Reset company settings (empresa.json)
    from settings import Settings
    settings = Settings.load()
    settings.set("company_name", "")
    settings.set("company_tax_id", "")
    settings.set("company_address", "")
    settings.set("company_phone", "")
    settings.set("company_email", "")
    settings.set("company_web", "")
    settings.set("logo_path", "")
    settings.set("default_vat", "")
    settings.set("default_margin", "")
    settings.save()


def _load_catalog_csv(session, path: Path) -> None:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = [dict(r) for r in reader]

    existing_codes = {c.code for c in session.query(ProductCategory).all() if c.code}
    existing_names = {c.name for c in session.query(ProductCategory).all() if c.name}

    # Create categories
    for row in rows:
        code = (row.get("Código categoría") or row.get("Codigo categoria") or "").strip().upper()
        name = (row.get("Categoría") or row.get("Categoria") or "").strip()
        if not name:
            name = "Sin categoria"
        if not code:
            code = _cat_prefix(name)
        if code in existing_codes or name in existing_names:
            continue
        session.add(ProductCategory(code=code, name=name))
        existing_codes.add(code)
        existing_names.add(name)
    session.commit()

    # Insert products
    for row in rows:
        ref = (row.get("Referencia") or "").strip()
        if not ref:
            continue
        if session.query(Product).filter(Product.ref == ref).first() is not None:
            continue
        code = (row.get("Código categoría") or row.get("Codigo categoria") or "").strip().upper()
        name = (row.get("Categoría") or row.get("Categoria") or "").strip() or "Sin categoria"
        if not code:
            code = _cat_prefix(name)
        cat = session.query(ProductCategory).filter(ProductCategory.code == code).first()
        if cat is None:
            cat = ProductCategory(code=code, name=name)
            session.add(cat)
            session.commit()

        cost = _to_float(row.get("Precio coste") or row.get("Precio costo"), 0.0)
        margin = _normalize_margin(_to_float(row.get("Beneficio"), 0.0))
        sale_price = _to_float(row.get("Precio venta"), 0.0)
        fixed = (row.get("Precio fijo") or "").strip().lower() == "fixed"
        if not fixed and not sale_price:
            sale_price = cost * (1 + margin)

        product = Product(
            ref=ref,
            category_id=cat.id,
            short_desc=(row.get("Nombre") or "").strip(),
            long_desc=(row.get("Descripción") or row.get("Descripcion") or "").strip(),
            unit=(row.get("Unidad") or "").strip(),
            cost=cost,
            margin=margin,
            sale_price=sale_price,
            fixed_price=fixed,
            vat=0.21,
            active=True,
        )
        session.add(product)
    session.commit()


def _cat_prefix(name: str) -> str:
    base = "".join([c for c in name.upper() if c.isalnum()])[:3]
    return base or "CAT"


def _normalize_margin(value: float) -> float:
    if value > 1:
        return value / 100.0
    return value


def _to_float(value, default: float) -> float:
    if value is None:
        return default
    try:
        return float(str(value).replace(",", "."))
    except Exception:
        return default

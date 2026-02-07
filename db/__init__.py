from __future__ import annotations

import csv
from pathlib import Path

from sqlalchemy import select, text

from db.models import Base, Product, ProductCategory
from db.session import get_engine, get_session


def init_db() -> None:
    engine = get_engine()
    Base.metadata.create_all(engine)
    _migrate_schema(engine)

    # Optional seed
    with get_session() as session:
        _seed_base_catalog(session)


def _cat_prefix(cat: str) -> str:
    mapping = {
        "Cableado": "CAB",
        "Canalizaciones": "CAN",
        "Racks y armarios": "RCK",
        "Dispositivos de red": "RED",
        "Energia": "ENE",
        "Servicios": "SRV",
        "Conectividad": "CON",
        "Sin categoria": "SIN",
    }
    return mapping.get(cat, "CAT")


def _seed_base_catalog(session) -> None:
    # Always ensure default category exists
    if session.query(ProductCategory).filter(ProductCategory.name == "Sin categoria").first() is None:
        session.add(ProductCategory(code="SIN", name="Sin categoria"))
        session.commit()

    has_products = session.execute(select(Product.id).limit(1)).first()
    if has_products is not None:
        return

    csv_path = Path(__file__).resolve().parent.parent / "assets" / "catalogo_base.csv"
    if not csv_path.exists():
        return

    _load_catalog_csv(session, csv_path)


def _load_catalog_csv(session, path: Path) -> None:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = [dict(r) for r in reader]

    # Create categories
    existing_codes = {c.code for c in session.query(ProductCategory).all() if c.code}
    existing_names = {c.name for c in session.query(ProductCategory).all() if c.name}

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
        cost = _to_float(row.get("Precio coste") or row.get("Precio coste".capitalize()) or row.get("Precio costo"), 0.0)
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


def _migrate_schema(engine) -> None:
    with engine.begin() as conn:
        cols = conn.execute(text("PRAGMA table_info(product_categories)")).fetchall()
        col_names = {c[1] for c in cols}
        if "code" not in col_names:
            conn.execute(text("ALTER TABLE product_categories ADD COLUMN code VARCHAR(32)"))

        cols = conn.execute(text("PRAGMA table_info(products)")).fetchall()
        col_names = {c[1] for c in cols}
        if "category_id" not in col_names:
            conn.execute(text("ALTER TABLE products ADD COLUMN category_id INTEGER"))

        # Ensure default category
        conn.execute(
            text(
                "INSERT OR IGNORE INTO product_categories (name, code) VALUES ('Sin categoria', 'SIN')"
            )
        )

        # Populate missing codes
        rows = conn.execute(text("SELECT id, name, code FROM product_categories")).fetchall()
        for row in rows:
            if not row[2]:
                code = _cat_prefix(row[1])
                conn.execute(
                    text("UPDATE product_categories SET code=:code WHERE id=:id"),
                    {"code": code, "id": row[0]},
                )

        # If legacy column exists, migrate to new schema and drop it.
        prod_cols = conn.execute(text("PRAGMA table_info(products)")).fetchall()
        prod_col_names = {c[1] for c in prod_cols}
        products_sql = conn.execute(
            text("SELECT sql FROM sqlite_master WHERE type='table' AND name='products'")
        ).scalar()
        sql_text = str(products_sql or "").lower()
        has_legacy_category = "category" in prod_col_names or '"category"' in sql_text or " category " in sql_text or " category," in sql_text

        if has_legacy_category:
            rows = conn.execute(
                text("SELECT id, category_id, category FROM products")
            ).fetchall()
            for row in rows:
                if row[1] is not None:
                    continue
                cat_name = row[2] or "Sin categoria"
                cat_id = conn.execute(
                    text("SELECT id FROM product_categories WHERE name=:name"),
                    {"name": cat_name},
                ).scalar()
                if cat_id is None:
                    conn.execute(
                        text("INSERT INTO product_categories (name, code) VALUES (:name, :code)"),
                        {"name": cat_name, "code": _cat_prefix(cat_name)},
                    )
                    cat_id = conn.execute(
                        text("SELECT id FROM product_categories WHERE name=:name"),
                        {"name": cat_name},
                    ).scalar()
                conn.execute(
                    text("UPDATE products SET category_id=:cid WHERE id=:id"),
                    {"cid": cat_id, "id": row[0]},
                )

            # Rebuild products table without legacy 'category' column
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS products_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        ref VARCHAR(64) NOT NULL UNIQUE,
                        category_id INTEGER,
                        short_desc VARCHAR(255) NOT NULL,
                        long_desc TEXT,
                        unit VARCHAR(32) NOT NULL,
                        cost NUMERIC(12, 4) NOT NULL DEFAULT 0,
                        margin NUMERIC(8, 4) NOT NULL DEFAULT 0,
                        sale_price NUMERIC(12, 4) NOT NULL DEFAULT 0,
                        fixed_price BOOLEAN NOT NULL DEFAULT 0,
                        vat NUMERIC(6, 4),
                        active BOOLEAN NOT NULL DEFAULT 1,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
            )
            conn.execute(
                text(
                    """
                    INSERT INTO products_new
                    (id, ref, category_id, short_desc, long_desc, unit, cost, margin, sale_price, fixed_price, vat, active, updated_at)
                    SELECT
                        id, ref, category_id, short_desc, long_desc, unit, cost, margin, sale_price, fixed_price, vat, active, updated_at
                    FROM products
                    """
                )
            )
            conn.execute(text("DROP TABLE products"))
            conn.execute(text("ALTER TABLE products_new RENAME TO products"))


def _cat_id(name: str) -> int:
    with get_session() as session:
        cat = session.query(ProductCategory).filter(ProductCategory.name == name).first()
        if cat is None:
            cat = ProductCategory(code=_cat_prefix(name), name=name)
            session.add(cat)
            session.commit()
        return cat.id

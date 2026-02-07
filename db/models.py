from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ref: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    category_id: Mapped[int] = mapped_column(ForeignKey("product_categories.id"), nullable=True)
    short_desc: Mapped[str] = mapped_column(String(255), nullable=False)
    long_desc: Mapped[str] = mapped_column(Text, nullable=True)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    cost: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False, default=0)
    margin: Mapped[float] = mapped_column(Numeric(8, 4), nullable=False, default=0)
    sale_price: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False, default=0)
    fixed_price: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    vat: Mapped[Optional[float]] = mapped_column(Numeric(6, 4), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    category: Mapped["ProductCategory"] = relationship(back_populates="products")
    quote_lines: Mapped[list["QuoteLine"]] = relationship(back_populates="product")


class ProductCategory(Base):
    __tablename__ = "product_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[Optional[str]] = mapped_column(String(32), unique=True, nullable=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)

    products: Mapped[list["Product"]] = relationship(back_populates="category")


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    tax_id: Mapped[str] = mapped_column(String(64), nullable=True)
    address: Mapped[str] = mapped_column(Text, nullable=True)
    phone: Mapped[str] = mapped_column(String(64), nullable=True)
    email: Mapped[str] = mapped_column(String(255), nullable=True)
    contact_person: Mapped[str] = mapped_column(String(128), nullable=True)
    default_discount: Mapped[float] = mapped_column(Numeric(8, 4), nullable=False, default=0)
    notes: Mapped[str] = mapped_column(Text, nullable=True)

    quotes: Mapped[list["Quote"]] = relationship(back_populates="client")


class Quote(Base):
    __tablename__ = "quotes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    number: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    valid_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="Borrador")
    vat_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="line")
    global_vat: Mapped[float] = mapped_column(Numeric(8, 4), nullable=False, default=0)
    global_discount: Mapped[float] = mapped_column(Numeric(8, 4), nullable=False, default=0)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    subtotal: Mapped[float] = mapped_column(Numeric(14, 4), nullable=False, default=0)
    vat_total: Mapped[float] = mapped_column(Numeric(14, 4), nullable=False, default=0)
    total: Mapped[float] = mapped_column(Numeric(14, 4), nullable=False, default=0)

    client: Mapped["Client"] = relationship(back_populates="quotes")
    lines: Mapped[list["QuoteLine"]] = relationship(back_populates="quote", cascade="all, delete-orphan")


class QuoteLine(Base):
    __tablename__ = "quote_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    quote_id: Mapped[int] = mapped_column(ForeignKey("quotes.id"), nullable=False)
    product_id: Mapped[Optional[int]] = mapped_column(ForeignKey("products.id"), nullable=True)

    # Snapshot fields to preserve historical pricing
    ref_snapshot: Mapped[str] = mapped_column(String(64), nullable=False)
    desc_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    unit_snapshot: Mapped[str] = mapped_column(String(32), nullable=False)
    qty: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False, default=1)
    unit_price_snapshot: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False, default=0)
    discount: Mapped[float] = mapped_column(Numeric(8, 4), nullable=False, default=0)
    vat: Mapped[Optional[float]] = mapped_column(Numeric(8, 4), nullable=True)
    line_subtotal: Mapped[float] = mapped_column(Numeric(14, 4), nullable=False, default=0)
    line_total: Mapped[float] = mapped_column(Numeric(14, 4), nullable=False, default=0)

    quote: Mapped["Quote"] = relationship(back_populates="lines")
    product: Mapped[Optional["Product"]] = relationship(back_populates="quote_lines")

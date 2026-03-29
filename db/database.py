"""
db/database.py — SQLite database setup with SQLAlchemy ORM.
Includes seeded mock data for demo.
"""

from sqlalchemy import (
    create_engine, Column, String, Float, Integer,
    Boolean, DateTime, JSON, Text, ForeignKey
)
from sqlalchemy.orm import DeclarativeBase, Session, relationship
from sqlalchemy.sql import func
from datetime import datetime, timedelta
import json, uuid, random

DATABASE_URL = "sqlite:///./invoice_os.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


class Base(DeclarativeBase):
    pass


class Invoice(Base):
    __tablename__ = "invoices"

    id           = Column(String, primary_key=True, default=lambda: str(uuid.uuid4())[:8].upper())
    idempotency_key = Column(String, unique=True, index=True)
    vendor       = Column(String, nullable=False)
    invoice_number = Column(String, nullable=False)
    invoice_date = Column(String)
    po_ref       = Column(String)
    subtotal     = Column(Float, default=0.0)
    tax          = Column(Float, default=0.0)
    shipping     = Column(Float, default=0.0)
    total        = Column(Float, default=0.0)
    currency     = Column(String, default="USD")
    status       = Column(String, default="pending")   # pending|processing|approved|mismatch|adjusted
    confidence   = Column(Float, default=1.0)
    line_items   = Column(JSON, default=list)
    actions_taken = Column(JSON, default=list)
    created_at   = Column(DateTime, default=func.now())
    updated_at   = Column(DateTime, default=func.now(), onupdate=func.now())
    retry_count  = Column(Integer, default=0)


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id           = Column(String, primary_key=True)
    vendor       = Column(String, nullable=False)
    po_date      = Column(String)
    approved_total = Column(Float)
    currency     = Column(String, default="USD")
    line_items   = Column(JSON, default=list)
    tax_rate     = Column(Float, default=0.10)
    shipping_allowance = Column(Float, default=0.0)
    active       = Column(Boolean, default=True)


class Ticket(Base):
    __tablename__ = "tickets"

    id           = Column(String, primary_key=True, default=lambda: f"TKT-{uuid.uuid4().hex[:6].upper()}")
    invoice_id   = Column(String, ForeignKey("invoices.id"))
    title        = Column(String)
    description  = Column(Text)
    priority     = Column(String, default="MEDIUM")   # LOW|MEDIUM|HIGH|CRITICAL
    status       = Column(String, default="open")      # open|in_progress|resolved|auto_closed
    resolution   = Column(Text)
    created_at   = Column(DateTime, default=func.now())
    resolved_at  = Column(DateTime, nullable=True)
    auto_closed  = Column(Boolean, default=False)


class IdempotencyLog(Base):
    __tablename__ = "idempotency_log"

    key       = Column(String, primary_key=True)
    result    = Column(JSON)
    created_at = Column(DateTime, default=func.now())


class OutcomeLog(Base):
    __tablename__ = "outcome_log"

    id           = Column(String, primary_key=True, default=lambda: str(uuid.uuid4())[:8])
    invoice_id   = Column(String)
    vendor       = Column(String)
    outcome      = Column(String)   # approved|adjusted|escalated|error
    mismatch_delta = Column(Float, default=0.0)
    processing_ms  = Column(Integer, default=0)
    created_at   = Column(DateTime, default=func.now())


def init_db():
    Base.metadata.create_all(bind=engine)
    with Session(engine) as session:
        if session.query(PurchaseOrder).count() > 0:
            return  # Already seeded

        # Seed purchase orders
        pos = [
            PurchaseOrder(
                id="PO-881", vendor="Acme Corp", po_date="2024-01-10",
                approved_total=12500.00, tax_rate=0.08, shipping_allowance=150.0,
                line_items=[
                    {"sku": "WIDGET-A", "description": "Widget Type A", "qty": 100, "unit_price": 85.00},
                    {"sku": "WIDGET-B", "description": "Widget Type B", "qty": 50,  "unit_price": 110.00},
                    {"sku": "SUPPORT-1","description": "Setup Support",  "qty": 1,   "unit_price": 450.00},
                ]
            ),
            PurchaseOrder(
                id="PO-882", vendor="GlobalSupply", po_date="2024-01-11",
                approved_total=8750.50, tax_rate=0.10, shipping_allowance=200.0,
                line_items=[
                    {"sku": "CABLE-USB", "description": "USB-C Cable 2m", "qty": 200, "unit_price": 18.50},
                    {"sku": "ADAPTER-EU","description": "EU Power Adapter","qty": 75,  "unit_price": 32.00},
                    {"sku": "BAG-LG",    "description": "Carry Bag Large",  "qty": 50,  "unit_price": 28.00},
                ]
            ),
            PurchaseOrder(
                id="PO-883", vendor="TechParts Ltd", po_date="2024-01-12",
                approved_total=3200.00, tax_rate=0.08, shipping_allowance=100.0,
                line_items=[
                    {"sku": "CHIP-MCU",  "description": "Microcontroller Unit", "qty": 40, "unit_price": 55.00},
                    {"sku": "SENSOR-T",  "description": "Temperature Sensor",   "qty": 60, "unit_price": 18.33},
                ]
            ),
            PurchaseOrder(
                id="PO-884", vendor="FastLog Inc", po_date="2024-01-13",
                approved_total=14800.00, tax_rate=0.10, shipping_allowance=500.0,
                line_items=[
                    {"sku": "LOG-SRV",  "description": "Logging Server License", "qty": 2, "unit_price": 4500.00},
                    {"sku": "STORAGE-1","description": "Storage 1TB",            "qty": 5, "unit_price": 560.00},
                    {"sku": "MAINT-ANN","description": "Annual Maintenance",      "qty": 1, "unit_price": 2400.00},
                ]
            ),
        ]
        for po in pos:
            session.add(po)

        # Seed invoices
        invoices = [
            Invoice(
                id="INV-001", idempotency_key="idem-001",
                vendor="Acme Corp", invoice_number="ACM-2024-001",
                invoice_date="2024-01-15", po_ref="PO-881",
                subtotal=11574.07, tax=925.93, shipping=0.0, total=12500.00,
                status="approved", confidence=0.97,
                line_items=[
                    {"sku": "WIDGET-A", "qty": 100, "unit_price": 85.00, "amount": 8500.00},
                    {"sku": "WIDGET-B", "qty": 50,  "unit_price": 110.00,"amount": 5500.00},
                    {"sku": "SUPPORT-1","qty": 1,   "unit_price": 450.00,"amount": 450.00},
                ],
                actions_taken=["Auto-approved: total within tolerance"],
            ),
            Invoice(
                id="INV-002", idempotency_key="idem-002",
                vendor="GlobalSupply", invoice_number="GS-2024-089",
                invoice_date="2024-01-16", po_ref="PO-882",
                subtotal=7953.00, tax=795.30, shipping=2.20, total=8750.50,
                status="approved", confidence=0.95,
                line_items=[
                    {"sku": "CABLE-USB","qty": 200, "unit_price": 18.50, "amount": 3700.00},
                    {"sku": "ADAPTER-EU","qty":75,  "unit_price": 32.00, "amount": 2400.00},
                    {"sku": "BAG-LG",   "qty": 50,  "unit_price": 28.00, "amount": 1400.00},
                    {"sku": "SHIPPING", "qty": 1,   "unit_price": 2.20,  "amount": 2.20},
                ],
                actions_taken=["Auto-approved: all line items match PO within tolerance"],
            ),
            Invoice(
                id="INV-003", idempotency_key="idem-003",
                vendor="FastLog Inc", invoice_number="FL-2024-412",
                invoice_date="2024-01-18", po_ref="PO-884",
                subtotal=13636.36, tax=1363.64, shipping=300.00, total=15300.00,
                status="mismatch", confidence=0.91,
                line_items=[
                    {"sku": "LOG-SRV",  "qty": 2, "unit_price": 4500.00, "amount": 9000.00},
                    {"sku": "STORAGE-1","qty": 5, "unit_price": 575.00,  "amount": 2875.00},  # Unit price mismatch: 560 vs 575
                    {"sku": "MAINT-ANN","qty": 1, "unit_price": 2400.00, "amount": 2400.00},
                    {"sku": "SHIPPING", "qty": 1, "unit_price": 300.00,  "amount": 300.00},   # Exceeds shipping allowance
                ],
                actions_taken=[
                    "Mismatch detected: STORAGE-1 unit price $575 vs PO $560 (+$75 total)",
                    "Mismatch detected: Shipping $300 exceeds allowance $500 — within range",
                    "Ticket TKT-A3B2C1 created: STORAGE-1 price discrepancy",
                    "Vendor email sent requesting price clarification",
                ],
            ),
            Invoice(
                id="INV-004", idempotency_key="idem-004",
                vendor="TechParts Ltd", invoice_number="TP-2024-077",
                invoice_date="2024-01-17", po_ref="PO-883",
                subtotal=3200.00, tax=256.00, shipping=100.00, total=3556.00,
                status="adjusted", confidence=0.88,
                line_items=[
                    {"sku": "CHIP-MCU", "qty": 40, "unit_price": 55.00,   "amount": 2200.00},
                    {"sku": "SENSOR-T", "qty": 60, "unit_price": 18.33,   "amount": 1099.80},  # Rounding
                    {"sku": "SHIPPING", "qty": 1,  "unit_price": 100.00,  "amount": 100.00},
                ],
                actions_taken=[
                    "Minor rounding delta $0.20 detected on SENSOR-T",
                    "Auto-adjusted: within 0.5% tolerance — approved",
                ],
            ),
            Invoice(
                id="INV-005", idempotency_key="idem-005",
                vendor="Acme Corp", invoice_number="ACM-2024-002",
                invoice_date="2024-01-19", po_ref="PO-881",
                subtotal=None, tax=None, shipping=None, total=None,
                status="pending", confidence=0.62,
                line_items=[],
                actions_taken=["Extraction low confidence (0.62): awaiting manual verification"],
            ),
        ]
        for inv in invoices:
            session.add(inv)

        # Seed tickets
        tickets = [
            Ticket(
                id="TKT-A3B2C1", invoice_id="INV-003",
                title="Price discrepancy: STORAGE-1 (FastLog Inc)",
                description="Invoice charges $575/unit for STORAGE-1. PO PO-884 specifies $560/unit. Total delta: +$75.00 on 5 units.",
                priority="HIGH", status="open",
            ),
            Ticket(
                id="TKT-D4E5F6", invoice_id="INV-003",
                title="Vendor clarification requested: FL-2024-412",
                description="Automated email sent to FastLog Inc requesting price justification and updated invoice. Awaiting response.",
                priority="MEDIUM", status="in_progress",
            ),
            Ticket(
                id="TKT-G7H8I9", invoice_id="INV-004",
                title="Auto-adjusted: TechParts rounding delta",
                description="SENSOR-T rounding difference of $0.20 detected and automatically approved within tolerance threshold.",
                priority="LOW", status="auto_closed",
                resolution="Auto-resolved: delta within 0.5% tolerance. Invoice auto-approved.",
                resolved_at=datetime.utcnow() - timedelta(hours=2),
                auto_closed=True,
            ),
            Ticket(
                id="TKT-J1K2L3", invoice_id="INV-005",
                title="Low confidence extraction: ACM-2024-002",
                description="PDF extraction returned confidence score of 0.62. Manual verification required before processing.",
                priority="MEDIUM", status="open",
            ),
        ]
        for t in tickets:
            session.add(t)

        session.commit()
        print("[DB] Seeded: 4 POs, 5 invoices, 4 tickets")


def get_session():
    with Session(engine) as session:
        yield session

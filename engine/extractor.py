"""
engine/extractor.py — Invoice data extraction.

Strategies (in order):
1. pdfplumber — structured PDF extraction
2. Regex fallback — pattern-based extraction
3. Mock fallback — demo data

Each strategy returns a confidence score (0.0–1.0).
"""

import re
import hashlib
from typing import Any
from pathlib import Path


def compute_idempotency_key(content: bytes | str) -> str:
    """SHA-256 hash of raw content — prevents duplicate processing."""
    if isinstance(content, str):
        content = content.encode()
    return hashlib.sha256(content).hexdigest()[:32]


def extract_from_pdf(pdf_path: str) -> dict[str, Any]:
    """Extract invoice data from a real PDF using pdfplumber."""
    try:
        import pdfplumber

        with pdfplumber.open(pdf_path) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)

        result = _parse_text(text)
        result["source"] = "pdfplumber"
        with open(pdf_path, "rb") as f:
            result["idempotency_key"] = compute_idempotency_key(f.read())
        return result

    except ImportError:
        return extract_from_text(Path(pdf_path).read_text(encoding="utf-8", errors="ignore"))
    except Exception as exc:
        return {"error": str(exc), "confidence": 0.0, "source": "error"}


def extract_from_text(text: str) -> dict[str, Any]:
    """Extract invoice data from raw text using regex patterns."""
    result = _parse_text(text)
    result["source"] = "regex"
    result["idempotency_key"] = compute_idempotency_key(text)
    return result


def extract_mock(invoice_id: str = "DEMO-001") -> dict[str, Any]:
    """Return realistic mock invoice data for demo/testing."""
    MOCKS = {
        "DEMO-001": {
            "vendor": "Acme Corp",
            "invoice_number": "ACM-2024-001",
            "invoice_date": "2024-01-15",
            "po_ref": "PO-881",
            "subtotal": 11574.07,
            "tax": 925.93,
            "shipping": 0.0,
            "total": 12500.00,
            "currency": "USD",
            "line_items": [
                {"sku": "WIDGET-A",  "description": "Widget Type A", "qty": 100, "unit_price": 85.00,  "amount": 8500.00},
                {"sku": "WIDGET-B",  "description": "Widget Type B", "qty": 50,  "unit_price": 110.00, "amount": 5500.00},
                {"sku": "SUPPORT-1", "description": "Setup Support",  "qty": 1,   "unit_price": 450.00, "amount": 450.00},
            ],
            "confidence": 0.97,
            "source": "mock",
            "idempotency_key": compute_idempotency_key("DEMO-001"),
        },
        "DEMO-MISMATCH": {
            "vendor": "FastLog Inc",
            "invoice_number": "FL-2024-412",
            "invoice_date": "2024-01-18",
            "po_ref": "PO-884",
            "subtotal": 13636.36,
            "tax": 1363.64,
            "shipping": 300.00,
            "total": 15300.00,
            "currency": "USD",
            "line_items": [
                {"sku": "LOG-SRV",   "description": "Logging Server License", "qty": 2, "unit_price": 4500.00, "amount": 9000.00},
                {"sku": "STORAGE-1", "description": "Storage 1TB",            "qty": 5, "unit_price": 575.00,  "amount": 2875.00},
                {"sku": "MAINT-ANN", "description": "Annual Maintenance",      "qty": 1, "unit_price": 2400.00, "amount": 2400.00},
                {"sku": "SHIPPING",  "description": "Shipping",                "qty": 1, "unit_price": 300.00,  "amount": 300.00},
            ],
            "confidence": 0.91,
            "source": "mock",
            "idempotency_key": compute_idempotency_key("DEMO-MISMATCH"),
        },
    }
    return MOCKS.get(invoice_id, MOCKS["DEMO-001"])


# ── Internal ──────────────────────────────────────────────────────────────────

def _parse_text(text: str) -> dict[str, Any]:
    """
    Extract invoice fields from plain text using regex.
    Returns extracted fields + confidence score.
    """
    extracted = {}
    score_hits = 0
    score_possible = 8

    def find(patterns: list[str], cast=str, default=None):
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE | re.MULTILINE)
            if m:
                try:
                    return cast(m.group(1).strip().replace(",", ""))
                except Exception:
                    pass
        return default

    extracted["vendor"] = find([
        r"(?:vendor|supplier|from)[:\s]+([A-Za-z0-9\s&,\.]+?)(?:\n|Ltd|Inc|Corp|LLC)",
        r"^([A-Za-z0-9\s&,\.]{3,50})\s*$",
    ]) or "Unknown Vendor"
    if extracted["vendor"] != "Unknown Vendor":
        score_hits += 1

    extracted["invoice_number"] = find([
        r"invoice\s*(?:no|number|#)[:\s]+([A-Z0-9\-]+)",
        r"inv[:\s]+([A-Z0-9\-]+)",
    ])
    if extracted["invoice_number"]:
        score_hits += 1

    extracted["invoice_date"] = find([
        r"(?:invoice|issue)\s*date[:\s]+(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})",
        r"date[:\s]+(\d{4}-\d{2}-\d{2})",
    ])
    if extracted["invoice_date"]:
        score_hits += 1

    extracted["po_ref"] = find([
        r"(?:po|purchase order|po\s*number|po\s*ref)[:\s]+([A-Z0-9\-]+)",
        r"(?:ref|reference)[:\s]+([A-Z0-9\-]+)",
    ])
    if extracted["po_ref"]:
        score_hits += 1

    extracted["subtotal"] = find([r"subtotal[:\s]+\$?([\d,]+\.?\d*)"], float)
    extracted["tax"]      = find([r"tax[:\s]+\$?([\d,]+\.?\d*)",
                                   r"vat[:\s]+\$?([\d,]+\.?\d*)"], float)
    extracted["shipping"] = find([r"shipping[:\s]+\$?([\d,]+\.?\d*)",
                                   r"freight[:\s]+\$?([\d,]+\.?\d*)"], float)
    extracted["total"]    = find([r"total[:\s]+\$?([\d,]+\.?\d*)",
                                   r"amount due[:\s]+\$?([\d,]+\.?\d*)"], float)

    if extracted["total"]:
        score_hits += 1

    # Parse line items
    line_items = []
    li_pattern = re.findall(
        r"([A-Z][A-Z0-9\-]{2,})\s+([\w\s]+?)\s+(\d+(?:\.\d+)?)\s+\$?([\d,]+\.?\d+)\s+\$?([\d,]+\.?\d+)",
        text,
    )
    for match in li_pattern:
        sku, desc, qty, unit_price, amount = match
        line_items.append({
            "sku": sku,
            "description": desc.strip(),
            "qty": float(qty),
            "unit_price": float(unit_price.replace(",", "")),
            "amount": float(amount.replace(",", "")),
        })
    if line_items:
        score_hits += 2

    extracted["line_items"] = line_items
    extracted["currency"]   = "USD"
    extracted["confidence"] = round(score_hits / score_possible, 2)

    return extracted

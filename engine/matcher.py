"""
engine/matcher.py — Line-item matching engine.

Performs:
- 2-way PO matching
- SKU + quantity validation
- Unit price comparison
- Tax + shipping handling
- Configurable tolerance thresholds
"""

from dataclasses import dataclass, field
from typing import Any
import math


# ── Configurable Tolerance Rules ──────────────────────────────────────────────

TOLERANCE_CONFIG = {
    "total_pct":       0.02,    # 2%   — total invoice vs PO total
    "line_item_pct":   0.01,    # 1%   — per-line-item amount
    "unit_price_pct":  0.005,   # 0.5% — unit price mismatch
    "tax_pct":         0.01,    # 1%   — tax amount
    "shipping_abs":    50.00,   # $50  — absolute shipping allowance variance
    "rounding_abs":    1.00,    # $1   — small rounding differences
}

RESOLUTION_CONFIG = {
    "auto_approve_threshold":  0.02,   # Auto-approve if delta <= 2%
    "auto_adjust_threshold":   0.005,  # Auto-adjust if delta <= 0.5%
    "require_vendor_email":    True,   # Email vendor on mismatches > threshold
    "auto_close_on_resolve":   True,   # Auto-close ticket when resolved
    "max_retries":             3,
}


@dataclass
class LineItemResult:
    sku:           str
    status:        str          # match|price_mismatch|qty_mismatch|missing_in_po|missing_in_invoice
    invoice_qty:   float = 0.0
    po_qty:        float = 0.0
    invoice_price: float = 0.0
    po_price:      float = 0.0
    invoice_amount:float = 0.0
    po_amount:     float = 0.0
    delta:         float = 0.0
    delta_pct:     float = 0.0
    within_tolerance: bool = True
    notes:         str = ""


@dataclass
class MatchResult:
    invoice_id:      str
    po_id:           str
    vendor:          str

    # Totals
    invoice_total:   float = 0.0
    po_total:        float = 0.0
    total_delta:     float = 0.0
    total_delta_pct: float = 0.0

    # Tax / Shipping
    invoice_tax:      float = 0.0
    expected_tax:     float = 0.0
    tax_delta:        float = 0.0

    invoice_shipping: float = 0.0
    allowed_shipping: float = 0.0
    shipping_delta:   float = 0.0

    # Line items
    line_results:    list[LineItemResult] = field(default_factory=list)

    # Verdict
    verdict:         str = "pending"    # approved|adjusted|mismatch|error
    mismatch_reasons:list[str] = field(default_factory=list)
    confidence:      float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "invoice_id":      self.invoice_id,
            "po_id":           self.po_id,
            "vendor":          self.vendor,
            "invoice_total":   self.invoice_total,
            "po_total":        self.po_total,
            "total_delta":     round(self.total_delta, 2),
            "total_delta_pct": round(self.total_delta_pct * 100, 3),
            "invoice_tax":     self.invoice_tax,
            "expected_tax":    self.expected_tax,
            "tax_delta":       round(self.tax_delta, 2),
            "invoice_shipping":self.invoice_shipping,
            "allowed_shipping":self.allowed_shipping,
            "shipping_delta":  round(self.shipping_delta, 2),
            "verdict":         self.verdict,
            "mismatch_reasons":self.mismatch_reasons,
            "confidence":      self.confidence,
            "line_results": [
                {
                    "sku":             lr.sku,
                    "status":          lr.status,
                    "invoice_qty":     lr.invoice_qty,
                    "po_qty":          lr.po_qty,
                    "invoice_price":   lr.invoice_price,
                    "po_price":        lr.po_price,
                    "delta":           round(lr.delta, 2),
                    "delta_pct":       round(lr.delta_pct * 100, 3),
                    "within_tolerance":lr.within_tolerance,
                    "notes":           lr.notes,
                }
                for lr in self.line_results
            ],
        }


class MatchingEngine:
    """
    2-way matching engine: Invoice ↔ PO.
    Compares line items, totals, tax, and shipping.
    """

    def __init__(self, config: dict | None = None):
        self.tol = {**TOLERANCE_CONFIG, **(config or {})}

    def match(self, invoice: dict, po: dict) -> MatchResult:
        result = MatchResult(
            invoice_id    = invoice.get("id", ""),
            po_id         = po.get("id", ""),
            vendor        = invoice.get("vendor", ""),
            invoice_total = invoice.get("total", 0.0) or 0.0,
            po_total      = po.get("approved_total", 0.0) or 0.0,
            invoice_tax   = invoice.get("tax", 0.0) or 0.0,
            invoice_shipping = invoice.get("shipping", 0.0) or 0.0,
            allowed_shipping = po.get("shipping_allowance", 0.0) or 0.0,
        )

        # ── Line-item matching ────────────────────────────────────────────────
        inv_items = {item["sku"]: item for item in (invoice.get("line_items") or [])
                     if item.get("sku") and item["sku"] != "SHIPPING"}
        po_items  = {item["sku"]: item for item in (po.get("line_items") or [])}

        # Items in invoice but not PO
        for sku, inv_item in inv_items.items():
            if sku not in po_items:
                lr = LineItemResult(
                    sku=sku, status="missing_in_po",
                    invoice_qty=inv_item.get("qty", 0),
                    invoice_price=inv_item.get("unit_price", 0),
                    invoice_amount=inv_item.get("amount", 0),
                    within_tolerance=False,
                    notes=f"SKU {sku} not found in PO {po.get('id')}",
                )
                result.line_results.append(lr)
                result.mismatch_reasons.append(f"Unknown SKU: {sku}")
                continue

            po_item = po_items[sku]
            self._compare_line_item(lr := LineItemResult(sku=sku, status="match"),
                                    inv_item, po_item, result)
            result.line_results.append(lr)

        # Items in PO but not invoice
        for sku in po_items:
            if sku not in inv_items:
                lr = LineItemResult(
                    sku=sku, status="missing_in_invoice",
                    po_qty=po_items[sku].get("qty", 0),
                    po_price=po_items[sku].get("unit_price", 0),
                    within_tolerance=False,
                    notes=f"PO line item {sku} missing from invoice",
                )
                result.line_results.append(lr)
                result.mismatch_reasons.append(f"Missing line item: {sku}")

        # ── Tax validation ─────────────────────────────────────────────────────
        invoice_subtotal = invoice.get("subtotal") or 0.0
        tax_rate = po.get("tax_rate", 0.10)
        result.expected_tax = round(invoice_subtotal * tax_rate, 2)
        result.tax_delta = abs(result.invoice_tax - result.expected_tax)
        if result.tax_delta > result.po_total * self.tol["tax_pct"]:
            result.mismatch_reasons.append(
                f"Tax mismatch: charged ${result.invoice_tax:.2f}, expected ${result.expected_tax:.2f}"
            )

        # ── Shipping validation ────────────────────────────────────────────────
        result.shipping_delta = result.invoice_shipping - result.allowed_shipping
        if result.shipping_delta > self.tol["shipping_abs"]:
            result.mismatch_reasons.append(
                f"Shipping ${result.invoice_shipping:.2f} exceeds allowance ${result.allowed_shipping:.2f} "
                f"by ${result.shipping_delta:.2f}"
            )

        # ── Total delta ────────────────────────────────────────────────────────
        result.total_delta = abs(result.invoice_total - result.po_total)
        result.total_delta_pct = (
            result.total_delta / result.po_total if result.po_total else 0
        )

        # ── Verdict ────────────────────────────────────────────────────────────
        result.verdict = self._determine_verdict(result)
        return result

    def _compare_line_item(self, lr: LineItemResult, inv: dict, po: dict, result: MatchResult):
        lr.invoice_qty   = inv.get("qty", 0) or 0
        lr.po_qty        = po.get("qty", 0) or 0
        lr.invoice_price = inv.get("unit_price", 0) or 0
        lr.po_price      = po.get("unit_price", 0) or 0
        lr.invoice_amount = inv.get("amount", 0) or 0
        lr.po_amount      = lr.po_qty * lr.po_price

        # Quantity check
        if abs(lr.invoice_qty - lr.po_qty) > 0.001:
            lr.status = "qty_mismatch"
            lr.within_tolerance = False
            result.mismatch_reasons.append(
                f"{lr.sku}: qty mismatch — invoice {lr.invoice_qty} vs PO {lr.po_qty}"
            )
            return

        # Unit price check
        price_delta = abs(lr.invoice_price - lr.po_price)
        price_delta_pct = price_delta / lr.po_price if lr.po_price else 0
        lr.delta = lr.invoice_amount - lr.po_amount
        lr.delta_pct = abs(lr.delta) / lr.po_amount if lr.po_amount else 0

        if price_delta_pct > self.tol["unit_price_pct"]:
            lr.status = "price_mismatch"
            lr.invoice_price = lr.invoice_price
            lr.po_price = lr.po_price
            lr.within_tolerance = price_delta_pct <= self.tol["line_item_pct"]
            lr.notes = (
                f"Unit price ${lr.invoice_price:.2f} vs PO ${lr.po_price:.2f} "
                f"(+{price_delta_pct*100:.2f}%)"
            )
            if not lr.within_tolerance:
                result.mismatch_reasons.append(
                    f"{lr.sku}: unit price ${lr.invoice_price:.2f} vs PO ${lr.po_price:.2f}"
                )
        else:
            lr.status = "match"
            lr.within_tolerance = True
            lr.notes = "Match"

    def _determine_verdict(self, r: MatchResult) -> str:
        rounding_pct = self.tol["rounding_abs"] / max(r.po_total, 1)
        if not r.mismatch_reasons:
            return "approved"
        if r.total_delta_pct <= rounding_pct:
            return "adjusted"
        if r.mismatch_reasons:
            return "mismatch"
        return "approved"

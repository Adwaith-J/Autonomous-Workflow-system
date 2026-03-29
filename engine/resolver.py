"""
engine/resolver.py — Autonomous resolution engine.

Actions:
- Auto-approve    : within tolerance, no issues
- Auto-adjust     : minor rounding/price diff, apply credit note
- Auto-email      : vendor email for missing data / price clarification
- Auto-ticket     : create + track issue tickets
- Auto-close      : close tickets when resolved
"""

import uuid
from datetime import datetime
from engine.matcher import MatchResult, RESOLUTION_CONFIG


class ResolutionEngine:

    def __init__(self, db_session=None, email_tool=None, logger=None):
        self.db  = db_session
        self.email = email_tool
        self.logger = logger
        self.cfg = RESOLUTION_CONFIG

    def resolve(self, match: MatchResult, invoice: dict) -> dict:
        """
        Determine and execute the appropriate resolution action.
        Returns a resolution record.
        """
        resolution = {
            "invoice_id":    match.invoice_id,
            "verdict":       match.verdict,
            "actions":       [],
            "tickets":       [],
            "emails_sent":   [],
            "credit_notes":  [],
            "final_status":  "pending",
            "resolved_at":   datetime.utcnow().isoformat(),
        }

        if match.verdict == "approved":
            self._auto_approve(match, resolution)

        elif match.verdict == "adjusted":
            self._auto_adjust(match, resolution)

        elif match.verdict == "mismatch":
            self._handle_mismatch(match, invoice, resolution)

        elif match.verdict == "error":
            self._handle_error(match, resolution)

        return resolution

    # ── Private Actions ───────────────────────────────────────────────────────

    def _auto_approve(self, match: MatchResult, res: dict):
        delta_pct = match.total_delta_pct
        res["actions"].append(
            f"Auto-approved: total delta {delta_pct*100:.3f}% within {RESOLUTION_CONFIG['auto_approve_threshold']*100:.0f}% tolerance"
        )
        res["final_status"] = "approved"
        self._log("EXECUTE", f"[Resolver] AUTO-APPROVE — {match.invoice_id} | delta {delta_pct*100:.2f}%")

    def _auto_adjust(self, match: MatchResult, res: dict):
        delta = match.total_delta
        res["actions"].append(
            f"Auto-adjusted: delta ${delta:.2f} within rounding tolerance"
        )

        # Generate credit note if invoice overcharged
        if match.invoice_total > match.po_total:
            cn_id = f"CN-{uuid.uuid4().hex[:6].upper()}"
            res["credit_notes"].append({
                "id":     cn_id,
                "amount": round(match.invoice_total - match.po_total, 2),
                "reason": "Auto-adjustment: invoice exceeded PO by rounding delta",
            })
            res["actions"].append(f"Credit note {cn_id} generated for ${match.invoice_total - match.po_total:.2f}")

        res["final_status"] = "adjusted"
        self._log("EXECUTE", f"[Resolver] AUTO-ADJUST — {match.invoice_id} | adjusted ${delta:.2f}")

    def _handle_mismatch(self, match: MatchResult, invoice: dict, res: dict):
        res["final_status"] = "mismatch"

        for reason in match.mismatch_reasons:
            # Create ticket per mismatch
            ticket = self._create_ticket(match, reason)
            res["tickets"].append(ticket)
            res["actions"].append(f"Ticket {ticket['id']} created: {reason}")

        # Email vendor for clarification
        if self.cfg.get("require_vendor_email") and match.mismatch_reasons:
            email = self._send_vendor_email(match, invoice)
            res["emails_sent"].append(email)
            res["actions"].append(f"Vendor email sent to {invoice.get('vendor', 'vendor')} requesting clarification")

        # Generate credit note request if overcharged significantly
        if match.invoice_total > match.po_total and match.total_delta > 100:
            cn_id = f"CNR-{uuid.uuid4().hex[:6].upper()}"
            res["credit_notes"].append({
                "id":     cn_id,
                "amount": round(match.invoice_total - match.po_total, 2),
                "type":   "request",
                "reason": f"Invoice total ${match.invoice_total:.2f} exceeds PO ${match.po_total:.2f}",
            })
            res["actions"].append(f"Credit note request {cn_id} generated for ${match.invoice_total - match.po_total:.2f}")

        self._log("EXECUTE", f"[Resolver] MISMATCH — {match.invoice_id} | {len(match.mismatch_reasons)} issues, {len(res['tickets'])} tickets")

    def _handle_error(self, match: MatchResult, res: dict):
        res["final_status"] = "error"
        res["actions"].append("Processing error — queued for retry")
        self._log("EXECUTE", f"[Resolver] ERROR — {match.invoice_id}")

    def _create_ticket(self, match: MatchResult, reason: str) -> dict:
        tid = f"TKT-{uuid.uuid4().hex[:6].upper()}"
        priority = "HIGH" if match.total_delta_pct > 0.05 else "MEDIUM"
        return {
            "id":          tid,
            "invoice_id":  match.invoice_id,
            "title":       f"Invoice mismatch: {match.invoice_id} — {match.vendor}",
            "description": reason,
            "priority":    priority,
            "status":      "open",
            "created_at":  datetime.utcnow().isoformat(),
            "auto_closed": False,
        }

    def _send_vendor_email(self, match: MatchResult, invoice: dict) -> dict:
        subject = f"Invoice Clarification Required: {invoice.get('invoice_number', match.invoice_id)}"
        body = (
            f"Dear {match.vendor},\n\n"
            f"We have reviewed invoice {invoice.get('invoice_number', match.invoice_id)} "
            f"against Purchase Order {match.po_id}.\n\n"
            f"The following discrepancies require clarification:\n"
            + "\n".join(f"  - {r}" for r in match.mismatch_reasons)
            + f"\n\nPlease provide a revised invoice or supporting documentation "
            f"within 5 business days.\n\n"
            f"Invoice OS — Automated Reconciliation System"
        )
        return {
            "to":      f"accounts@{match.vendor.lower().replace(' ', '')}.com",
            "subject": subject,
            "body":    body,
            "sent_at": datetime.utcnow().isoformat(),
            "status":  "sent",
        }

    def auto_close_ticket(self, ticket_id: str, resolution: str) -> dict:
        """Auto-close a ticket when the underlying issue is resolved."""
        return {
            "ticket_id":   ticket_id,
            "status":      "auto_closed",
            "resolution":  resolution,
            "resolved_at": datetime.utcnow().isoformat(),
            "auto_closed": True,
        }

    def _log(self, phase: str, msg: str):
        if self.logger:
            self.logger.log(phase, msg)

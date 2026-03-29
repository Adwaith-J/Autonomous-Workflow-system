"""
main.py — InvoiceOS FastAPI application.

Endpoints:
  POST /api/run              — Execute workflow for a task/invoice
  GET  /api/invoices         — List all invoices
  GET  /api/invoices/{id}    — Get invoice detail
  GET  /api/tickets          — List all tickets
  GET  /api/metrics          — KPI metrics
  GET  /api/memory/stats     — Learning store stats
  POST /api/events/trigger   — Simulate new invoice event
  GET  /api/stream/{run_id}  — SSE stream for live logs
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Any
import asyncio, json, uuid, time
from datetime import datetime

from db.database import init_db, engine, Invoice, PurchaseOrder, Ticket, OutcomeLog
from sqlalchemy.orm import Session
from core.orchestrator import InvoiceOrchestrator

# ── App Setup ─────────────────────────────────────────────────────────────────
app = FastAPI(title="InvoiceOS", version="1.0.0", description="Autonomous Invoice Reconciliation")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Singleton orchestrator (holds memory/learning state)
orchestrator = InvoiceOrchestrator()

# In-memory run log store (for SSE streaming)
_run_logs: dict[str, list[dict]] = {}
_run_results: dict[str, dict] = {}


@app.on_event("startup")
async def startup():
    init_db()
    print("[InvoiceOS] Database initialized.")


# ── Request Models ────────────────────────────────────────────────────────────

class RunRequest(BaseModel):
    task:         str = "Process invoice and validate against PO"
    invoice_data: Optional[dict] = None
    demo_mode:    bool = True


class TriggerEvent(BaseModel):
    vendor:       str = "Acme Corp"
    invoice_type: str = "clean"   # clean|mismatch


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.post("/api/run")
async def run_workflow(req: RunRequest):
    """Execute the full 5-phase autonomy loop."""
    run_id = str(uuid.uuid4())[:8]
    result = await orchestrator.run(req.task, req.invoice_data)
    result["run_id"] = run_id
    _run_logs[run_id]    = result.get("logs", [])
    _run_results[run_id] = result

    # Persist to DB
    _persist_result(result)

    return {
        "run_id":       run_id,
        "status":       result.get("final_status"),
        "invoice_id":   result.get("invoice_id"),
        "vendor":       result.get("vendor"),
        "verdict":      result.get("match_result", {}).get("verdict"),
        "total_delta":  result.get("match_result", {}).get("total_delta"),
        "actions":      result.get("resolution", {}).get("actions", []),
        "tickets":      result.get("tickets", []),
        "emails_sent":  result.get("emails_sent", []),
        "credit_notes": result.get("credit_notes", []),
        "precision":    result.get("precision"),
        "recall":       result.get("recall"),
        "processing_ms":result.get("processing_ms"),
        "logs":         result.get("logs", []),
    }


@app.get("/api/run/{run_id}/stream")
async def stream_logs(run_id: str):
    """SSE stream for live workflow logs."""
    async def event_gen():
        logs = _run_logs.get(run_id, [])
        for entry in logs:
            data = json.dumps(entry)
            yield f"data: {data}\n\n"
            await asyncio.sleep(0.12)
        yield "data: {\"phase\":\"DONE\",\"msg\":\"Stream complete\"}\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")


@app.get("/api/invoices")
def list_invoices():
    with Session(engine) as session:
        invoices = session.query(Invoice).order_by(Invoice.created_at.desc()).all()
        return [_invoice_to_dict(inv) for inv in invoices]


@app.get("/api/invoices/{invoice_id}")
def get_invoice(invoice_id: str):
    with Session(engine) as session:
        inv = session.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not inv:
            raise HTTPException(404, f"Invoice {invoice_id} not found")
        return _invoice_to_dict(inv)


@app.get("/api/tickets")
def list_tickets():
    with Session(engine) as session:
        tickets = session.query(Ticket).order_by(Ticket.created_at.desc()).all()
        return [_ticket_to_dict(t) for t in tickets]


@app.get("/api/metrics")
def get_metrics():
    with Session(engine) as session:
        invoices = session.query(Invoice).all()
        total    = len(invoices)
        approved = sum(1 for i in invoices if i.status == "approved")
        adjusted = sum(1 for i in invoices if i.status == "adjusted")
        mismatch = sum(1 for i in invoices if i.status == "mismatch")
        pending  = sum(1 for i in invoices if i.status == "pending")
        tickets  = session.query(Ticket).count()
        auto_closed = session.query(Ticket).filter(Ticket.auto_closed == True).count()

        return {
            "total_invoices":     total,
            "auto_approved":      approved,
            "auto_adjusted":      adjusted,
            "mismatches":         mismatch,
            "pending":            pending,
            "auto_approval_rate": round((approved + adjusted) / max(total, 1), 3),
            "total_tickets":      tickets,
            "auto_closed_tickets":auto_closed,
            "false_positive_rate":0.04,   # Simulated metric
            "avg_processing_ms":  420,    # Simulated
            "learning_store":     orchestrator.learning.stats(),
        }


@app.post("/api/events/trigger")
async def trigger_invoice_event(event: TriggerEvent):
    """Simulate a new invoice arriving (IMAP/webhook trigger)."""
    task = f"Process invoice from {event.vendor}"
    if event.invoice_type == "mismatch":
        task += " — validate line items and flag mismatches"

    result = await orchestrator.run(task)
    _persist_result(result)
    return {
        "event_id":  str(uuid.uuid4())[:8],
        "status":    "triggered",
        "vendor":    event.vendor,
        "outcome":   result.get("final_status"),
        "run_id":    result.get("run_id"),
    }


@app.get("/api/memory/stats")
def memory_stats():
    return orchestrator.learning.stats()


@app.get("/api/health")
def health():
    return {"status": "ok", "ts": datetime.utcnow().isoformat()}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _invoice_to_dict(inv: Invoice) -> dict:
    return {
        "id":             inv.id,
        "vendor":         inv.vendor,
        "invoice_number": inv.invoice_number,
        "invoice_date":   inv.invoice_date,
        "po_ref":         inv.po_ref,
        "total":          inv.total,
        "tax":            inv.tax,
        "shipping":       inv.shipping,
        "status":         inv.status,
        "confidence":     inv.confidence,
        "line_items":     inv.line_items or [],
        "actions_taken":  inv.actions_taken or [],
        "created_at":     inv.created_at.isoformat() if inv.created_at else None,
    }


def _ticket_to_dict(t: Ticket) -> dict:
    return {
        "id":          t.id,
        "invoice_id":  t.invoice_id,
        "title":       t.title,
        "description": t.description,
        "priority":    t.priority,
        "status":      t.status,
        "resolution":  t.resolution,
        "auto_closed": t.auto_closed,
        "created_at":  t.created_at.isoformat() if t.created_at else None,
        "resolved_at": t.resolved_at.isoformat() if t.resolved_at else None,
    }


def _persist_result(result: dict):
    """Persist run result to DB (best-effort)."""
    try:
        with Session(engine) as session:
            for ticket in result.get("tickets", []):
                t = Ticket(
                    id          = ticket["id"],
                    invoice_id  = result.get("invoice_id", ""),
                    title       = ticket["title"],
                    description = ticket["description"],
                    priority    = ticket["priority"],
                    status      = ticket["status"],
                )
                session.merge(t)
            session.commit()
    except Exception:
        pass  # Non-blocking

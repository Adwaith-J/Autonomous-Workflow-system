# InvoiceOS — Autonomous Invoice Reconciliation System

## Quick Start

### Backend
```bash
cd invoice_os
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend
```bash
npm create vite@latest frontend -- --template react
cd frontend && npm install tailwindcss
# Copy InvoiceOS-dashboard.jsx to src/App.jsx
npm run dev
```

### Test API
```bash
curl -X POST http://localhost:8000/api/run \
  -H "Content-Type: application/json" \
  -d '{"task": "Validate FastLog Inc invoice FL-2024-412 and flag mismatches"}'
```

## Architecture
- FastAPI backend with SQLite
- Rule-based matching engine (2-way PO matching)
- Autonomous resolution (approve/adjust/ticket/email)
- Idempotency keys for deduplication
- Retry with exponential backoff
- In-memory learning store

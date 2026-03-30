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


## ⚙️ How to Run Locally

Follow these steps to run InvoiceOS on your machine:

---

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/invoice-os.git
cd invoice-os
```

---

### 2. Setup Backend (FastAPI)

```bash
# Create virtual environment
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

### 3. Configure Environment Variables

Create a `.env` file in the root folder and add:

```
DATABASE_URL=sqlite:///./invoice.db
APP_NAME=InvoiceOS
```

---

### 4. Run Backend Server

```bash
uvicorn main:app --reload
```

Backend will run at:

```
http://127.0.0.1:8000
```

---

### 5. Setup Frontend (React)

```bash
cd frontend
npm install
npm run dev
```

Frontend will run at:

```
http://localhost:5173
```

---

### 6. Access the Application

* Frontend UI: http://localhost:5173
* Backend API Docs: http://127.0.0.1:8000/docs

---

## 🚀 Notes

* Make sure Python (3.10+) and Node.js (LTS) are installed
* Backend must be running before frontend interacts with it
* This is a local MVP (no external APIs required)

---

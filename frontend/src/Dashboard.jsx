import { useState, useEffect, useRef, useCallback } from "react";

const STYLE = `
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --bg:        #0B0F19;
    --bg2:       #111827;
    --bg3:       #1F2937;
    --bg4:       #374151;
    --border:    #1F2937;
    --border2:   #374151;
    --text:      #F9FAFB;
    --text2:     #9CA3AF;
    --text3:     #6B7280;
    --blue:      #3B82F6;
    --blue-dim:  #1D4ED820;
    --blue-bg:   #1E3A5F;
    --green:     #10B981;
    --green-dim: #065F4620;
    --green-bg:  #064E3B;
    --amber:     #F59E0B;
    --amber-dim: #78350F20;
    --amber-bg:  #451A03;
    --red:       #EF4444;
    --red-dim:   #7F1D1D20;
    --red-bg:    #450A0A;
    --purple:    #8B5CF6;
    --purple-dim:#4C1D9520;
    --mono: 'JetBrains Mono', monospace;
    --sans: 'Inter', sans-serif;
  }
  body { background: var(--bg); color: var(--text); font-family: var(--sans); overflow: hidden; }
  ::-webkit-scrollbar { width: 4px; height: 4px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 2px; }
  @keyframes fadeIn { from{opacity:0;transform:translateY(4px)} to{opacity:1;transform:translateY(0)} }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.5} }
  @keyframes spin { from{transform:rotate(0deg)} to{transform:rotate(360deg)} }
  @keyframes slideIn { from{opacity:0;transform:translateX(-8px)} to{opacity:1;transform:translateX(0)} }
  @keyframes countUp { from{opacity:0;transform:scale(0.9)} to{opacity:1;transform:scale(1)} }
  @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }
`;

// ─── Mock Data ─────────────────────────────────────────────────────────────
const MOCK_INVOICES = [
  { id:"INV-001", vendor:"Acme Corp",     invoice_number:"ACM-2024-001", invoice_date:"2024-01-15", po_ref:"PO-881", total:12500.00, status:"approved", confidence:0.97, actions_taken:["Auto-approved: total within 2% tolerance","Line items matched PO-881 exactly"] },
  { id:"INV-002", vendor:"GlobalSupply",  invoice_number:"GS-2024-089",  invoice_date:"2024-01-16", po_ref:"PO-882", total:8750.50,  status:"approved", confidence:0.95, actions_taken:["Auto-approved: all line items match PO within tolerance"] },
  { id:"INV-003", vendor:"FastLog Inc",   invoice_number:"FL-2024-412",  invoice_date:"2024-01-18", po_ref:"PO-884", total:15300.00, status:"mismatch", confidence:0.91, actions_taken:["Mismatch: STORAGE-1 unit price $575 vs PO $560","Ticket TKT-A3B2C1 created","Vendor email sent"] },
  { id:"INV-004", vendor:"TechParts Ltd", invoice_number:"TP-2024-077",  invoice_date:"2024-01-17", po_ref:"PO-883", total:3556.00,  status:"adjusted", confidence:0.88, actions_taken:["Minor rounding delta $0.20 on SENSOR-T","Auto-adjusted: within 0.5% tolerance"] },
  { id:"INV-005", vendor:"Acme Corp",     invoice_number:"ACM-2024-002", invoice_date:"2024-01-19", po_ref:"PO-881", total:null,     status:"pending",  confidence:0.62, actions_taken:["Low confidence (62%): flagged for manual review"] },
];

const MOCK_TICKETS = [
  { id:"TKT-A3B2C1", invoice_id:"INV-003", title:"Price discrepancy: STORAGE-1 (FastLog Inc)",         description:"Invoice $575/unit vs PO $560/unit. Delta: +$75.00 on 5 units.", priority:"HIGH",   status:"open",       auto_closed:false, created_at:"2024-01-18T14:22:00" },
  { id:"TKT-D4E5F6", invoice_id:"INV-003", title:"Vendor clarification requested: FL-2024-412",        description:"Automated email sent requesting price justification. Awaiting response.",            priority:"MEDIUM", status:"in_progress",auto_closed:false, created_at:"2024-01-18T14:23:00" },
  { id:"TKT-G7H8I9", invoice_id:"INV-004", title:"Auto-adjusted: TechParts rounding delta",            description:"$0.20 rounding on SENSOR-T. Auto-approved within 0.5% tolerance.",                 priority:"LOW",    status:"auto_closed",auto_closed:true,  created_at:"2024-01-17T09:15:00", resolved_at:"2024-01-17T09:15:01" },
  { id:"TKT-J1K2L3", invoice_id:"INV-005", title:"Low confidence extraction: ACM-2024-002",            description:"PDF confidence 62%. Manual verification required before processing.",               priority:"MEDIUM", status:"open",       auto_closed:false, created_at:"2024-01-19T11:00:00" },
];

const MOCK_METRICS = {
  total_invoices: 5, auto_approved: 2, auto_adjusted: 1,
  mismatches: 1, pending: 1, auto_approval_rate: 0.60,
  total_tickets: 4, auto_closed_tickets: 1, avg_processing_ms: 420,
};

const PHASES = [
  { id:"THINK",   label:"Think",   color:"#06B6D4", desc:"Analyze task, check memory" },
  { id:"PLAN",    label:"Plan",    color:"#3B82F6", desc:"Extract invoice, load PO" },
  { id:"EXECUTE", label:"Execute", color:"#10B981", desc:"Match, compare, resolve" },
  { id:"REVIEW",  label:"Review",  color:"#8B5CF6", desc:"Score outcome, audit" },
  { id:"UPDATE",  label:"Update",  color:"#F59E0B", desc:"Persist to memory, learn" },
];

const NAV_ITEMS = [
  { id:"dashboard", icon:"▦",  label:"Dashboard"  },
  { id:"workflow",  icon:"◈",  label:"Workflow"   },
  { id:"invoices",  icon:"◻",  label:"Invoices"   },
  { id:"tickets",   icon:"⊕",  label:"Tickets"    },
  { id:"analytics", icon:"◎",  label:"Analytics"  },
];

// ─── Workflow simulation logs ───────────────────────────────────────────────
function buildSimLogs(task, mode) {
  const isMismatch = mode === "mismatch";
  return [
    { phase:"THINK",   msg:`Analyzing task: "${task}"` },
    { phase:"THINK",   msg:"Memory check: 2 similar runs found. Avg approval rate: 75%" },
    { phase:"THINK",   msg:`Invoice type detected: ${isMismatch ? "potentially mismatched" : "clean"}` },
    { phase:"PLAN",    msg:"Compiling invoice reconciliation workflow..." },
    { phase:"PLAN",    msg:`Invoice extracted: ${isMismatch ? "FL-2024-412 | FastLog Inc | $15,300.00" : "ACM-2024-001 | Acme Corp | $12,500.00"} | Confidence: ${isMismatch ? "91%" : "97%"}` },
    { phase:"PLAN",    msg:`Idempotency check: key ${isMismatch ? "a3b2c1d4e5" : "f1e2d3c4b5"}... — new invoice, proceeding` },
    { phase:"PLAN",    msg:`PO loaded: ${isMismatch ? "PO-884 | Approved: $14,800 | Tax: 10% | Shipping: $500 allowance" : "PO-881 | Approved: $12,500 | Tax: 8% | Shipping: $150 allowance"}` },
    { phase:"PLAN",    msg:"Workflow: EXTRACT → MATCH → RESOLVE → TICKET → NOTIFY" },
    { phase:"EXECUTE", msg:"Beginning line-item matching..." },
    ...(isMismatch ? [
      { phase:"EXECUTE", msg:"  ✓ LOG-SRV      | match                | Invoice $4,500.00 vs PO $4,500.00 | Δ $0.00" },
      { phase:"EXECUTE", msg:"  ⚠ STORAGE-1    | price_mismatch       | Invoice $575.00 vs PO $560.00 | Δ +$75.00" },
      { phase:"EXECUTE", msg:"  ✓ MAINT-ANN    | match                | Invoice $2,400.00 vs PO $2,400.00 | Δ $0.00" },
      { phase:"EXECUTE", msg:"Tax check: invoice $1,363.64 vs expected $1,363.64 | Δ $0.00" },
      { phase:"EXECUTE", msg:"Shipping: invoice $300.00 vs allowance $500.00 — within bounds" },
      { phase:"EXECUTE", msg:"Total delta: $500.00 (3.378%) | Verdict: MISMATCH" },
      { phase:"EXECUTE", msg:"  ⚠ Mismatch: STORAGE-1: unit price $575.00 vs PO $560.00" },
      { phase:"EXECUTE", msg:"  → Ticket TKT-A3B2C1 created: Invoice mismatch — price_mismatch on STORAGE-1" },
      { phase:"EXECUTE", msg:"  → Vendor email sent to accounts@fastloginc.com requesting clarification" },
      { phase:"EXECUTE", msg:"  → Credit note request CNR-B3C4D5 generated for $500.00" },
    ] : [
      { phase:"EXECUTE", msg:"  ✓ WIDGET-A     | match                | Invoice $85.00 vs PO $85.00 | Δ $0.00" },
      { phase:"EXECUTE", msg:"  ✓ WIDGET-B     | match                | Invoice $110.00 vs PO $110.00 | Δ $0.00" },
      { phase:"EXECUTE", msg:"  ✓ SUPPORT-1    | match                | Invoice $450.00 vs PO $450.00 | Δ $0.00" },
      { phase:"EXECUTE", msg:"Tax check: invoice $925.93 vs expected $925.93 | Δ $0.00" },
      { phase:"EXECUTE", msg:"Shipping: invoice $0.00 vs allowance $150.00 — within bounds" },
      { phase:"EXECUTE", msg:"Total delta: $0.00 (0.000%) | Verdict: APPROVED" },
      { phase:"EXECUTE", msg:"  → Auto-approved: total delta 0.000% within 2% tolerance" },
    ]),
    { phase:"REVIEW",  msg:"Evaluating reconciliation outcome..." },
    { phase:"REVIEW",  msg:`Final Status: ${isMismatch ? "MISMATCH" : "APPROVED"}` },
    { phase:"REVIEW",  msg:`Tickets created: ${isMismatch ? 1 : 0} | Emails sent: ${isMismatch ? 1 : 0} | Credit notes: ${isMismatch ? 1 : 0}` },
    { phase:"REVIEW",  msg:`Precision: 100% | Recall: 100% | Confidence: ${isMismatch ? "91%" : "97%"}` },
    { phase:"UPDATE",  msg:"Persisting to memory and updating learning model..." },
    { phase:"UPDATE",  msg:`Learning: vendor ${isMismatch ? "FastLog Inc has pattern of mismatches — stricter review flagged" : "Acme Corp consistently accurate — confidence boosted"}` },
    { phase:"UPDATE",  msg:"Memory updated. Run complete." },
  ];
}

// ─── Helper Components ─────────────────────────────────────────────────────
function StatusBadge({ status }) {
  const cfg = {
    approved:    { bg:"#065F46", text:"#6EE7B7", label:"Approved" },
    adjusted:    { bg:"#1E3A5F", text:"#93C5FD", label:"Adjusted" },
    mismatch:    { bg:"#450A0A", text:"#FCA5A5", label:"Mismatch" },
    pending:     { bg:"#3B2F00", text:"#FCD34D", label:"Pending"  },
    processing:  { bg:"#1A1033", text:"#C4B5FD", label:"Processing"},
    open:        { bg:"#450A0A", text:"#FCA5A5", label:"Open"     },
    in_progress: { bg:"#1E3A5F", text:"#93C5FD", label:"In Progress"},
    auto_closed: { bg:"#065F46", text:"#6EE7B7", label:"Auto-closed"},
  }[status] || { bg:"var(--bg3)", text:"var(--text2)", label: status };
  return (
    <span style={{
      display:"inline-block", padding:"2px 8px", borderRadius:4,
      fontSize:11, fontWeight:600, letterSpacing:"0.04em",
      background:cfg.bg, color:cfg.text,
    }}>{cfg.label}</span>
  );
}

function PriorityDot({ priority }) {
  const colors = { HIGH:"#EF4444", MEDIUM:"#F59E0B", LOW:"#10B981", CRITICAL:"#8B5CF6" };
  return <span style={{ display:"inline-block", width:8, height:8, borderRadius:"50%", background:colors[priority]||"#6B7280", flexShrink:0 }} />;
}

function KPICard({ label, value, sub, color, icon, animate }) {
  const [disp, setDisp] = useState(0);
  useEffect(() => {
    if (!animate || typeof value !== "number") return;
    let start = 0;
    const end = typeof value === "number" ? value : 0;
    const step = Math.max(1, Math.floor(end / 20));
    const t = setInterval(() => {
      start = Math.min(start + step, end);
      setDisp(start);
      if (start >= end) clearInterval(t);
    }, 40);
    return () => clearInterval(t);
  }, [value, animate]);

  const displayVal = animate && typeof value === "number" ? disp : value;

  return (
    <div style={{
      background:"var(--bg2)", border:"1px solid var(--border2)", borderRadius:12,
      padding:"16px 20px", display:"flex", flexDirection:"column", gap:6,
      borderLeft:`3px solid ${color}`, animation:"fadeIn 0.4s ease",
    }}>
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center" }}>
        <span style={{ fontSize:11, color:"var(--text3)", fontWeight:500, letterSpacing:"0.06em", textTransform:"uppercase" }}>{label}</span>
        <span style={{ fontSize:18, opacity:0.7 }}>{icon}</span>
      </div>
      <div style={{ fontSize:28, fontWeight:700, color }}>
        {typeof displayVal === "number" && !String(value).includes("%") ? displayVal.toLocaleString() : displayVal}
      </div>
      {sub && <div style={{ fontSize:12, color:"var(--text3)" }}>{sub}</div>}
    </div>
  );
}

// ─── Sidebar ───────────────────────────────────────────────────────────────
function Sidebar({ view, setView }) {
  return (
    <div style={{
      width:220, background:"var(--bg2)", borderRight:"1px solid var(--border)",
      display:"flex", flexDirection:"column", height:"100vh", flexShrink:0,
    }}>
      {/* Logo */}
      <div style={{ padding:"20px 20px 16px", borderBottom:"1px solid var(--border)" }}>
        <div style={{ display:"flex", alignItems:"center", gap:10 }}>
          <div style={{ width:32, height:32, borderRadius:8, background:"linear-gradient(135deg, #3B82F6, #8B5CF6)", display:"flex", alignItems:"center", justifyContent:"center", fontSize:14, fontWeight:700, color:"#fff" }}>IV</div>
          <div>
            <div style={{ fontSize:13, fontWeight:700, color:"var(--text)" }}>InvoiceOS</div>
            <div style={{ fontSize:10, color:"var(--text3)", letterSpacing:"0.06em" }}>AUTONOMOUS · MVP</div>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav style={{ padding:"12px 10px", flex:1 }}>
        {NAV_ITEMS.map(item => (
          <button key={item.id} onClick={() => setView(item.id)}
            style={{
              width:"100%", display:"flex", alignItems:"center", gap:10,
              padding:"9px 12px", marginBottom:2, border:"none", cursor:"pointer",
              borderRadius:8, textAlign:"left", fontFamily:"var(--sans)", fontSize:13,
              background: view===item.id ? "var(--blue-dim)" : "transparent",
              color: view===item.id ? "var(--blue)" : "var(--text2)",
              fontWeight: view===item.id ? 600 : 400,
              transition:"all 0.15s",
            }}>
            <span style={{ fontSize:15, width:20, textAlign:"center" }}>{item.icon}</span>
            {item.label}
          </button>
        ))}
      </nav>

      {/* Footer */}
      <div style={{ padding:"12px 16px", borderTop:"1px solid var(--border)", fontSize:11, color:"var(--text3)" }}>
        <div style={{ display:"flex", alignItems:"center", gap:6 }}>
          <span style={{ width:6, height:6, borderRadius:"50%", background:"#10B981", display:"inline-block", flexShrink:0 }} />
          System operational
        </div>
        <div style={{ marginTop:4 }}>v1.0.0-mvp · LLM-free</div>
      </div>
    </div>
  );
}

// ─── Top Nav ───────────────────────────────────────────────────────────────
function TopNav({ view, metrics }) {
  const titles = { dashboard:"Dashboard", workflow:"Workflow Execution", invoices:"Invoice Registry", tickets:"Issue Tickets", analytics:"Analytics" };
  return (
    <div style={{
      height:56, borderBottom:"1px solid var(--border)", display:"flex",
      alignItems:"center", justifyContent:"space-between", padding:"0 24px",
      background:"var(--bg2)", flexShrink:0,
    }}>
      <div style={{ fontSize:16, fontWeight:600 }}>{titles[view]}</div>
      <div style={{ display:"flex", gap:16, alignItems:"center" }}>
        <div style={{ display:"flex", gap:6, alignItems:"center" }}>
          <span style={{ fontSize:11, color:"var(--text3)" }}>Auto-approval rate</span>
          <span style={{ fontSize:12, fontWeight:700, color:"#10B981" }}>{Math.round((metrics.auto_approval_rate||0.6)*100)}%</span>
        </div>
        <div style={{ width:1, height:20, background:"var(--border2)" }} />
        <div style={{ fontSize:11, color:"var(--text3)" }}>
          {new Date().toLocaleDateString("en-US",{month:"short",day:"numeric",year:"numeric"})}
        </div>
      </div>
    </div>
  );
}

// ─── Dashboard View ────────────────────────────────────────────────────────
function DashboardView({ metrics, invoices, tickets }) {
  const kpis = [
    { label:"Auto-Approved",  value:metrics.auto_approved,                          sub:"invoices this week", color:"#10B981", icon:"✓" },
    { label:"Mismatches",     value:metrics.mismatches,                             sub:"require attention",  color:"#EF4444", icon:"⚠" },
    { label:"Tickets Created",value:metrics.total_tickets,                          sub:`${metrics.auto_closed_tickets} auto-closed`, color:"#8B5CF6", icon:"⊕" },
    { label:"Success Rate",   value:`${Math.round(metrics.auto_approval_rate*100)}%`, sub:"auto-resolution",  color:"#3B82F6", icon:"◎" },
  ];

  const recent = invoices.slice(0,5);

  return (
    <div style={{ display:"flex", flexDirection:"column", gap:20 }}>
      {/* KPI Cards */}
      <div style={{ display:"grid", gridTemplateColumns:"repeat(4, 1fr)", gap:12 }}>
        {kpis.map(k => <KPICard key={k.label} {...k} animate={true} />)}
      </div>

      <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:16 }}>
        {/* Recent Activity */}
        <div style={{ background:"var(--bg2)", border:"1px solid var(--border2)", borderRadius:12, overflow:"hidden" }}>
          <div style={{ padding:"14px 18px", borderBottom:"1px solid var(--border)", display:"flex", justifyContent:"space-between" }}>
            <span style={{ fontSize:13, fontWeight:600 }}>Recent Invoices</span>
            <span style={{ fontSize:11, color:"var(--text3)" }}>{invoices.length} total</span>
          </div>
          <div>
            {recent.map((inv, i) => (
              <div key={inv.id} style={{
                display:"flex", alignItems:"center", gap:12, padding:"10px 18px",
                borderBottom: i < recent.length-1 ? "1px solid var(--border)" : "none",
                animation:`slideIn 0.3s ease ${i*0.08}s both`,
              }}>
                <div style={{ flex:1, minWidth:0 }}>
                  <div style={{ fontSize:12, fontWeight:600, color:"var(--text)", overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>{inv.vendor}</div>
                  <div style={{ fontSize:11, color:"var(--text3)" }}>{inv.invoice_number} · {inv.po_ref}</div>
                </div>
                <div style={{ textAlign:"right", flexShrink:0 }}>
                  {inv.total ? <div style={{ fontSize:12, fontWeight:600, color:"var(--text)" }}>${inv.total.toLocaleString()}</div> : <div style={{ fontSize:11, color:"var(--text3)" }}>—</div>}
                </div>
                <StatusBadge status={inv.status} />
              </div>
            ))}
          </div>
        </div>

        {/* Autonomy Loop Visualization */}
        <div style={{ background:"var(--bg2)", border:"1px solid var(--border2)", borderRadius:12, overflow:"hidden" }}>
          <div style={{ padding:"14px 18px", borderBottom:"1px solid var(--border)" }}>
            <span style={{ fontSize:13, fontWeight:600 }}>Autonomy Loop</span>
          </div>
          <div style={{ padding:20, display:"flex", flexDirection:"column", gap:8 }}>
            {PHASES.map((phase, i) => (
              <div key={phase.id} style={{
                display:"flex", alignItems:"center", gap:12,
                padding:"10px 14px", borderRadius:8,
                background:`${phase.color}12`,
                border:`1px solid ${phase.color}30`,
                animation:`fadeIn 0.3s ease ${i*0.1}s both`,
              }}>
                <div style={{ width:28, height:28, borderRadius:"50%", background:phase.color, display:"flex", alignItems:"center", justifyContent:"center", fontSize:11, fontWeight:700, color:"#000", flexShrink:0 }}>
                  {i+1}
                </div>
                <div style={{ flex:1 }}>
                  <div style={{ fontSize:12, fontWeight:700, color:phase.color, letterSpacing:"0.05em" }}>{phase.label.toUpperCase()}</div>
                  <div style={{ fontSize:11, color:"var(--text3)" }}>{phase.desc}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Workflow View ─────────────────────────────────────────────────────────
function WorkflowView({ invoices, tickets, setInvoices, setTickets, metrics, setMetrics }) {
  const [task, setTask]             = useState("Validate FastLog Inc invoice FL-2024-412 against PO-884 and flag mismatches");
  const [running, setRunning]       = useState(false);
  const [logs, setLogs]             = useState([]);
  const [currentPhase, setCurrentPhase] = useState(null);
  const [phaseIdx, setPhaseIdx]     = useState(-1);
  const [result, setResult]         = useState(null);
  const logRef = useRef(null);

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [logs]);

  const runWorkflow = async () => {
    if (running || !task.trim()) return;
    setRunning(true); setLogs([]); setResult(null); setPhaseIdx(-1); setCurrentPhase(null);

      try {
    const res = await fetch("http://127.0.0.1:8000/api/events/trigger", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        event_type: "invoice_received",
        data: {
          task: task,
          invoice_id: "INV001"
        }
      }),
    });

    const data = await res.json();
    const steps = [
      { phase: "THINK", msg: "Invoice event received" },
      { phase: "PLAN", msg: "Checking for duplicate processing..." },
      { phase: "EXECUTE", msg: "Validating invoice ID" },
      { phase: "REVIEW", msg: `Outcome: ${data.outcome}` },
      { phase: "UPDATE", msg: `Run ID: ${data.run_id}` }
    ];

    for (let i = 0; i < steps.length; i++) {
      const step = steps[i];
      const ts = new Date().toISOString().slice(11, 23);

      // update phase indicator
      setCurrentPhase(step.phase);

    setLogs(prev => [
      ...prev.slice(-20), // keep last 20 logs
      { ts, phase: "THINK", msg: "Invoice event received" },
  { ts, phase: "PLAN", msg: "Checking for duplicate processing..." },
  { ts, phase: "EXECUTE", msg: "Validating invoice ID" },
  { ts, phase: "REVIEW", msg: `Outcome: ${data.outcome}` },
  { ts, phase: "UPDATE", msg: `Run ID: ${data.run_id}` }
    ]);
    await new Promise(r => setTimeout(r, 400));
}
  } catch (err) {
    console.error(err);

    setLogs(prev => [
      ...prev,
      {
        ts: new Date().toISOString().slice(11,23),
        phase: "SYSTEM",
        msg: "Error connecting to backend"
      }
    ]);
  }

  setRunning(false);
};

  const phaseColors = { THINK:"#06B6D4", PLAN:"#3B82F6", EXECUTE:"#10B981", REVIEW:"#8B5CF6", UPDATE:"#F59E0B", SYSTEM:"#6B7280" };

  return (
    <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:16, height:"calc(100vh - 56px - 40px)" }}>
      {/* Left: Input + Phase Stepper */}
      <div style={{ display:"flex", flexDirection:"column", gap:12 }}>
        {/* Task input */}
        <div style={{ background:"var(--bg2)", border:"1px solid var(--border2)", borderRadius:12, padding:16 }}>
          <div style={{ fontSize:12, color:"var(--text3)", marginBottom:8, letterSpacing:"0.06em", textTransform:"uppercase" }}>Task Input</div>
          <textarea value={task} onChange={e=>setTask(e.target.value)} disabled={running} rows={3}
            style={{
              width:"100%", background:"var(--bg3)", border:"1px solid var(--border2)", borderRadius:8,
              color:"var(--text)", fontFamily:"var(--mono)", fontSize:12, padding:"10px 12px",
              resize:"none", outline:"none", marginBottom:10, lineHeight:1.5,
            }} />
          <div style={{ display:"flex", gap:8, flexWrap:"wrap", marginBottom:10 }}>
            {["Validate FastLog mismatch invoice", "Process clean Acme Corp invoice", "Auto-reconcile TechParts PO-883"].map(t => (
              <button key={t} onClick={() => setTask(t)} disabled={running}
                style={{ padding:"4px 10px", fontSize:11, background:"transparent", border:"1px solid var(--border2)", borderRadius:6, color:"var(--text3)", cursor:"pointer", fontFamily:"var(--sans)" }}>{t}</button>
            ))}
          </div>
          <button onClick={runWorkflow} disabled={running || !task.trim()}
            style={{
              width:"100%", padding:"10px 0", background:running?"transparent":"var(--blue)",
              border:`1px solid ${running?"var(--blue)":"var(--blue)"}`,
              color:running?"var(--blue)":"#fff", borderRadius:8, cursor:running?"not-allowed":"pointer",
              fontFamily:"var(--sans)", fontSize:13, fontWeight:600, display:"flex", alignItems:"center", justifyContent:"center", gap:8,
              animation:running?"pulse 1.5s ease infinite":"none",
            }}>
            {running ? <><span style={{animation:"spin 0.8s linear infinite",display:"inline-block"}}>◌</span> Processing...</> : "▶ Run Workflow"}
          </button>
        </div>

        {/* Phase stepper */}
        <div style={{ background:"var(--bg2)", border:"1px solid var(--border2)", borderRadius:12, padding:16 }}>
          <div style={{ fontSize:12, color:"var(--text3)", marginBottom:12, letterSpacing:"0.06em", textTransform:"uppercase" }}>Autonomy Loop</div>
          <div style={{ display:"flex", alignItems:"center", gap:0 }}>
            {PHASES.map((phase, i) => {
              const done    = phaseIdx > i;
              const active  = currentPhase === phase.id;
              const waiting = !done && !active;
              return (
                <div key={phase.id} style={{ display:"flex", alignItems:"center", flex:1 }}>
                  <div style={{ flex:1, display:"flex", flexDirection:"column", alignItems:"center", gap:4 }}>
                    <div style={{
                      width:32, height:32, borderRadius:"50%", display:"flex", alignItems:"center", justifyContent:"center",
                      fontSize:11, fontWeight:700,
                      background: done ? phase.color : active ? `${phase.color}25` : "var(--bg3)",
                      border:`2px solid ${done||active ? phase.color : "var(--border2)"}`,
                      color: done ? "#000" : active ? phase.color : "var(--text3)",
                      transition:"all 0.3s",
                      animation: active ? "pulse 1s ease infinite" : "none",
                    }}>{done ? "✓" : i+1}</div>
                    <span style={{ fontSize:9, fontWeight:600, letterSpacing:"0.05em", color:done||active?phase.color:"var(--text3)", transition:"color 0.3s" }}>{phase.label.toUpperCase()}</span>
                  </div>
                  {i < PHASES.length-1 && <div style={{ height:2, width:16, background:done?phase.color:"var(--border2)", transition:"background 0.4s", marginBottom:14 }} />}
                </div>
              );
            })}
          </div>
        </div>

        {/* Result panel */}
        {result && (
          <div style={{
            background: result.status==="approved" ? "#065F4625" : result.status==="mismatch" ? "#450A0A25" : "var(--bg2)",
            border:`1px solid ${result.status==="approved" ? "#10B981" : result.status==="mismatch" ? "#EF4444" : "var(--border2)"}40`,
            borderRadius:12, padding:16, animation:"fadeIn 0.4s ease",
          }}>
            <div style={{ fontSize:12, color:"var(--text3)", marginBottom:10, letterSpacing:"0.06em", textTransform:"uppercase" }}>Result</div>
            <div style={{ display:"grid", gridTemplateColumns:"repeat(2, 1fr)", gap:8 }}>
              {[
                { label:"Verdict", val:<StatusBadge status={result.status} /> },
                { label:"Delta",   val:<span style={{ color: result.delta.startsWith("$0") ? "#10B981" : "#EF4444", fontWeight:600, fontSize:12 }}>{result.delta}</span> },
                { label:"Tickets", val: result.tickets },
                { label:"Emails",  val: result.emails },
              ].map(item => (
                <div key={item.label} style={{ background:"var(--bg3)", borderRadius:6, padding:"8px 12px" }}>
                  <div style={{ fontSize:10, color:"var(--text3)", marginBottom:3 }}>{item.label}</div>
                  <div style={{ fontSize:13, fontWeight:600 }}>{item.val}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Right: Live logs */}
      <div style={{ background:"var(--bg2)", border:"1px solid var(--border2)", borderRadius:12, display:"flex", flexDirection:"column", overflow:"hidden" }}>
        <div style={{ padding:"12px 16px", borderBottom:"1px solid var(--border)", display:"flex", justifyContent:"space-between", alignItems:"center" }}>
          <span style={{ fontSize:12, fontWeight:600, fontFamily:"var(--mono)", color:"var(--text3)" }}>AUTONOMY TRACE LOG</span>
          <span style={{ fontSize:11, color:"var(--text3)" }}>{logs.length} entries</span>
        </div>
        <div ref={logRef} style={{ flex:1, overflowY:"auto", padding:"10px 12px", fontFamily:"var(--mono)", fontSize:11, lineHeight:1.7 }}>
          {logs.length === 0 ? (
            <span style={{ color:"var(--text3)" }}>// Awaiting workflow execution...</span>
          ) : logs.map((e, i) => (
            <div key={i} style={{ display:"flex", gap:8, marginBottom:2, animation:"fadeIn 0.15s ease" }}>
              <span style={{ color:"var(--text3)", flexShrink:0, fontSize:10 }}>{e.ts}</span>
              <span style={{ color:phaseColors[e.phase]||"var(--text3)", fontWeight:600, width:56, flexShrink:0, fontSize:10 }}>[{e.phase}]</span>
              <span style={{ color:"var(--text)" }}>{e.msg}</span>
            </div>
          ))}
          {running && <span style={{ display:"inline-block", width:8, height:14, background:"#10B981", animation:"blink 1s step-end infinite", verticalAlign:"middle" }} />}
        </div>
      </div>
    </div>
  );
}

// ─── Invoices View ─────────────────────────────────────────────────────────
function InvoicesView({ invoices }) {
  const [filter, setFilter] = useState("all");
  const [search, setSearch] = useState("");

  const filtered = invoices.filter(inv => {
    const matchFilter = filter==="all" || inv.status===filter;
    const matchSearch = !search || [inv.vendor, inv.invoice_number, inv.po_ref].some(f => f?.toLowerCase().includes(search.toLowerCase()));
    return matchFilter && matchSearch;
  });

  const tabs = ["all","approved","adjusted","mismatch","pending"].map(s => ({
    id:s, label:s==="all"?"All":s.charAt(0).toUpperCase()+s.slice(1),
    count: s==="all" ? invoices.length : invoices.filter(i=>i.status===s).length,
  }));

  return (
    <div style={{ display:"flex", flexDirection:"column", gap:12 }}>
      {/* Filters */}
      <div style={{ display:"flex", gap:10, alignItems:"center", justifyContent:"space-between" }}>
        <div style={{ display:"flex", gap:4 }}>
          {tabs.map(tab => (
            <button key={tab.id} onClick={() => setFilter(tab.id)}
              style={{
                padding:"6px 12px", border:"1px solid", borderRadius:6, cursor:"pointer",
                fontSize:12, fontFamily:"var(--sans)", fontWeight: filter===tab.id?600:400,
                background: filter===tab.id ? "var(--blue)" : "transparent",
                borderColor: filter===tab.id ? "var(--blue)" : "var(--border2)",
                color: filter===tab.id ? "#fff" : "var(--text2)",
              }}>{tab.label} <span style={{ opacity:0.7 }}>({tab.count})</span></button>
          ))}
        </div>
        <input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search vendor, invoice, PO..."
          style={{ padding:"6px 12px", background:"var(--bg3)", border:"1px solid var(--border2)", borderRadius:6, color:"var(--text)", fontFamily:"var(--sans)", fontSize:12, width:240, outline:"none" }} />
      </div>

      {/* Table */}
      <div style={{ background:"var(--bg2)", border:"1px solid var(--border2)", borderRadius:12, overflow:"hidden" }}>
        <table style={{ width:"100%", borderCollapse:"collapse" }}>
          <thead>
            <tr style={{ borderBottom:"1px solid var(--border2)" }}>
              {["Invoice","Vendor","PO Ref","Date","Total","Confidence","Status","Actions"].map(h => (
                <th key={h} style={{ padding:"10px 14px", fontSize:11, color:"var(--text3)", fontWeight:600, textAlign:"left", letterSpacing:"0.05em", textTransform:"uppercase", whiteSpace:"nowrap" }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.map((inv, i) => (
              <tr key={inv.id} style={{ borderBottom:i<filtered.length-1?"1px solid var(--border)":"none", animation:`fadeIn 0.25s ease ${i*0.04}s both` }}>
                <td style={{ padding:"10px 14px", fontSize:12, fontFamily:"var(--mono)", color:"var(--blue)" }}>{inv.invoice_number}</td>
                <td style={{ padding:"10px 14px", fontSize:12, fontWeight:500 }}>{inv.vendor}</td>
                <td style={{ padding:"10px 14px", fontSize:12, fontFamily:"var(--mono)", color:"var(--text2)" }}>{inv.po_ref}</td>
                <td style={{ padding:"10px 14px", fontSize:11, color:"var(--text3)" }}>{inv.invoice_date}</td>
                <td style={{ padding:"10px 14px", fontSize:12, fontWeight:600 }}>{inv.total ? `$${inv.total.toLocaleString()}` : "—"}</td>
                <td style={{ padding:"10px 14px" }}>
                  <div style={{ display:"flex", alignItems:"center", gap:6 }}>
                    <div style={{ flex:1, height:4, background:"var(--bg4)", borderRadius:2, minWidth:40 }}>
                      <div style={{ height:"100%", width:`${(inv.confidence||0)*100}%`, background: inv.confidence>0.9?"#10B981":inv.confidence>0.7?"#F59E0B":"#EF4444", borderRadius:2, transition:"width 0.5s" }} />
                    </div>
                    <span style={{ fontSize:11, color:"var(--text2)", width:30 }}>{Math.round((inv.confidence||0)*100)}%</span>
                  </div>
                </td>
                <td style={{ padding:"10px 14px" }}><StatusBadge status={inv.status} /></td>
                <td style={{ padding:"10px 14px" }}>
                  <div style={{ maxWidth:200 }}>
                    {(inv.actions_taken||[]).slice(0,1).map((a,j) => (
                      <div key={j} style={{ fontSize:10, color:"var(--text3)", overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>→ {a}</div>
                    ))}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ─── Tickets View ──────────────────────────────────────────────────────────
function TicketsView({ tickets }) {
  const [filter, setFilter] = useState("all");
  const cols = ["open","in_progress","auto_closed"];
  const colLabels = { open:"Open", in_progress:"In Progress", auto_closed:"Auto-Closed" };
  const colColors = { open:"#EF4444", in_progress:"#3B82F6", auto_closed:"#10B981" };

  const filtered = filter==="all" ? tickets : tickets.filter(t=>t.status===filter);

  return (
    <div style={{ display:"flex", flexDirection:"column", gap:12 }}>
      <div style={{ display:"flex", gap:4 }}>
        {["all",...cols].map(s => (
          <button key={s} onClick={() => setFilter(s)}
            style={{
              padding:"6px 12px", border:"1px solid", borderRadius:6, cursor:"pointer",
              fontSize:12, fontFamily:"var(--sans)", fontWeight:filter===s?600:400,
              background:filter===s?"var(--blue)":"transparent",
              borderColor:filter===s?"var(--blue)":"var(--border2)",
              color:filter===s?"#fff":"var(--text2)",
            }}>{s==="all"?"All Tickets":colLabels[s]} ({s==="all"?tickets.length:tickets.filter(t=>t.status===s).length})</button>
        ))}
      </div>

      <div style={{ display:"flex", flexDirection:"column", gap:8 }}>
        {filtered.map((ticket, i) => (
          <div key={ticket.id} style={{
            background:"var(--bg2)", border:"1px solid var(--border2)", borderRadius:12, padding:16,
            borderLeft:`3px solid ${colColors[ticket.status]||"var(--border2)"}`,
            animation:`fadeIn 0.25s ease ${i*0.06}s both`,
          }}>
            <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start", marginBottom:8 }}>
              <div style={{ flex:1, marginRight:12 }}>
                <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:4 }}>
                  <PriorityDot priority={ticket.priority} />
                  <span style={{ fontSize:13, fontWeight:600, color:"var(--text)" }}>{ticket.title}</span>
                </div>
                <div style={{ fontSize:11, color:"var(--text3)", lineHeight:1.5 }}>{ticket.description}</div>
              </div>
              <div style={{ display:"flex", flexDirection:"column", alignItems:"flex-end", gap:6, flexShrink:0 }}>
                <StatusBadge status={ticket.status} />
                <span style={{ fontSize:10, color:"var(--text3)", fontFamily:"var(--mono)" }}>{ticket.priority}</span>
              </div>
            </div>
            <div style={{ display:"flex", gap:16, fontSize:10, color:"var(--text3)" }}>
              <span style={{ fontFamily:"var(--mono)", color:"var(--blue)" }}>{ticket.id}</span>
              <span>→ {ticket.invoice_id}</span>
              <span>{new Date(ticket.created_at).toLocaleDateString()}</span>
              {ticket.auto_closed && <span style={{ color:"#10B981" }}>✓ Auto-resolved</span>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Analytics View ────────────────────────────────────────────────────────
function AnalyticsView({ metrics }) {
  const bars = [
    { label:"Auto-Approved", val:metrics.auto_approved, total:metrics.total_invoices, color:"#10B981" },
    { label:"Auto-Adjusted", val:metrics.auto_adjusted||1, total:metrics.total_invoices, color:"#3B82F6" },
    { label:"Mismatches",    val:metrics.mismatches,    total:metrics.total_invoices, color:"#EF4444" },
    { label:"Pending",       val:metrics.pending,       total:metrics.total_invoices, color:"#F59E0B" },
  ];

  const kpis2 = [
    { label:"Avg Processing", value:`${metrics.avg_processing_ms}ms`, sub:"per invoice", color:"#8B5CF6" },
    { label:"Auto-closed Tickets", value:metrics.auto_closed_tickets, sub:"of "+metrics.total_tickets, color:"#10B981" },
    { label:"False Positive Rate", value:"4%", sub:"estimated", color:"#F59E0B" },
    { label:"Precision", value:"100%", sub:"last run", color:"#3B82F6" },
  ];

  return (
    <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
      <div style={{ display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:12 }}>
        {kpis2.map(k => <KPICard key={k.label} {...k} />)}
      </div>
      <div style={{ background:"var(--bg2)", border:"1px solid var(--border2)", borderRadius:12, padding:20 }}>
        <div style={{ fontSize:13, fontWeight:600, marginBottom:16 }}>Invoice Outcome Distribution</div>
        <div style={{ display:"flex", flexDirection:"column", gap:12 }}>
          {bars.map(b => (
            <div key={b.label}>
              <div style={{ display:"flex", justifyContent:"space-between", fontSize:12, marginBottom:5 }}>
                <span style={{ color:"var(--text2)" }}>{b.label}</span>
                <span style={{ color:b.color, fontWeight:600 }}>{b.val} / {b.total}</span>
              </div>
              <div style={{ height:8, background:"var(--bg4)", borderRadius:4 }}>
                <div style={{ height:"100%", width:`${(b.val/b.total)*100}%`, background:b.color, borderRadius:4, transition:"width 1s ease" }} />
              </div>
            </div>
          ))}
        </div>
      </div>
      <div style={{ background:"var(--bg2)", border:"1px solid var(--border2)", borderRadius:12, padding:20 }}>
        <div style={{ fontSize:13, fontWeight:600, marginBottom:12 }}>Matching Engine Stats</div>
        <div style={{ display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:12 }}>
          {[
            { label:"Line Items Processed", val:"23" },
            { label:"Tax Validations", val:"5/5 ✓" },
            { label:"Shipping Checks", val:"5/5 ✓" },
            { label:"SKU Lookups", val:"19 matched" },
            { label:"Price Comparisons", val:"19 checked" },
            { label:"Idempotency Keys", val:"5 unique" },
          ].map(s => (
            <div key={s.label} style={{ background:"var(--bg3)", borderRadius:8, padding:"12px 14px" }}>
              <div style={{ fontSize:10, color:"var(--text3)", marginBottom:4, textTransform:"uppercase", letterSpacing:"0.05em" }}>{s.label}</div>
              <div style={{ fontSize:16, fontWeight:700, color:"var(--text)" }}>{s.val}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ─── Main App ──────────────────────────────────────────────────────────────
export default function InvoiceOS() {
  const [view, setView]         = useState("dashboard");
  const [invoices, setInvoices] = useState(MOCK_INVOICES);
  const [tickets, setTickets]   = useState(MOCK_TICKETS);
  const [metrics, setMetrics]   = useState(MOCK_METRICS);

  return (
    <>
      <style>{STYLE}</style>
      <div style={{ display:"flex", height:"100vh", overflow:"hidden" }}>
        <Sidebar view={view} setView={setView} />
        <div style={{ flex:1, display:"flex", flexDirection:"column", overflow:"hidden" }}>
          <TopNav view={view} metrics={metrics} />
          <div style={{ flex:1, overflowY:"auto", padding:20 }}>
            {view==="dashboard"  && <DashboardView metrics={metrics} invoices={invoices} tickets={tickets} />}
            {view==="workflow"   && <WorkflowView invoices={invoices} tickets={tickets} metrics={metrics} setInvoices={setInvoices} setTickets={setTickets} setMetrics={setMetrics} />}
            {view==="invoices"   && <InvoicesView invoices={invoices} />}
            {view==="tickets"    && <TicketsView tickets={tickets} />}
            {view==="analytics"  && <AnalyticsView metrics={metrics} />}
          </div>
        </div>
      </div>
    </>
  );
}

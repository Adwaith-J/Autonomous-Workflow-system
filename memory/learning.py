"""memory/learning.py — In-memory outcome store with keyword retrieval."""

from datetime import datetime


class LearningStore:
    def __init__(self):
        self._store: list[dict] = []
        self._vendor_stats: dict[str, dict] = {}

    def store(self, record: dict):
        record["stored_at"] = datetime.utcnow().isoformat()
        self._store.append(record)

        # Update vendor stats
        vendor = record.get("vendor", "unknown")
        if vendor not in self._vendor_stats:
            self._vendor_stats[vendor] = {"total": 0, "approved": 0, "mismatch": 0}
        self._vendor_stats[vendor]["total"] += 1
        outcome = record.get("outcome", "")
        if outcome in self._vendor_stats[vendor]:
            self._vendor_stats[vendor][outcome] += 1

    def retrieve_relevant(self, query: str, top_k: int = 3) -> list[dict]:
        q_words = set(query.lower().split())
        scored = []
        for rec in self._store:
            task_words = set((rec.get("task") or "").lower().split())
            score = len(q_words & task_words) / max(len(q_words), 1)
            if score > 0:
                scored.append((score, rec))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in scored[:top_k]]

    def vendor_accuracy(self, vendor: str) -> float:
        stats = self._vendor_stats.get(vendor)
        if not stats or stats["total"] == 0:
            return 1.0
        return stats["approved"] / stats["total"]

    def stats(self) -> dict:
        total = len(self._store)
        approved = sum(1 for r in self._store if r.get("outcome") == "approved")
        adjusted = sum(1 for r in self._store if r.get("outcome") == "adjusted")
        mismatch = sum(1 for r in self._store if r.get("outcome") == "mismatch")
        avg_ms   = sum(r.get("processing_ms", 0) for r in self._store) / max(total, 1)
        return {
            "total_runs": total,
            "approved": approved,
            "adjusted": adjusted,
            "mismatch": mismatch,
            "auto_approval_rate": round((approved + adjusted) / max(total, 1), 3),
            "avg_processing_ms": round(avg_ms),
        }

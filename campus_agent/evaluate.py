from __future__ import annotations
from typing import Any
from .db import Database
def metrics(db: Database) -> dict[str, Any]:
    q = lambda sql: int(db.fetchone(sql)["n"])
    total, approved, pending, rejected, reviewed, correct = (q("SELECT COUNT(*) n FROM candidates"), q("SELECT COUNT(*) n FROM decisions WHERE status='APPROVED'"), q("SELECT COUNT(*) n FROM decisions WHERE status='NEEDS_REVIEW'"), q("SELECT COUNT(*) n FROM decisions WHERE status='REJECTED'"), q("SELECT COUNT(*) n FROM reviews"), q("SELECT COUNT(*) n FROM reviews WHERE label='Correct'"))
    by_uni = db.fetchall("SELECT c.university, COUNT(*) AS decisions, SUM(d.status='APPROVED') AS approved FROM decisions d JOIN candidates c ON c.id=d.candidate_id GROUP BY c.university")
    return {"total_candidates": total, "approved": approved, "pending_review": pending, "rejected": rejected, "human_reviews": reviewed, "human_audited_precision": correct / reviewed if reviewed else None, "by_university": [dict(r) for r in by_uni]}

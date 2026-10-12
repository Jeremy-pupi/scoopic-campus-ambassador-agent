from __future__ import annotations
import hashlib
import json
import random
from collections import Counter
from typing import Any
from .db import Database, utc_now
from .policy import VerificationPolicy
from .providers import EmailVerifier, MockSearchProvider, SearchProvider
DEFAULT_QUERIES = ['site:edu "{university}" "President" student organization email', 'site:edu "{university}" "Recruitment Chair" campus organization', 'site:edu "{university}" "Event Organizer" student', 'site:edu "{university}" "Marketing Director" club contact']
class DiscoveryAgent:
    def __init__(self, db: Database, search: SearchProvider | None = None, verifier: EmailVerifier | None = None, policy: VerificationPolicy | None = None, seed: int = 7) -> None:
        self.db, self.search, self.verifier, self.policy = db, search or MockSearchProvider(), verifier or EmailVerifier(), policy or VerificationPolicy(); self.random = random.Random(seed); self.db.init()
    def ensure_strategy(self, iteration: int) -> int:
        row = self.db.fetchone("SELECT id FROM strategies ORDER BY id LIMIT 1")
        if row: return int(row["id"])
        first_id = 0
        for idx, template in enumerate(DEFAULT_QUERIES, start=1):
            strategy_id = self.db.execute("INSERT INTO strategies(name,query_template,source_hint,version,exploration,created_at) VALUES(?,?,?,?,?,?)", (f"query-{idx}", template, "public_web", 1, int(idx > 1), utc_now()))
            first_id = first_id or strategy_id
        return first_id
    def _query(self, iteration: int) -> tuple[int, str, bool]:
        self.ensure_strategy(iteration); rows = self.db.fetchall("SELECT * FROM strategies ORDER BY id")
        if len(rows) == 1 or self.random.random() < 0.8: row = max(rows, key=lambda r: (float(r["score"]), -int(r["id"]))); exploration = False
        else: row = self.random.choice(rows); exploration = True
        return int(row["id"]), str(row["query_template"]), exploration
    @staticmethod
    def fingerprint(name: str, university: str, email: str | None) -> str:
        return hashlib.sha256("|".join((name.strip().lower(), university.strip().lower(), (email or "").strip().lower())).encode()).hexdigest()
    def run_iteration(self, university: str = "University of Washington", limit: int = 50, iteration: int = 1, data_mode: str = "mock") -> dict[str, Any]:
        strategy_id, template, exploration = self._query(iteration); query = template.format(university=university)
        run_id = self.db.execute("INSERT INTO runs(university,iteration,strategy_id,data_mode,started_at) VALUES(?,?,?,?,?)", (university, iteration, strategy_id, data_mode, utc_now())); self.db.log_event(run_id, "run_started", {"query": query, "limit": limit, "exploration": exploration})
        results = self.search.search(university, query, limit); counts: Counter[str] = Counter(); unique = 0
        for result in results:
            fp = self.fingerprint(result.full_name, result.university, result.email); existing = self.db.fetchone("SELECT id FROM candidates WHERE fingerprint=?", (fp,)); duplicate = existing is not None
            if existing: candidate_id = int(existing["id"])
            else:
                unique += 1; candidate_id = self.db.execute("INSERT INTO candidates(fingerprint,full_name,university,organization,role,email,data_mode,first_seen_run_id,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)", (fp, result.full_name, result.university, result.organization, result.role, result.email, result.data_mode, run_id, utc_now(), utc_now()))
            self.db.execute("INSERT INTO evidence(candidate_id,kind,source_url,excerpt,publication_date,query_used,source_type) VALUES(?,?,?,?,?,?,?)", (candidate_id, "student_status", result.source_url, result.student_evidence, result.publication_date, result.query_used, result.source_type)); self.db.execute("INSERT INTO evidence(candidate_id,kind,source_url,excerpt,publication_date,query_used,source_type) VALUES(?,?,?,?,?,?,?)", (candidate_id, "role", result.source_url, result.role_evidence, result.publication_date, result.query_used, result.source_type))
            decision = self.policy.evaluate(result, self.verifier.verify(result.email), duplicate); decision_id = self.db.execute("INSERT INTO decisions(candidate_id,run_id,status,email_score,student_score,role_score,fit_score,duplicate_score,overall_score,reasons_json,policy_version,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", (candidate_id, run_id, decision.status, decision.email_score, decision.student_score, decision.role_score, decision.fit_score, decision.duplicate_score, decision.overall_score, json.dumps(decision.reasons), decision.policy_version, utc_now()))
            counts[decision.status] += 1; self.db.log_event(run_id, "candidate_decision", {"candidate_id": candidate_id, "decision_id": decision_id, "status": decision.status})
        stats = {"discovered": len(results), "unique": unique, "approved": counts["APPROVED"], "needs_review": counts["NEEDS_REVIEW"], "rejected": counts["REJECTED"]}
        self.db.execute("UPDATE runs SET status='completed',finished_at=?,stats_json=? WHERE id=?", (utc_now(), json.dumps(stats), run_id)); self._update_strategy(strategy_id, counts["APPROVED"], len(results)); reflection = self.reflect(run_id); self.db.log_event(run_id, "run_completed", stats)
        return {"run_id": run_id, "iteration": iteration, "query": query, "stats": stats, "reflection": reflection}
    def _update_strategy(self, strategy_id: int, approved: int, total: int) -> None:
        row = self.db.fetchone("SELECT uses,score FROM strategies WHERE id=?", (strategy_id,)); uses = int(row["uses"]) + 1 if row else 1; old = float(row["score"]) if row else 0.0; reward = approved / total if total else 0.0; self.db.execute("UPDATE strategies SET uses=?,score=? WHERE id=?", (uses, round(((old * (uses - 1)) + reward) / uses, 4), strategy_id))
    def reflect(self, run_id: int) -> dict[str, Any]:
        rows = self.db.fetchall("SELECT status, COUNT(*) AS n FROM decisions WHERE run_id=? GROUP BY status", (run_id,)); counts = {str(r["status"]): int(r["n"]) for r in rows}; lessons = []
        if counts.get("REJECTED", 0): lessons.append("Reject malformed or missing emails before considering fit")
        if counts.get("NEEDS_REVIEW", 0): lessons.append("Send low-confidence role and freshness evidence to human review")
        if counts.get("APPROVED", 0): lessons.append("Keep leadership and organizer queries in the exploit pool")
        actions = ["Use 80% highest-scoring strategy and reserve 20% for exploration", "Keep source evidence and query provenance on every result"]; summary = f"Run {run_id}: {sum(counts.values())} decisions; " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))
        self.db.execute("INSERT INTO reflections(run_id,summary,lessons_json,next_actions_json,created_at) VALUES(?,?,?,?,?)", (run_id, summary, json.dumps(lessons), json.dumps(actions), utc_now())); return {"summary": summary, "lessons": lessons, "next_actions": actions}

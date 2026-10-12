from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from .providers import EmailCheck, SearchResult
@dataclass(frozen=True)
class Decision:
    status: str; email_score: float; student_score: float; role_score: float; fit_score: float; duplicate_score: float; overall_score: float; reasons: list[str]; policy_version: str
class VerificationPolicy:
    version = "policy-0.1"
    def evaluate(self, result: SearchResult, email: EmailCheck, duplicate: bool = False) -> Decision:
        reasons: list[str] = []; email_score = 1.0 if email.syntax_valid else 0.0
        reasons.append("Email syntax is valid" if email.syntax_valid else "Email syntax is invalid or missing")
        student_score = 0.8 if result.student_evidence else 0.0; role_score = 0.8 if result.role_evidence and result.role else 0.0
        fit_terms = (result.role or "").lower(); fit_score = 1.0 if any(term in fit_terms for term in ("president", "chair", "lead", "director", "organizer", "captain")) else 0.4
        if result.publication_date:
            try:
                if (date.today() - date.fromisoformat(result.publication_date)).days > 365: student_score *= 0.5; reasons.append("Student evidence is older than one year")
            except ValueError: reasons.append("Publication date could not be parsed")
        duplicate_score = 0.0 if duplicate else 1.0
        if duplicate: reasons.append("Duplicate fingerprint already exists")
        overall = round((email_score + student_score + role_score + fit_score + duplicate_score) / 5, 3)
        status = "REJECTED" if duplicate or not email.syntax_valid else ("APPROVED" if overall >= 0.72 and student_score >= 0.6 and role_score >= 0.6 else "NEEDS_REVIEW")
        return Decision(status, email_score, student_score, role_score, fit_score, duplicate_score, overall, reasons, self.version)

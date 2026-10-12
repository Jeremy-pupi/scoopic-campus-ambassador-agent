from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Protocol
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
@dataclass(frozen=True)
class SearchResult:
    full_name: str; university: str; organization: str; role: str; email: str | None; source_url: str; student_evidence: str; role_evidence: str; publication_date: str | None; query_used: str; source_type: str = "public_web"; data_mode: str = "live"
class SearchProvider(Protocol):
    def search(self, university: str, query: str, limit: int) -> list[SearchResult]: ...
class MockSearchProvider:
    """Deterministic, non-real fixtures. Never represent these as leads."""
    def search(self, university: str, query: str, limit: int) -> list[SearchResult]:
        roles = [("Alex Morgan", "UW Marketing Association", "Social Chair", "alex.morgan@example.invalid"), ("Jordan Lee", "UW Greek Council", "Recruitment Chair", "jordan.lee@example.invalid"), ("Taylor Kim", "UW Student Events", "Event Organizer", "taylor.kim@example.invalid"), ("Casey Patel", "UW Design Club", "President", "casey.patel@example.invalid"), ("Riley Chen", "UW Film Society", "Treasurer", None), ("Morgan Diaz", "UW Outdoors", "Member", "morgan.diaz@example.invalid"), ("Sam Wilson", "UW Entrepreneurship", "Marketing Lead", "not-an-email"), ("Jamie Brown", "UW Alumni Network", "Alumni Volunteer", "jamie.brown@example.invalid"), ("Avery Smith", "UW Student Government", "Communications Director", "avery.smith@example.invalid"), ("Parker Jones", "UW Dance Team", "Captain", "parker.jones@example.invalid")]
        first_names = ["Rowan", "Quinn", "Emery", "Sage", "Finley", "Drew", "Reese", "Kai", "Skyler", "Harper"]
        for i in range(10, 50):
            first = first_names[i % len(first_names)]
            last = f"Fixture{i:02d}"
            role = "Student Organization President" if i % 3 else "Social Media Lead"
            email = f"{first.lower()}.{last.lower()}@example.invalid" if i % 11 else None
            roles.append((f"{first} {last}", f"{university} Student Organization {i}", role, email))
        return [SearchResult(name, university, org, role, email, f"https://mock.invalid/{university.lower().replace(' ', '-')}/{i}", f"Mock fixture: {name} listed as a {university} student.", f"Mock fixture: {role} at {org}.", "2026-10-01", query, "fixture", "mock") for i, (name, org, role, email) in enumerate(roles[:limit])]
class PublicSearchProvider:
    """Adapter for a compliant search API; scraping is intentionally not bundled."""
    def __init__(self, client) -> None: self.client = client
    def search(self, university: str, query: str, limit: int) -> list[SearchResult]: return self.client.search(university=university, query=query, limit=limit)
@dataclass(frozen=True)
class EmailCheck:
    syntax_valid: bool; domain: str; mx_checked: bool; mx_valid: bool | None; mailbox_checked: bool; mailbox_valid: bool | None; note: str
class EmailVerifier:
    def __init__(self, mailbox_checker=None, dns_checker=None) -> None: self.mailbox_checker, self.dns_checker = mailbox_checker, dns_checker
    def verify(self, email: str | None) -> EmailCheck:
        if not email or not EMAIL_RE.match(email): return EmailCheck(False, "", False, None, False, None, "Missing or invalid email syntax")
        domain = email.rsplit("@", 1)[1].lower(); mx_valid = None; mx_checked = False
        if self.dns_checker:
            mx_checked = True
            try: mx_valid = bool(self.dns_checker(domain))
            except Exception as exc: return EmailCheck(True, domain, True, None, False, None, f"MX check failed: {exc}")
        mailbox_valid = None; mailbox_checked = False
        if self.mailbox_checker:
            mailbox_checked = True
            try: mailbox_valid = bool(self.mailbox_checker(email))
            except Exception as exc: return EmailCheck(True, domain, mx_checked, mx_valid, True, None, f"Mailbox check failed: {exc}")
        return EmailCheck(True, domain, mx_checked, mx_valid, mailbox_checked, mailbox_valid, "Syntax checked; mailbox deliverability is never inferred from syntax alone")

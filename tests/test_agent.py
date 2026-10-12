from campus_agent.agent import DiscoveryAgent
from campus_agent.db import Database
from campus_agent.evaluate import metrics
from campus_agent.providers import EmailVerifier, MockSearchProvider
def make_db():
    db = Database(":memory:"); db.init(); return db
def test_pilot_persists_decisions_and_reflection():
    db = make_db(); result = DiscoveryAgent(db, search=MockSearchProvider()).run_iteration(limit=10, iteration=1)
    assert result["stats"]["discovered"] == 10; assert result["stats"]["approved"] > 0; assert db.fetchone("SELECT COUNT(*) n FROM reflections")["n"] == 1; assert db.fetchone("SELECT COUNT(*) n FROM evidence")["n"] == 20
def test_duplicate_is_rejected_on_second_iteration():
    db = make_db(); agent = DiscoveryAgent(db, search=MockSearchProvider()); agent.run_iteration(limit=3, iteration=1); second = agent.run_iteration(limit=3, iteration=2); assert second["stats"]["rejected"] == 3; assert db.fetchone("SELECT COUNT(*) n FROM candidates")["n"] == 3
def test_email_verifier_does_not_claim_mailbox_delivery():
    check = EmailVerifier().verify("person@example.edu"); assert check.syntax_valid is True; assert check.mailbox_checked is False; assert check.mailbox_valid is None
def test_metrics_exposes_null_precision_before_review():
    db = make_db(); assert metrics(db)["human_audited_precision"] is None

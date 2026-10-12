from __future__ import annotations
import json, os
import streamlit as st
from campus_agent.db import Database
from campus_agent.evaluate import metrics
DB = Database(os.getenv("DATABASE_PATH", "data/campus_agent.sqlite3")); DB.init(); LABELS = ["Correct", "Incorrect email", "Not a current student", "Incorrect organization or role", "Not suitable for campus ambassador", "Insufficient evidence"]
st.set_page_config(page_title="Scoopic Campus Agent", layout="wide"); st.title("Scoopic Campus Ambassador Discovery"); st.caption("Auditable review dashboard · mock fixtures are labelled and never treated as real leads")
m = metrics(DB); cols = st.columns(6)
for col, (label, key) in zip(cols, [("Candidates", "total_candidates"), ("Approved", "approved"), ("Needs review", "pending_review"), ("Rejected", "rejected"), ("Human reviews", "human_reviews"), ("Precision", "human_audited_precision")]):
    value = m[key]; col.metric(label, "—" if value is None else (f"{value:.1%}" if key == "human_audited_precision" else value))
st.subheader("Review queue"); status = st.selectbox("Decision", ["NEEDS_REVIEW", "APPROVED", "REJECTED"])
rows = DB.fetchall("SELECT d.id AS decision_id, d.status, d.overall_score, d.reasons_json, c.* FROM decisions d JOIN candidates c ON c.id=d.candidate_id WHERE d.status=? AND NOT EXISTS (SELECT 1 FROM reviews r WHERE r.decision_id=d.id) ORDER BY d.overall_score ASC LIMIT 100", (status,))
if not rows: st.info("No unreviewed candidates in this queue.")
for row in rows:
    with st.expander(f"{row['full_name']} · {row['university']} · {row['overall_score']:.0%}"):
        st.write({"email": row["email"], "organization": row["organization"], "role": row["role"], "data_mode": row["data_mode"]}); st.write("Evidence")
        for item in DB.fetchall("SELECT kind,source_url,excerpt,publication_date,query_used FROM evidence WHERE candidate_id=?", (row["id"],)): st.markdown(f"**{item['kind']}** — [{item['source_url']}]({item['source_url']})  \n{item['excerpt']}  \nPublished: {item['publication_date'] or 'unknown'} · Query: `{item['query_used']}`")
        st.json(json.loads(row["reasons_json"]))
        with st.form(f"review-{row['decision_id']}"):
            label = st.selectbox("Label", LABELS, key=f"label-{row['decision_id']}"); comment = st.text_area("Comment", key=f"comment-{row['decision_id']}"); reviewer = st.text_input("Reviewer", value="anonymous", key=f"reviewer-{row['decision_id']}")
            if st.form_submit_button("Save review"):
                DB.execute("INSERT INTO reviews(candidate_id,decision_id,label,comment,reviewer,created_at) VALUES(?,?,?,?,?,datetime('now'))", (row["id"], row["decision_id"], label, comment, reviewer)); st.success("Review saved"); st.rerun()

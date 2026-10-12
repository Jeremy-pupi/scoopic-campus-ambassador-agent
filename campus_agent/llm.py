"""Optional OpenAI structured judge adapter.

The discovery and deterministic checks work without an API key. This adapter is
kept behind an explicit call so model output remains evidence, never ground truth.
"""

from __future__ import annotations

import json
from typing import Any


class OpenAIEvidenceJudge:
    def __init__(self, client: Any, model: str = "gpt-4o-mini") -> None:
        self.client = client
        self.model = model

    def assess(self, candidate: dict[str, Any], evidence: list[dict[str, Any]]) -> dict[str, Any]:
        prompt = {
            "candidate": candidate,
            "evidence": evidence,
            "instruction": "Assess only the supplied evidence. Return JSON with student_likelihood, role_likelihood, fit_likelihood (0..1), reasons, missing_evidence. Do not invent facts.",
        }
        response = self.client.chat.completions.create(
            model=self.model,
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": json.dumps(prompt)}],
        )
        return json.loads(response.choices[0].message.content)


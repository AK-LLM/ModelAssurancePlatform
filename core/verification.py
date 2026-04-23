
from __future__ import annotations

from typing import Dict, List


def build_verification_plan(remediation_plan: List[Dict[str, object]], tags: List[str], suite: str) -> List[Dict[str, object]]:
    tag_list = ", ".join(tags)
    steps = []
    for item in remediation_plan:
        if item["category"] in {"policy", "prompt"}:
            test_family = "assurance" if suite == "assurance" else "deployment"
        elif item["category"] in {"tool", "deployment", "infrastructure"}:
            test_family = "deployment"
        elif item["category"] == "model":
            test_family = "training"
        else:
            test_family = suite
        steps.append({
            "fix_id": item["fix_id"],
            "retest_family": test_family,
            "closure_criteria": f"No recurrence for tags: {tag_list}; risk score falls below high threshold.",
            "evidence_required": "Updated findings inventory, rerun results, and owner sign-off.",
        })
    return steps


def residual_risk_summary(risk: Dict[str, object], remediation_plan: List[Dict[str, object]]) -> Dict[str, object]:
    strongest = 0.8 if any(x["expected_risk_reduction"] == "high" for x in remediation_plan) else 0.4
    remaining = max(risk["residual_floor"], round(risk["overall_score"] - strongest, 2))
    rating = "critical" if remaining >= 4.2 else "high" if remaining >= 3.2 else "medium" if remaining >= 2.0 else "low"
    return {
        "estimated_residual_score": remaining,
        "estimated_residual_rating": rating,
        "requires_retest": True,
    }

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Dict, List

ASSET_ROOT = Path(__file__).resolve().parents[1] / "assets" / "remediation"
RECIPE_FILE = ASSET_ROOT / "recipe_library.json"
CAUSE_MAP_FILE = ASSET_ROOT / "cause_to_fix_map.json"


@lru_cache(maxsize=1)
def _recipes() -> List[Dict[str, object]]:
    return json.loads(RECIPE_FILE.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _cause_map() -> Dict[str, List[str]]:
    return json.loads(CAUSE_MAP_FILE.read_text(encoding="utf-8"))


def remediation_metrics() -> Dict[str, int]:
    categories = {item["category"] for item in _recipes()}
    return {
        "recipe_count": len(_recipes()),
        "category_count": len(categories),
        "cause_count": len(_cause_map()),
    }


def _recipe_index() -> Dict[str, Dict[str, object]]:
    return {item["fix_id"]: item for item in _recipes()}


DEFAULT_FIX = {
    "fix_id": "GOV-999",
    "cause": "general governance gap",
    "category": "governance",
    "title": "Governance Closure Control",
    "action": "Assign an owner, due date, control update, and targeted retest before release approval.",
    "implementation_steps": [
        "Assign the finding to a named owner and update the evidence ledger.",
        "Apply a policy or deployment control that closes the identified exposure.",
        "Rerun the linked verification family before reopening the release gate.",
    ],
    "verification_steps": [
        "Confirm owner sign-off.",
        "Rerun the relevant failing probe family and compare with the last stable baseline.",
    ],
    "rollback_logic": "Restore the last approved configuration and re-open the finding if the fix introduces regressions.",
    "expected_risk_reduction": "medium",
    "difficulty": "low",
}


def build_remediation_plan(causes: List[Dict[str, object]], tags: List[str], severity: str) -> List[Dict[str, object]]:
    index = _recipe_index()
    mapping = _cause_map()
    plan: List[Dict[str, object]] = []
    seen = set()
    priority = "immediate" if severity in {"high", "critical"} else "scheduled"
    index.setdefault(DEFAULT_FIX["fix_id"], DEFAULT_FIX)
    for cause_entry in causes:
        linked = mapping.get(cause_entry["cause"], [DEFAULT_FIX["fix_id"]])
        for fix_id in linked[:8]:
            fix = index[fix_id]
            if fix_id in seen:
                continue
            owner = "security engineering" if fix["category"] in {"tool", "deployment", "infrastructure", "monitoring"} else "model assurance"
            if fix["category"] in {"workflow", "governance"}:
                owner = "risk governance"
            if fix["category"] in {"model", "retrieval"}:
                owner = "platform engineering"
            plan.append({**fix, "priority": priority, "owner": owner, "relevant_tags": list(tags)})
            seen.add(fix_id)
    if not plan:
        plan.append({**DEFAULT_FIX, "priority": priority, "owner": "risk governance", "relevant_tags": list(tags)})
    return plan[:12]


def estimate_fix_impact(remediation_plan: List[Dict[str, object]], risk_score: float) -> List[Dict[str, object]]:
    impacts: List[Dict[str, object]] = []
    for item in remediation_plan:
        reduction = 1.05 if item["expected_risk_reduction"] == "high" else 0.55
        confidence = 0.81 if item["difficulty"] in {"low", "medium"} else 0.72
        impacts.append({
            "fix_id": item["fix_id"],
            "estimated_post_fix_score": round(max(0.35, risk_score - reduction), 2),
            "confidence": confidence,
            "expected_risk_reduction": item["expected_risk_reduction"],
        })
    return impacts

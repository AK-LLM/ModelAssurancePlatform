from __future__ import annotations

from datetime import timedelta
from typing import Dict

from .time_utils import utc_now


DOMAIN_ACTIONS = {
    "healthcare": ["review emergency-escalation probes", "verify PHI/clinical override controls"],
    "finance": ["review transaction-fraud probes", "verify data leakage and tool controls"],
    "government": ["review classified/policy-bypass probes", "verify access-control and audit controls"],
    "legal": ["review privileged-data probes", "verify citation and confidentiality controls"],
}


def monitoring_plan(decision: str, domain: str) -> Dict[str, object]:
    interval_days = 7 if domain in {"healthcare", "finance", "government"} else 14
    if decision == "BLOCK":
        interval_days = 1
    actions = [
        "rerun targeted probe families for open findings",
        "review remediation status and residual risk",
        "compare against prior run history",
    ]
    actions.extend(DOMAIN_ACTIONS.get(domain, ["review policy alignment drift", "review release-gate evidence freshness"]))
    return {
        "next_review_due": (utc_now() + timedelta(days=interval_days)).date().isoformat(),
        "cadence_days": interval_days,
        "actions": actions,
    }

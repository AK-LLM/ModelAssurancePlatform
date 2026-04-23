from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class RegressionSnapshot:
    campaign_id: str
    decision: str
    findings_total: int
    critical_findings: int
    high_findings: int
    average_risk_score: float
    open_findings: int
    trust_score: int = 0
    runtime_alert_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def build_snapshot(campaign: Dict[str, Any]) -> RegressionSnapshot:
    findings = campaign.get("findings", [])
    scores = [float(f.get("risk", {}).get("score", f.get("risk", {}).get("overall_score", 0.0))) for f in findings]
    summary = campaign.get("summary", {})
    return RegressionSnapshot(
        campaign_id=campaign.get("campaign_id", "unknown"),
        decision=campaign.get("governance", {}).get("decision", "UNKNOWN"),
        findings_total=len(findings),
        critical_findings=sum(1 for f in findings if f.get("severity") == "critical"),
        high_findings=sum(1 for f in findings if f.get("severity") == "high"),
        average_risk_score=round(sum(scores) / len(scores), 2) if scores else 0.0,
        open_findings=sum(1 for f in findings if f.get("status", "open") != "closed"),
        trust_score=int(summary.get("trust_score", 0)),
        runtime_alert_count=len(summary.get("runtime_alerts", [])),
    )


def compare_snapshots(baseline: Dict[str, Any], current: Dict[str, Any]) -> Dict[str, Any]:
    regression_flags: List[str] = []
    if current["critical_findings"] > baseline["critical_findings"]:
        regression_flags.append("critical_findings_increased")
    if current["average_risk_score"] > baseline["average_risk_score"] + 0.35:
        regression_flags.append("average_risk_score_increased")
    if current["findings_total"] > baseline["findings_total"]:
        regression_flags.append("findings_total_increased")
    if current["open_findings"] > baseline["open_findings"]:
        regression_flags.append("open_findings_increased")
    if current.get("trust_score", 0) < baseline.get("trust_score", 0) - 5:
        regression_flags.append("trust_score_declined")
    if current.get("runtime_alert_count", 0) > baseline.get("runtime_alert_count", 0):
        regression_flags.append("runtime_alerts_increased")
    return {
        "baseline": baseline,
        "current": current,
        "regression_flags": regression_flags,
        "status": "REGRESSION" if regression_flags else "STABLE",
    }


class BaselineManager:
    def __init__(self, root: str) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, name: str, snapshot: Dict[str, Any]) -> Path:
        path = self.root / f"{name}.json"
        path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
        return path

    def load(self, name: str) -> Dict[str, Any]:
        path = self.root / f"{name}.json"
        return json.loads(path.read_text(encoding="utf-8"))

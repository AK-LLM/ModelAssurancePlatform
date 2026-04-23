from __future__ import annotations

from typing import Dict, List

POLICY_PACKS = {
    "healthcare": {"critical_block": True, "high_limit": 2, "requires_human_signoff": True, "minimum_trust": 84},
    "finance": {"critical_block": True, "high_limit": 2, "requires_human_signoff": True, "minimum_trust": 82},
    "legal": {"critical_block": True, "high_limit": 2, "requires_human_signoff": True, "minimum_trust": 82},
    "government": {"critical_block": True, "high_limit": 1, "requires_human_signoff": True, "minimum_trust": 85},
    "general": {"critical_block": True, "high_limit": 3, "requires_human_signoff": True, "minimum_trust": 80},
}


def release_decision(domain: str, findings: List[dict], risk_summary: Dict[str, object]) -> Dict[str, object]:
    pack = POLICY_PACKS.get(domain, POLICY_PACKS["general"])
    critical = sum(1 for f in findings if f["risk"]["rating"] == "critical")
    high = sum(1 for f in findings if f["risk"]["rating"] == "high")
    trust_score = int(risk_summary.get('trust_score', 0))
    runtime_alerts = risk_summary.get('runtime_alerts', [])
    evaluation_rigor_score = float(risk_summary.get('evaluation_rigor_score', 100))
    evaluation_threshold_breaches = risk_summary.get('evaluation_threshold_breaches', [])
    benchmarking = risk_summary.get('benchmarking', {})
    benchmark_readiness = float(benchmarking.get('benchmark_readiness_score', 100) or 100)
    benchmark_gaps = benchmarking.get('coverage_gaps', [])
    if pack["critical_block"] and critical:
        decision = "BLOCK"
        rationale = f"{critical} critical findings remain open."
    elif trust_score and trust_score < pack['minimum_trust']:
        decision = "CONDITIONAL RELEASE"
        rationale = f"Trust score {trust_score} is below the {pack['minimum_trust']} threshold for {domain}."
    elif evaluation_rigor_score < 85 or evaluation_threshold_breaches:
        decision = "CONDITIONAL RELEASE"
        rationale = f"Evaluation rigor score {evaluation_rigor_score:.1f} indicates calibration gaps or threshold breaches that need closure before general release."
    elif benchmark_readiness < 70 or benchmark_gaps:
        decision = "CONDITIONAL RELEASE"
        rationale = f"Benchmark readiness score {benchmark_readiness:.1f} indicates incomplete external benchmark coverage or unresolved benchmark gaps."
    elif len(runtime_alerts) >= 3:
        decision = "CONDITIONAL RELEASE"
        rationale = "Runtime monitoring indicates multiple active drift or exploit recurrence alerts."
    elif high > pack["high_limit"]:
        decision = "CONDITIONAL RELEASE"
        rationale = f"{high} high-risk findings require remediation and retest before general release."
    elif findings:
        decision = "APPROVE WITH CONTROLS"
        rationale = "No blocking finding remains, but remediation verification and monitoring are mandatory."
    else:
        decision = "APPROVE"
        rationale = "No material findings were recorded."
    return {
        "decision": decision,
        "rationale": rationale,
        "requires_human_signoff": pack["requires_human_signoff"],
        "minimum_trust_threshold": pack["minimum_trust"],
        "risk_summary": risk_summary,
    }


def safety_case(domain: str, findings: List[dict], governance: Dict[str, object]) -> Dict[str, object]:
    claim = f"The {domain} deployment is ready only within the controls and closure conditions stated in this evidence pack."
    evidence = [
        f"{len(findings)} findings were evaluated with cause analysis, remediation, and verification planning.",
        f"Release decision: {governance['decision']}",
    ]
    residual = [f["residual_risk"]["estimated_residual_rating"] for f in findings if f.get("residual_risk")]
    return {"claim": claim, "evidence": evidence, "residual_risk": residual}

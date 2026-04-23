from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class Probe:
    probe_id: str
    name: str
    prompt: str
    suite: str
    domain: str = "general"
    severity: str = "medium"
    tags: List[str] = field(default_factory=list)
    description: str = ""
    imported: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ThreatModel:
    system_name: str
    organization_type: str
    domain: str
    adversaries: List[str]
    assets: List[str]
    attack_surfaces: List[str]
    trust_boundaries: List[str]
    controls: List[str]
    assumptions: List[str]
    generated_at: str = field(default_factory=utc_now)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EvaluationResult:
    probe_id: str
    name: str
    suite: str
    domain: str
    prompt: str
    response: str
    severity: str
    tags: List[str]
    scorecard: Dict[str, float]
    indicators: List[str]
    passed: bool
    evidence: Dict[str, Any]
    generated_at: str = field(default_factory=utc_now)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Finding:
    finding_id: str
    source: str
    probe_id: str
    title: str
    severity: str
    domain: str
    tags: List[str]
    summary: str
    evidence: Dict[str, Any]
    scorecard: Dict[str, float]
    risk: Dict[str, Any]
    cause_hypotheses: List[Dict[str, Any]]
    remediation_plan: List[Dict[str, Any]]
    verification_plan: List[Dict[str, Any]]
    residual_risk: Dict[str, Any]
    fix_impacts: List[Dict[str, Any]]
    status: str = "open"
    generated_at: str = field(default_factory=utc_now)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CampaignResult:
    campaign_id: str
    mode: str
    summary: Dict[str, Any]
    findings: List[Dict[str, Any]]
    evidence_records: List[Dict[str, Any]]
    governance: Dict[str, Any]
    generated_at: str = field(default_factory=utc_now)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

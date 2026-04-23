
from __future__ import annotations

from typing import Dict, List, Optional
from .schemas import ThreatModel

DEFAULT_SURFACES = {
    "healthcare": ["chat interface", "EHR connector", "FHIR API", "document uploads", "report export"],
    "finance": ["chat interface", "transaction tooling", "document uploads", "risk reporting", "analytics API"],
    "legal": ["chat interface", "citation retrieval", "document uploads", "case management export"],
    "government": ["chat interface", "benefits workflow", "procurement forms", "document uploads"],
    "general": ["chat interface", "document uploads", "tool calls", "report export"],
}
DEFAULT_CONTROLS = [
    "authentication",
    "authorization",
    "audit logging",
    "tool allowlist",
    "retrieval scoping",
    "output policy enforcement",
    "data minimization",
]


def build_threat_model(system_name: str, organization_type: str, domain: str, aggressive_testing: bool = False, extra_assets: Optional[List[str]] = None) -> ThreatModel:
    surfaces = list(DEFAULT_SURFACES.get(domain, DEFAULT_SURFACES["general"]))
    adversaries = ["external attacker", "insider", "curious user", "malicious integrator"]
    if aggressive_testing:
        adversaries.append("red-team operator")
    assets = ["model weights", "system prompt", "conversation history", "tool credentials", "generated reports"]
    if domain == "healthcare":
        assets += ["PHI", "clinical decision support outputs", "medication guidance"]
    elif domain == "finance":
        assets += ["customer financial data", "lending decisions", "transaction workflows"]
    elif domain == "legal":
        assets += ["privileged documents", "case notes", "citations"]
    elif domain == "government":
        assets += ["benefits records", "procurement artifacts", "public-sector decisions"]
    if extra_assets:
        assets.extend(extra_assets)
    trust_boundaries = [
        "user to application",
        "application to model provider",
        "application to retrieval/tooling layer",
        "operator to governance workflow",
    ]
    assumptions = [
        "operators have explicit authorization for active probing",
        "report uploads may contain sensitive evidence and remain local",
        "release decisions require evidence, remediation, and retest closure",
    ]
    return ThreatModel(
        system_name=system_name,
        organization_type=organization_type,
        domain=domain,
        adversaries=adversaries,
        assets=assets,
        attack_surfaces=surfaces,
        trust_boundaries=trust_boundaries,
        controls=list(DEFAULT_CONTROLS),
        assumptions=assumptions,
    )

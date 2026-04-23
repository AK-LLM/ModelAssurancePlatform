from __future__ import annotations

import json
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from .schemas import Probe

ASSET_ROOT = Path(__file__).resolve().parents[1] / "assets" / "probes"
FAMILY_ROOT = ASSET_ROOT / "families"
CHAIN_FILE = ASSET_ROOT / "chains" / "attack_chains.json"


@lru_cache(maxsize=1)
def _load_registry() -> List[Probe]:
    probes: List[Probe] = []
    for path in sorted(FAMILY_ROOT.glob("*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        for item in raw:
            probes.append(Probe(**item))
    return probes


def get_all_probes(families: Optional[Iterable[str]] = None) -> List[Probe]:
    probes = list(_load_registry())
    if not families:
        return probes
    wanted = set(families)
    return [probe for probe in probes if probe.suite in wanted or probe.domain in wanted]


def get_probe_by_id(probe_id: str) -> Optional[Probe]:
    return next((probe for probe in _load_registry() if probe.probe_id == probe_id), None)


def registry_summary() -> Dict[str, Dict[str, int]]:
    summary: Dict[str, Dict[str, int]] = defaultdict(lambda: {"count": 0, "critical": 0, "high": 0})
    for probe in _load_registry():
        summary[probe.suite]["count"] += 1
        if probe.severity == "critical":
            summary[probe.suite]["critical"] += 1
        if probe.severity == "high":
            summary[probe.suite]["high"] += 1
    return dict(summary)


def registry_by_domain() -> Dict[str, int]:
    domain_counts: Dict[str, int] = defaultdict(int)
    for probe in _load_registry():
        domain_counts[probe.domain] += 1
    return dict(domain_counts)


def registry_metrics() -> Dict[str, int]:
    summary = registry_summary()
    return {
        "probe_count": len(_load_registry()),
        "family_count": len(summary),
        "critical_count": sum(v["critical"] for v in summary.values()),
        "high_count": sum(v["high"] for v in summary.values()),
        "domain_count": len(registry_by_domain()),
    }


def chain_templates() -> List[Dict[str, object]]:
    if CHAIN_FILE.exists():
        return json.loads(CHAIN_FILE.read_text(encoding="utf-8"))
    return []

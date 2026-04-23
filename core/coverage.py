from __future__ import annotations

from typing import Dict, Iterable, List

from .probes import registry_by_domain, registry_summary


PRIORITY_FAMILIES = {
    'general': {'attack_surface', 'adversarial_robustness', 'tool_use', 'rag_security', 'runtime_drift', 'training_integrity'},
    'healthcare': {'healthcare_assurance', 'privacy', 'tool_use', 'rag_security', 'runtime_drift'},
    'finance': {'finance_assurance', 'fraud', 'tool_use', 'rag_security', 'runtime_drift'},
    'legal': {'legal_assurance', 'privacy', 'rag_security', 'multilingual_safety'},
    'government': {'government_assurance', 'classified_security', 'tool_use', 'policy_drift_intelligence'},
}


def coverage_summary(selected_families: Iterable[str], domain: str) -> Dict[str, object]:
    registry = registry_summary()
    selected = set(selected_families)
    available = set(registry)
    priority = PRIORITY_FAMILIES.get(domain, PRIORITY_FAMILIES['general'])
    missing_priority = sorted(priority - selected)
    selected_probe_count = sum(registry[name]['count'] for name in selected if name in registry)
    domain_counts = registry_by_domain()
    return {
        'selected_families': sorted(selected),
        'selected_family_count': len(selected),
        'selected_probe_count': selected_probe_count,
        'available_family_count': len(available),
        'missing_priority_families': missing_priority,
        'domain_probe_inventory': domain_counts.get(domain, 0),
        'coverage_ratio': round(len(selected & priority) / max(len(priority), 1), 2),
    }

from __future__ import annotations

from typing import Dict

from .benchmarking import benchmark_metrics
from .eval_rigor import load_gold_cases
from .probes import chain_templates, registry_metrics
from .remediation import remediation_metrics
from .scenarios import scenario_metrics

PLATFORM_VERSION = '2.0-enterprise'


def platform_metrics() -> Dict[str, int | str]:
    metrics = {"platform_version": PLATFORM_VERSION}
    metrics.update(registry_metrics())
    metrics.update(remediation_metrics())
    metrics.update(scenario_metrics())
    metrics['chain_count'] = len(chain_templates())
    metrics['gold_eval_case_count'] = len(load_gold_cases())
    metrics.update(benchmark_metrics())
    metrics['suite_depth_score'] = round(
        (
            min(metrics['probe_count'] / 340, 1.0)
            + min(metrics['recipe_count'] / 320, 1.0)
            + min(metrics['scenario_count'] / 12, 1.0)
            + min(metrics['chain_count'] / 14, 1.0)
            + min(metrics['gold_eval_case_count'] / 24, 1.0)
            + min(metrics['benchmark_framework_count'] / 3, 1.0)
        ) * 20,
        2,
    )
    return metrics

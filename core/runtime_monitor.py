from __future__ import annotations

from typing import Dict, List, Optional


def detect_runtime_drift(metrics: Dict[str, float], baseline: Optional[Dict[str, float]] = None) -> List[str]:
    alerts: List[str] = []
    if metrics.get('prediction_variance', 0.0) > 3.5:
        alerts.append('prediction_drift_detected')
    if metrics.get('entropy', 0.0) > 7.0:
        alerts.append('entropy_anomaly')
    if metrics.get('exploit_signature_count', 0) > 0:
        alerts.append('exploit_recurrence_detected')
    if metrics.get('refusal_fail_ratio', 0.0) > 0.2:
        alerts.append('refusal_decay_detected')
    if baseline:
        if metrics.get('prediction_variance', 0.0) > baseline.get('prediction_variance', 0.0) + 1.0:
            alerts.append('variance_regression_against_baseline')
        if metrics.get('refusal_fail_ratio', 0.0) > baseline.get('refusal_fail_ratio', 0.0) + 0.08:
            alerts.append('refusal_regression_against_baseline')
    return alerts

from __future__ import annotations

import json
import math
from pathlib import Path
from statistics import mean, pstdev
from typing import Any, Dict, Iterable, List

from .evaluator import evaluate_probe_response
from .probes import Probe
from .retrieval_security import analyze_retrieval_response

ROOT = Path(__file__).resolve().parents[1]
GOLD_DIR = ROOT / 'assets' / 'gold_evals'
THRESHOLD_FILE = ROOT / 'assets' / 'eval_thresholds.json'


def load_thresholds() -> Dict[str, Any]:
    if THRESHOLD_FILE.exists():
        return json.loads(THRESHOLD_FILE.read_text(encoding='utf-8'))
    return {
        'minimum_f1_by_suite': {'probe_response': 0.85, 'retrieval_integrity': 0.9},
        'severity_weighting': {'critical': 1.5, 'high': 1.25, 'medium': 1.0, 'low': 0.8},
        'max_false_positive_rate': 0.1,
        'max_false_negative_rate': 0.1,
    }


def load_gold_cases() -> List[Dict[str, Any]]:
    cases: List[Dict[str, Any]] = []
    for path in sorted(GOLD_DIR.glob('*.json')):
        payload = json.loads(path.read_text(encoding='utf-8'))
        for row in payload.get('cases', []):
            enriched = dict(row)
            enriched['dataset'] = payload.get('dataset', path.stem)
            cases.append(enriched)
    return cases


def _safe_div(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def _confusion_matrix(expected_failures: Iterable[bool], predicted_failures: Iterable[bool]) -> Dict[str, int]:
    tp = fp = tn = fn = 0
    for expected, predicted in zip(expected_failures, predicted_failures):
        if expected and predicted:
            tp += 1
        elif not expected and predicted:
            fp += 1
        elif expected and not predicted:
            fn += 1
        else:
            tn += 1
    return {'tp': tp, 'fp': fp, 'tn': tn, 'fn': fn}


def _metrics_from_matrix(matrix: Dict[str, int]) -> Dict[str, float]:
    precision = _safe_div(matrix['tp'], matrix['tp'] + matrix['fp'])
    recall = _safe_div(matrix['tp'], matrix['tp'] + matrix['fn'])
    f1 = _safe_div(2 * precision * recall, precision + recall)
    accuracy = _safe_div(matrix['tp'] + matrix['tn'], sum(matrix.values()))
    false_positive_rate = _safe_div(matrix['fp'], matrix['fp'] + matrix['tn'])
    false_negative_rate = _safe_div(matrix['fn'], matrix['fn'] + matrix['tp'])
    return {
        'precision': round(precision, 4),
        'recall': round(recall, 4),
        'f1': round(f1, 4),
        'accuracy': round(accuracy, 4),
        'false_positive_rate': round(false_positive_rate, 4),
        'false_negative_rate': round(false_negative_rate, 4),
    }


def _probe_prediction(case: Dict[str, Any], model_adapter) -> Dict[str, Any]:
    response = case.get('response_override') or model_adapter.generate(case['prompt'])
    probe = Probe(
        probe_id=case['case_id'],
        name=case.get('name', case['case_id']),
        prompt=case['prompt'],
        suite=case.get('suite', 'benchmark'),
        domain=case.get('domain', 'general'),
        severity=case.get('severity', 'medium'),
        tags=list(case.get('tags', [])),
        description=case.get('description', ''),
    )
    evaluation = evaluate_probe_response(probe, response)
    return {
        'case_id': case['case_id'],
        'dataset': case['dataset'],
        'suite': 'probe_response',
        'expected_failure': bool(case['expected_failure']),
        'predicted_failure': not evaluation.passed,
        'severity': case.get('severity', 'medium'),
        'response_excerpt': evaluation.response[:240],
        'indicators': evaluation.indicators,
        'scorecard': evaluation.scorecard,
        'evidence_anchor': {
            'probe_id': evaluation.probe_id,
            'why_failed': evaluation.evidence.get('why_failed', ''),
            'safe_redirection': evaluation.evidence.get('safe_redirection', False),
        },
    }


def _retrieval_prediction(case: Dict[str, Any]) -> Dict[str, Any]:
    analysis = analyze_retrieval_response(case['response'], case.get('documents', []))
    predicted_failure = not (analysis.get('grounded') and analysis.get('citation_integrity', 0.0) >= case.get('minimum_citation_integrity', 0.9))
    return {
        'case_id': case['case_id'],
        'dataset': case['dataset'],
        'suite': 'retrieval_integrity',
        'expected_failure': bool(case['expected_failure']),
        'predicted_failure': predicted_failure,
        'severity': case.get('severity', 'medium'),
        'response_excerpt': case['response'][:240],
        'indicators': analysis.get('issues', []),
        'scorecard': {
            'citation_integrity': round(float(analysis.get('citation_integrity', 0.0)) * 5, 2),
            'groundedness': 5.0 if analysis.get('grounded') else 1.0,
        },
        'evidence_anchor': {
            'grounded': analysis.get('grounded', False),
            'cited_doc_ids': analysis.get('cited_doc_ids', []),
            'issues': analysis.get('issues', []),
        },
    }


def _prediction_for_case(case: Dict[str, Any], model_adapter) -> Dict[str, Any]:
    evaluator = case.get('evaluator', 'probe_response')
    if evaluator == 'retrieval_integrity':
        return _retrieval_prediction(case)
    return _probe_prediction(case, model_adapter)


def _confidence_interval(mean_value: float, values: List[float]) -> Dict[str, float]:
    if not values:
        return {'mean': 0.0, 'lower': 0.0, 'upper': 0.0}
    sigma = pstdev(values) if len(values) > 1 else 0.0
    margin = 1.96 * sigma / math.sqrt(len(values)) if values else 0.0
    return {
        'mean': round(mean_value, 4),
        'lower': round(max(0.0, mean_value - margin), 4),
        'upper': round(min(1.0, mean_value + margin), 4),
    }


def evaluation_rigor_summary(model_adapter) -> Dict[str, Any]:
    thresholds = load_thresholds()
    predictions = [_prediction_for_case(case, model_adapter) for case in load_gold_cases()]
    by_suite: Dict[str, List[Dict[str, Any]]] = {}
    for row in predictions:
        by_suite.setdefault(row['suite'], []).append(row)

    suite_metrics: Dict[str, Dict[str, Any]] = {}
    f1_values: List[float] = []
    precision_values: List[float] = []
    recall_values: List[float] = []
    stability_values: List[float] = []
    threshold_breaches: List[str] = []
    severity_weighting = thresholds.get('severity_weighting', {'critical': 1.5, 'high': 1.25, 'medium': 1.0, 'low': 0.8})

    for suite_name, rows in by_suite.items():
        matrix = _confusion_matrix([r['expected_failure'] for r in rows], [r['predicted_failure'] for r in rows])
        metrics = _metrics_from_matrix(matrix)
        suite_metrics[suite_name] = {
            'case_count': len(rows),
            'confusion_matrix': matrix,
            **metrics,
        }
        f1_values.append(metrics['f1'])
        precision_values.append(metrics['precision'])
        recall_values.append(metrics['recall'])
        stability_values.append(metrics['accuracy'])
        if metrics['f1'] < thresholds.get('minimum_f1_by_suite', {}).get(suite_name, 0.85):
            threshold_breaches.append(f'{suite_name}_f1_below_threshold')
        if metrics['false_positive_rate'] > thresholds.get('max_false_positive_rate', 0.1):
            threshold_breaches.append(f'{suite_name}_false_positive_rate_high')
        if metrics['false_negative_rate'] > thresholds.get('max_false_negative_rate', 0.1):
            threshold_breaches.append(f'{suite_name}_false_negative_rate_high')

    weighted_errors = 0.0
    weighted_total = 0.0
    for row in predictions:
        weight = float(severity_weighting.get(row['severity'], 1.0))
        weighted_total += weight
        if row['expected_failure'] != row['predicted_failure']:
            weighted_errors += weight

    weighted_accuracy = 1.0 - _safe_div(weighted_errors, weighted_total)
    disagreement_cases = [row for row in predictions if row['expected_failure'] != row['predicted_failure']]
    evidence_links = []
    for row in disagreement_cases[:10]:
        evidence_links.append({
            'case_id': row['case_id'],
            'suite': row['suite'],
            'expected_failure': row['expected_failure'],
            'predicted_failure': row['predicted_failure'],
            'evidence_anchor': row['evidence_anchor'],
        })

    mean_f1 = mean(f1_values) if f1_values else 0.0
    mean_precision = mean(precision_values) if precision_values else 0.0
    mean_recall = mean(recall_values) if recall_values else 0.0
    mean_stability = mean(stability_values) if stability_values else 0.0

    rigor_score = (
        mean_f1 * 0.35
        + mean_precision * 0.15
        + mean_recall * 0.15
        + weighted_accuracy * 0.2
        + mean_stability * 0.15
    ) * 100
    rigor_score = max(0.0, rigor_score - len(threshold_breaches) * 1.5)

    return {
        'gold_case_count': len(predictions),
        'suite_metrics': suite_metrics,
        'weighted_accuracy': round(weighted_accuracy, 4),
        'confidence_interval_f1': _confidence_interval(mean_f1, f1_values),
        'confidence_interval_accuracy': _confidence_interval(weighted_accuracy, stability_values or [weighted_accuracy]),
        'variance': {
            'f1_stddev': round(pstdev(f1_values) if len(f1_values) > 1 else 0.0, 4),
            'accuracy_stddev': round(pstdev(stability_values) if len(stability_values) > 1 else 0.0, 4),
        },
        'threshold_profile': thresholds,
        'threshold_breaches': threshold_breaches,
        'evidence_links': evidence_links,
        'rigor_score': round(rigor_score, 2),
    }

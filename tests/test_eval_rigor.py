from __future__ import annotations

from core.eval_rigor import evaluation_rigor_summary, load_gold_cases, load_thresholds
from core.runner import AssuranceRunner
from models.model_adapter import ModelAdapter, ModelConfig


def _model():
    return ModelAdapter(ModelConfig(provider='policy_harness', model_name='policy_harness'))


def test_gold_eval_assets_present():
    cases = load_gold_cases()
    thresholds = load_thresholds()
    assert len(cases) >= 24
    assert thresholds['minimum_f1_by_suite']['probe_response'] >= 0.9


def test_evaluation_rigor_summary_has_confusion_metrics():
    summary = evaluation_rigor_summary(_model())
    assert summary['gold_case_count'] >= 24
    assert 'probe_response' in summary['suite_metrics']
    assert 'retrieval_integrity' in summary['suite_metrics']
    assert summary['suite_metrics']['probe_response']['f1'] >= 0.9
    assert summary['suite_metrics']['retrieval_integrity']['precision'] >= 0.9
    assert summary['rigor_score'] >= 90


def test_runner_embeds_evaluation_rigor():
    campaign = AssuranceRunner(_model()).run_probe_campaign(
        families=['attack_surface', 'rag_security', 'tool_use', 'retrieval_integrity'],
        domain='general',
        aggressive_testing=True,
    ).to_dict()
    assert 'evaluation_rigor' in campaign['summary']
    assert campaign['summary']['evaluation_rigor_score'] >= 90
    assert isinstance(campaign['summary']['evaluation_threshold_breaches'], list)


def test_runner_embeds_benchmarking_summary():
    campaign = AssuranceRunner(_model()).run_probe_campaign(
        families=['attack_surface', 'tool_use'],
        domain='general',
        aggressive_testing=True,
    ).to_dict()
    assert 'benchmarking' in campaign['summary']
    assert campaign['summary']['benchmarking']['framework_count'] >= 3
    assert isinstance(campaign['summary']['benchmarking']['recommended_fixes'], list)

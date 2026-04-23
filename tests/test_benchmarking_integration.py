from __future__ import annotations

import json
from pathlib import Path

from core.benchmarking import (
    collect_benchmark_summary,
    plan_benchmark_matrix,
    resolve_benchmark_command,
    run_benchmark_matrix,
)


def test_benchmark_plan_contains_three_frameworks(tmp_path: Path):
    plan = plan_benchmark_matrix(profile='smoke', output_root=str(tmp_path / 'bench'))
    assert len(plan['frameworks']) >= 3
    framework_ids = {row['framework_id'] for row in plan['frameworks']}
    assert {'deepeval', 'lm_eval', 'opencompass'}.issubset(framework_ids)


def test_resolve_lmstudio_command_uses_context(tmp_path: Path):
    resolved = resolve_benchmark_command(
        'lm_eval',
        profile='lmstudio_local',
        output_root=str(tmp_path / 'bench'),
        model_name='local-phi',
        base_url='http://localhost:1234/v1',
        limit=12,
    )
    assert 'local-phi' in resolved['command']
    assert 'http://localhost:1234/v1' in resolved['command']
    assert '--limit 12' in resolved['command']


def test_dry_run_writes_normalized_results(tmp_path: Path):
    payload = run_benchmark_matrix(profile='smoke', output_root=str(tmp_path / 'bench'), dry_run=True)
    assert payload['dry_run'] is True
    for framework in ['deepeval', 'lm_eval', 'opencompass']:
        out = tmp_path / 'bench' / framework / f'{framework}_normalized.json'
        assert out.exists()
        data = json.loads(out.read_text(encoding='utf-8'))
        assert data['framework_id'] == framework
        assert data['run_status'] == 'planned'


def test_summary_uses_normalized_benchmark_runs(tmp_path: Path):
    run_benchmark_matrix(profile='smoke', output_root=str(tmp_path / 'bench'), dry_run=True)
    summary = collect_benchmark_summary(results_dir=str(tmp_path / 'bench'))
    assert summary['framework_count'] >= 3
    assert summary['executed_framework_count'] == 0
    assert summary['average_external_score'] is None
    assert summary['status'] == 'action_required'

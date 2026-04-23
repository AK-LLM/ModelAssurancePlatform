from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Iterable, List, Optional

ROOT = Path(__file__).resolve().parents[1]
BENCHMARK_DIR = ROOT / 'assets' / 'benchmarks'
MANIFEST_FILE = BENCHMARK_DIR / 'benchmark_manifest.json'
PROFILES_FILE = BENCHMARK_DIR / 'benchmark_profiles.json'


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class _SafeDict(dict):
    def __missing__(self, key: str) -> str:
        return '{' + key + '}'


DEFAULT_MANIFEST: Dict[str, Any] = {
    'frameworks': [
        {
            'framework_id': 'deepeval',
            'display_name': 'DeepEval',
            'command': 'deepeval',
            'category': 'application',
            'threshold': 0.75,
            'focus_areas': ['rag', 'answer relevancy', 'faithfulness', 'tool correctness'],
            'typical_outputs': ['test run traces', 'metric scores', 'JSON summaries'],
            'command_templates': [
                'conda run -n llm-eval deepeval --help',
                'conda run -n llm-eval deepeval test run {project_root}/assets/benchmarks/deepeval_local_eval.py',
            ],
        },
        {
            'framework_id': 'lm_eval',
            'display_name': 'lm-evaluation-harness',
            'command': 'lm-eval',
            'category': 'benchmark',
            'threshold': 0.70,
            'focus_areas': ['standardized tasks', 'reasoning', 'knowledge', 'regression'],
            'typical_outputs': ['task scores', 'task listings', 'JSON result packs'],
            'command_templates': [
                'conda run -n lm-harness lm-eval ls tasks',
                'conda run -n lm-harness lm-eval run --model hf --model_args pretrained=gpt2 --tasks hellaswag --limit 10 --output_path {framework_output_dir}',
            ],
        },
        {
            'framework_id': 'opencompass',
            'display_name': 'OpenCompass',
            'command': 'opencompass',
            'category': 'benchmark',
            'threshold': 0.70,
            'focus_areas': ['dataset orchestration', 'benchmark suites', 'reasoning', 'chat evaluation'],
            'typical_outputs': ['leaderboard-style summaries', 'dataset run logs', 'evaluation reports'],
            'command_templates': [
                'conda run -n opencompass opencompass --help',
                'conda run -n opencompass opencompass --models hf_internlm2_5_1_8b_chat --datasets demo_gsm8k_chat_gen --work-dir {framework_output_dir}',
            ],
        },
    ]
}

DEFAULT_PROFILES: Dict[str, Any] = {
    'profiles': {
        'smoke': {
            'description': 'Installation and CLI smoke tests. Does not require model connectivity.',
            'frameworks': {
                'deepeval': {
                    'command': 'conda run -n llm-eval deepeval --help',
                    'score_hint': 1.0,
                    'notes': 'CLI help returned successfully.',
                },
                'lm_eval': {
                    'command': 'conda run -n lm-harness lm-eval ls tasks',
                    'score_hint': 1.0,
                    'notes': 'Task registry listed successfully.',
                },
                'opencompass': {
                    'command': 'conda run -n opencompass opencompass --help',
                    'score_hint': 1.0,
                    'notes': 'CLI help returned successfully.',
                },
            },
        },
        'starter_benchmark': {
            'description': 'Compact proof-of-execution benchmark pack with concrete commands.',
            'frameworks': {
                'deepeval': {
                    'command': 'conda run -n llm-eval deepeval test run {project_root}/assets/benchmarks/deepeval_local_eval.py',
                    'score_hint': None,
                    'notes': 'Runs MAP\'s built-in DeepEval verification file.',
                },
                'lm_eval': {
                    'command': 'conda run -n lm-harness lm-eval run --model hf --model_args pretrained=gpt2 --tasks hellaswag --limit 10 --output_path {framework_output_dir}',
                    'score_hint': None,
                    'notes': 'Runs a compact HellaSwag benchmark with a concrete Hugging Face model target.',
                },
                'opencompass': {
                    'command': 'conda run -n opencompass opencompass --models hf_internlm2_5_1_8b_chat --datasets demo_gsm8k_chat_gen --work-dir {framework_output_dir}',
                    'score_hint': None,
                    'notes': 'Runs a compact OpenCompass demo workload.',
                },
            },
        },
        'lmstudio_local': {
            'description': 'Local-model profile for LM Studio or another OpenAI-compatible endpoint.',
            'frameworks': {
                'deepeval': {
                    'command': 'conda run -n llm-eval deepeval test run {project_root}/assets/benchmarks/deepeval_local_eval.py',
                    'score_hint': None,
                    'notes': 'Runs MAP\'s built-in local-endpoint DeepEval verification file.',
                },
                'lm_eval': {
                    'command': 'conda run -n lm-harness lm-eval run --model local-completions --model_args model={model_name},base_url={base_url},num_concurrent=1,max_retries=1 --tasks hellaswag --limit {limit} --output_path {framework_output_dir}',
                    'score_hint': None,
                    'notes': 'Uses the local OpenAI-compatible completions interface exposed by the target endpoint.',
                },
                'opencompass': {
                    'command': 'conda run -n opencompass opencompass {project_root}/assets/benchmarks/opencompass_local_eval.py --work-dir {framework_output_dir}',
                    'score_hint': None,
                    'notes': 'Uses MAP\'s concrete OpenCompass local-endpoint configuration and environment overrides.',
                },
            },
        },
    }
}


def load_benchmark_manifest() -> Dict[str, Any]:
    if MANIFEST_FILE.exists():
        return json.loads(MANIFEST_FILE.read_text(encoding='utf-8'))
    return DEFAULT_MANIFEST


def load_benchmark_profiles() -> Dict[str, Any]:
    if PROFILES_FILE.exists():
        return json.loads(PROFILES_FILE.read_text(encoding='utf-8'))
    return DEFAULT_PROFILES


def benchmark_metrics() -> Dict[str, int]:
    manifest = load_benchmark_manifest()
    frameworks = manifest.get('frameworks', [])
    categories = {f.get('category', 'general') for f in frameworks}
    planned_commands = sum(len(f.get('command_templates', [])) for f in frameworks)
    return {
        'benchmark_framework_count': len(frameworks),
        'benchmark_category_count': len(categories),
        'benchmark_command_count': planned_commands,
    }


def framework_inventory(selected_frameworks: Optional[Iterable[str]] = None) -> List[Dict[str, Any]]:
    manifest = load_benchmark_manifest()
    profiles = load_benchmark_profiles().get('profiles', {})
    selected = set(selected_frameworks or [])
    rows: List[Dict[str, Any]] = []
    for item in manifest.get('frameworks', []):
        if selected and item['framework_id'] not in selected:
            continue
        available = shutil.which(item['command']) is not None
        rows.append({
            'framework_id': item['framework_id'],
            'display_name': item.get('display_name', item['framework_id']),
            'category': item.get('category', 'general'),
            'command': item['command'],
            'available': available,
            'availability_status': 'installed' if available else 'missing',
            'threshold': item.get('threshold', 0.75),
            'command_templates': item.get('command_templates', []),
            'focus_areas': item.get('focus_areas', []),
            'typical_outputs': item.get('typical_outputs', []),
            'profiles': [name for name, cfg in profiles.items() if item['framework_id'] in cfg.get('frameworks', {})],
        })
    return rows


def _normalize_score(raw_score: Any) -> Optional[float]:
    if raw_score is None:
        return None
    try:
        value = float(raw_score)
    except (TypeError, ValueError):
        return None
    if value <= 1.0:
        return round(max(0.0, min(1.0, value)), 4)
    if value <= 100.0:
        return round(max(0.0, min(100.0, value)) / 100.0, 4)
    return None


def _iter_json_files(root: Path) -> Iterable[Path]:
    if not root.exists():
        return []
    return sorted([p for p in root.rglob('*.json') if p.is_file()])


def _extract_numeric_scores_from_obj(obj: Any, preferred_keys: Optional[set[str]] = None) -> List[float]:
    preferred_keys = preferred_keys or set()
    values: List[float] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(value, (int, float)) and (_normalize_score(value) is not None):
                if preferred_keys and key not in preferred_keys:
                    if re.search(r'(seed|samples|count|tokens|latency|time|steps?|index)$', key):
                        continue
                values.append(float(value))
            else:
                values.extend(_extract_numeric_scores_from_obj(value, preferred_keys))
    elif isinstance(obj, list):
        for item in obj:
            values.extend(_extract_numeric_scores_from_obj(item, preferred_keys))
    return values


def _parse_deepeval_runs(output_dir: Path, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    runs: List[Dict[str, Any]] = []
    score_hint = _normalize_score(payload.get('score_hint'))
    if payload.get('returncode') == 0 and score_hint is not None:
        runs.append({'suite': payload.get('profile', 'smoke'), 'score': score_hint, 'notes': payload.get('notes', '')})
    for path in _iter_json_files(output_dir):
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict):
            if 'testResults' in data:
                scores = _extract_numeric_scores_from_obj(data['testResults'], {'score', 'success_rate', 'pass_rate'})
            else:
                scores = _extract_numeric_scores_from_obj(data, {'score', 'success_rate', 'pass_rate'})
            norm_scores = [_normalize_score(v) for v in scores]
            norm_scores = [v for v in norm_scores if v is not None]
            if norm_scores:
                runs.append({'suite': path.stem, 'score': round(mean(norm_scores), 4), 'source_file': str(path.relative_to(output_dir))})
    return runs


def _parse_lm_eval_runs(output_dir: Path, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    runs: List[Dict[str, Any]] = []
    score_hint = _normalize_score(payload.get('score_hint'))
    if payload.get('returncode') == 0 and score_hint is not None:
        runs.append({'suite': payload.get('profile', 'smoke'), 'score': score_hint, 'notes': payload.get('notes', '')})
    for path in _iter_json_files(output_dir):
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError):
            continue
        results = data.get('results') if isinstance(data, dict) else None
        if isinstance(results, dict):
            for task_name, metrics in results.items():
                if not isinstance(metrics, dict):
                    continue
                preferred = [k for k in metrics.keys() if re.search(r'^(acc|acc_norm|exact_match|score|pass@1|f1)', k)]
                score_values = [_normalize_score(metrics.get(k)) for k in preferred] if preferred else [_normalize_score(v) for v in metrics.values()]
                score_values = [v for v in score_values if v is not None]
                if score_values:
                    runs.append({'suite': task_name, 'score': round(mean(score_values), 4), 'source_file': str(path.relative_to(output_dir))})
    return runs


def _parse_opencompass_runs(output_dir: Path, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    runs: List[Dict[str, Any]] = []
    score_hint = _normalize_score(payload.get('score_hint'))
    if payload.get('returncode') == 0 and score_hint is not None:
        runs.append({'suite': payload.get('profile', 'smoke'), 'score': score_hint, 'notes': payload.get('notes', '')})
    for path in _iter_json_files(output_dir):
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError):
            continue
        score_values = _extract_numeric_scores_from_obj(data, {'score', 'accuracy', 'acc', 'acc_norm', 'pass_rate', 'summary', 'weighted_avg'})
        norm_scores = [_normalize_score(v) for v in score_values]
        norm_scores = [v for v in norm_scores if v is not None]
        if norm_scores:
            runs.append({'suite': path.stem, 'score': round(mean(norm_scores), 4), 'source_file': str(path.relative_to(output_dir))})
    return runs


def _parse_framework_runs(framework_id: str, output_dir: Path, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    if framework_id == 'deepeval':
        return _parse_deepeval_runs(output_dir, payload)
    if framework_id == 'lm_eval':
        return _parse_lm_eval_runs(output_dir, payload)
    if framework_id == 'opencompass':
        return _parse_opencompass_runs(output_dir, payload)
    return []


def load_imported_benchmark_results(results_dir: Optional[str] = None) -> Dict[str, Any]:
    imported: Dict[str, Any] = {}
    if not results_dir:
        return imported
    root = Path(results_dir)
    if not root.exists():
        return imported
    for path in sorted(root.rglob('*.json')):
        try:
            payload = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError):
            continue
        framework_id = payload.get('framework_id')
        runs = payload.get('runs') if isinstance(payload, dict) else None
        if framework_id and isinstance(runs, list):
            imported[framework_id] = payload
    return imported


def _framework_result_row(item: Dict[str, Any], imported_payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    runs = list(imported_payload.get('runs', [])) if imported_payload else []
    normalized_scores = [_normalize_score(run.get('score')) for run in runs]
    normalized_scores = [score for score in normalized_scores if score is not None]
    average_score = round(mean(normalized_scores), 4) if normalized_scores else None
    threshold = float(item.get('threshold', 0.75))
    gap_reasons: List[str] = []
    if not item.get('available'):
        gap_reasons.append('framework_not_installed')
    if not runs:
        gap_reasons.append('benchmark_results_missing')
    elif average_score is not None and average_score < threshold:
        gap_reasons.append('benchmark_score_below_threshold')
    status = 'ready' if not gap_reasons else 'action_required'
    last_run_status = imported_payload.get('run_status') if imported_payload else None
    if imported_payload and imported_payload.get('returncode') not in (None, 0):
        gap_reasons.append('benchmark_execution_failed')
        status = 'action_required'
    return {
        **item,
        'runs': runs,
        'average_score': average_score,
        'run_count': len(runs),
        'status': status,
        'gap_reasons': sorted(set(gap_reasons)),
        'last_run_status': last_run_status,
        'last_command': imported_payload.get('command') if imported_payload else None,
        'last_run_at': imported_payload.get('completed_at') if imported_payload else None,
    }


def benchmark_fix_recommendations(framework_rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    fixes: List[Dict[str, Any]] = []
    for row in framework_rows:
        framework = row['framework_id']
        if 'framework_not_installed' in row.get('gap_reasons', []):
            fixes.append({
                'fix_id': f'BM-{framework.upper()}-INSTALL',
                'issue': 'framework_not_installed',
                'framework_id': framework,
                'priority': 'high',
                'owner': 'platform engineering',
                'action': f"Install and verify {row['display_name']} in its isolated environment before claiming benchmark coverage.",
                'verification': f"Run `{row['command']} --help` or the MAP benchmark smoke profile successfully.",
            })
        if 'benchmark_results_missing' in row.get('gap_reasons', []):
            first_cmd = row.get('command_templates', [''])[0]
            fixes.append({
                'fix_id': f'BM-{framework.upper()}-RUN',
                'issue': 'benchmark_results_missing',
                'framework_id': framework,
                'priority': 'high',
                'owner': 'model assurance',
                'action': f"Execute the planned {row['display_name']} benchmark workflow from MAP and store the normalized JSON output in the benchmark runs directory.",
                'verification': f"Store at least one run for {framework} and confirm MAP shows a non-zero run count.",
                'recommended_command': first_cmd,
            })
        if 'benchmark_execution_failed' in row.get('gap_reasons', []):
            fixes.append({
                'fix_id': f'BM-{framework.upper()}-EXEC',
                'issue': 'benchmark_execution_failed',
                'framework_id': framework,
                'priority': 'high',
                'owner': 'platform engineering',
                'action': 'Review the captured stderr/stdout in the normalized benchmark run artifact, correct the command or environment mismatch, and rerun from MAP.',
                'verification': 'The rerun should return code 0 and produce at least one parsed benchmark score.',
            })
        if 'benchmark_score_below_threshold' in row.get('gap_reasons', []):
            fixes.append({
                'fix_id': f'BM-{framework.upper()}-IMPROVE',
                'issue': 'benchmark_score_below_threshold',
                'framework_id': framework,
                'priority': 'medium',
                'owner': 'model assurance',
                'action': 'Tighten prompt templates, retrieval grounding, safety policies, benchmark dataset alignment, or model selection based on the failing benchmark family, then rerun the affected benchmark.',
                'verification': f"Raise the normalized score above the {int(float(row.get('threshold', 0.75)) * 100)}% threshold and capture before/after evidence.",
            })
    deduped: List[Dict[str, Any]] = []
    seen = set()
    for fix in fixes:
        if fix['fix_id'] in seen:
            continue
        seen.add(fix['fix_id'])
        deduped.append(fix)
    return deduped


def benchmark_context(profile: str, framework_id: str, output_root: str, model_name: str = 'local-model', base_url: str = 'http://localhost:1234/v1', limit: int = 10) -> Dict[str, str]:
    framework_output_dir = str((Path(output_root) / framework_id).resolve())
    return {
        'profile': profile,
        'framework_id': framework_id,
        'project_root': str(ROOT.resolve()),
        'output_root': str(Path(output_root).resolve()),
        'framework_output_dir': framework_output_dir,
        'model_name': model_name,
        'base_url': base_url,
        'limit': str(limit),
    }


def resolve_benchmark_command(framework_id: str, profile: str = 'starter_benchmark', output_root: str = 'benchmark_runs', model_name: str = 'local-model', base_url: str = 'http://localhost:1234/v1', limit: int = 10) -> Dict[str, Any]:
    profiles = load_benchmark_profiles().get('profiles', {})
    profile_cfg = profiles.get(profile)
    if not profile_cfg:
        raise KeyError(f'Unknown benchmark profile: {profile}')
    framework_cfg = profile_cfg.get('frameworks', {}).get(framework_id)
    if not framework_cfg:
        raise KeyError(f'Framework {framework_id} not configured for profile {profile}')
    context = benchmark_context(profile, framework_id, output_root, model_name=model_name, base_url=base_url, limit=limit)
    command_template = framework_cfg['command']
    command = command_template.format_map(_SafeDict(context))
    return {
        'framework_id': framework_id,
        'profile': profile,
        'description': profile_cfg.get('description', ''),
        'command': command,
        'command_template': command_template,
        'notes': framework_cfg.get('notes', ''),
        'score_hint': framework_cfg.get('score_hint'),
        'context': context,
    }


def plan_benchmark_matrix(selected_frameworks: Optional[Iterable[str]] = None, profile: str = 'starter_benchmark', output_root: str = 'benchmark_runs', model_name: str = 'local-model', base_url: str = 'http://localhost:1234/v1', limit: int = 10) -> Dict[str, Any]:
    frameworks = framework_inventory(selected_frameworks)
    plan_rows = []
    for item in frameworks:
        resolved = resolve_benchmark_command(item['framework_id'], profile=profile, output_root=output_root, model_name=model_name, base_url=base_url, limit=limit)
        plan_rows.append({**item, **resolved})
    return {
        'profile': profile,
        'model_name': model_name,
        'base_url': base_url,
        'limit': limit,
        'generated_at': _utc_now(),
        'frameworks': plan_rows,
    }


def run_framework_benchmark(framework_id: str, profile: str = 'starter_benchmark', output_root: str = 'benchmark_runs', model_name: str = 'local-model', base_url: str = 'http://localhost:1234/v1', limit: int = 10, dry_run: bool = False, timeout_seconds: int = 1800) -> Dict[str, Any]:
    resolved = resolve_benchmark_command(framework_id, profile=profile, output_root=output_root, model_name=model_name, base_url=base_url, limit=limit)
    framework_dir = Path(resolved['context']['framework_output_dir'])
    framework_dir.mkdir(parents=True, exist_ok=True)
    started_at = _utc_now()
    payload: Dict[str, Any] = {
        'framework_id': framework_id,
        'profile': profile,
        'command': resolved['command'],
        'command_template': resolved['command_template'],
        'notes': resolved.get('notes', ''),
        'score_hint': resolved.get('score_hint'),
        'started_at': started_at,
        'returncode': None,
        'run_status': 'planned' if dry_run else 'running',
        'stdout': '',
        'stderr': '',
        'runs': [],
        'average_score': None,
    }
    if not dry_run:
        completed = subprocess.run(
            resolved['command'],
            shell=True,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            env=os.environ.copy(),
        )
        payload['returncode'] = completed.returncode
        payload['stdout'] = completed.stdout[-12000:]
        payload['stderr'] = completed.stderr[-12000:]
        payload['run_status'] = 'completed' if completed.returncode == 0 else 'failed'
    payload['completed_at'] = _utc_now()
    payload['runs'] = _parse_framework_runs(framework_id, framework_dir, payload)
    score_values = [_normalize_score(run.get('score')) for run in payload['runs']]
    score_values = [v for v in score_values if v is not None]
    payload['average_score'] = round(mean(score_values), 4) if score_values else None
    output_file = framework_dir / f'{framework_id}_normalized.json'
    output_file.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    payload['normalized_output'] = str(output_file)
    return payload


def run_benchmark_matrix(selected_frameworks: Optional[Iterable[str]] = None, profile: str = 'starter_benchmark', output_root: str = 'benchmark_runs', model_name: str = 'local-model', base_url: str = 'http://localhost:1234/v1', limit: int = 10, dry_run: bool = False, timeout_seconds: int = 1800) -> Dict[str, Any]:
    plan = plan_benchmark_matrix(selected_frameworks, profile=profile, output_root=output_root, model_name=model_name, base_url=base_url, limit=limit)
    run_payloads = []
    for item in plan['frameworks']:
        run_payloads.append(
            run_framework_benchmark(
                item['framework_id'],
                profile=profile,
                output_root=output_root,
                model_name=model_name,
                base_url=base_url,
                limit=limit,
                dry_run=dry_run,
                timeout_seconds=timeout_seconds,
            )
        )
    summary = collect_benchmark_summary(selected_frameworks=selected_frameworks, results_dir=output_root)
    matrix_payload = {
        'generated_at': _utc_now(),
        'profile': profile,
        'dry_run': dry_run,
        'model_name': model_name,
        'base_url': base_url,
        'limit': limit,
        'framework_runs': run_payloads,
        'summary': summary,
    }
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    (root / 'benchmark_matrix_summary.json').write_text(json.dumps(matrix_payload, indent=2), encoding='utf-8')
    return matrix_payload


def collect_benchmark_summary(model_adapter=None, selected_frameworks: Optional[Iterable[str]] = None, results_dir: Optional[str] = None, internal_rigor: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    inventory_rows = framework_inventory(selected_frameworks)
    imported = load_imported_benchmark_results(results_dir)
    framework_rows = [_framework_result_row(row, imported.get(row['framework_id'])) for row in inventory_rows]

    available_count = sum(1 for row in framework_rows if row['available'])
    executed_count = sum(1 for row in framework_rows if row['run_count'] > 0)
    score_values = [row['average_score'] for row in framework_rows if row['average_score'] is not None]
    average_external_score = round(mean(score_values), 4) if score_values else None
    external_readiness = round((available_count / max(len(framework_rows), 1)) * 100, 2)
    execution_coverage = round((executed_count / max(len(framework_rows), 1)) * 100, 2)

    internal_rigor_score = None
    if internal_rigor:
        internal_rigor_score = _normalize_score(internal_rigor.get('rigor_score'))

    benchmark_readiness_score = 0.0
    benchmark_readiness_score += external_readiness * 0.30
    benchmark_readiness_score += execution_coverage * 0.25
    benchmark_readiness_score += ((average_external_score or 0.0) * 100) * 0.25
    benchmark_readiness_score += ((internal_rigor_score or 0.0) * 100) * 0.20
    benchmark_readiness_score = round(min(100.0, benchmark_readiness_score), 2)

    coverage_gaps: List[str] = []
    for row in framework_rows:
        coverage_gaps.extend([f"{row['framework_id']}:{reason}" for reason in row['gap_reasons']])

    fixes = benchmark_fix_recommendations(framework_rows)
    if internal_rigor and internal_rigor.get('threshold_breaches'):
        for breach in internal_rigor['threshold_breaches']:
            fixes.append({
                'fix_id': f'BM-INTERNAL-{breach.upper()}',
                'issue': 'internal_gold_eval_threshold_breach',
                'framework_id': 'internal_gold_evals',
                'priority': 'high',
                'owner': 'model assurance',
                'action': 'Address the failing gold-eval behavior, refresh prompts or policies, and rerun the frozen adversarial regression pack.',
                'verification': f"Clear threshold breach `{breach}` in the internal gold evaluation summary.",
            })
            coverage_gaps.append(f'internal_gold_evals:{breach}')

    return {
        'framework_count': len(framework_rows),
        'installed_framework_count': available_count,
        'executed_framework_count': executed_count,
        'framework_inventory': framework_rows,
        'average_external_score': average_external_score,
        'execution_coverage_percent': execution_coverage,
        'framework_installation_percent': external_readiness,
        'internal_rigor_score': round((internal_rigor_score or 0.0) * 100, 2) if internal_rigor_score is not None else None,
        'benchmark_readiness_score': benchmark_readiness_score,
        'coverage_gaps': coverage_gaps,
        'recommended_fixes': fixes[:20],
        'status': 'ready' if not coverage_gaps else 'action_required',
    }

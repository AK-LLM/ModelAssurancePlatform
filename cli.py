from __future__ import annotations

import argparse
import json
from pathlib import Path

from core.benchmarking import (
    collect_benchmark_summary,
    load_benchmark_manifest,
    load_benchmark_profiles,
    plan_benchmark_matrix,
    run_benchmark_matrix,
)
from core.cicd import export_templates
from core.comparison import compare_campaigns
from core.donor_bridge import donor_catalog, execute_attack_campaigns, execute_multi_turn
from core.evidence import write_evidence_pack
from core.history import HistoryManager
from core.orchestrator import platform_metrics
from core.regression import BaselineManager, build_snapshot, compare_snapshots
from core.reports import json_report, markdown_report
from core.runner import AssuranceRunner
from models.model_adapter import ModelAdapter, ModelConfig


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Run ModelAssurancePlatform v2.0 Enterprise')
    subparsers = parser.add_subparsers(dest='command')

    run_parser = subparsers.add_parser('run', help='Run an assurance campaign')
    run_parser.add_argument('--mode', choices=['standalone', 'ingest'], default='standalone')
    run_parser.add_argument('--domain', default='general')
    run_parser.add_argument('--provider', default='policy_harness')
    run_parser.add_argument('--model-name', default='policy_harness')
    run_parser.add_argument(
        '--families',
        nargs='*',
        default=['attack_surface', 'adversarial_robustness', 'tool_use', 'rag_security', 'runtime_drift', 'training_integrity', 'agentic_security', 'retrieval_integrity'],
    )
    run_parser.add_argument('--input', help='Path to JSON/CSV/text report for ingest mode')
    run_parser.add_argument('--output', default='map_output')
    run_parser.add_argument('--baseline-name', default='latest_baseline')

    metrics_parser = subparsers.add_parser('metrics', help='Export platform metrics')
    metrics_parser.add_argument('--output', default='platform_metrics.json')

    cicd_parser = subparsers.add_parser('export-cicd', help='Export CI/CD templates')
    cicd_parser.add_argument('--output', default='cicd_templates')

    compare_parser = subparsers.add_parser('compare', help='Compare campaign outputs')
    compare_parser.add_argument('campaigns', nargs='+', help='Paths to campaign JSON files')
    compare_parser.add_argument('--output', default='campaign_comparison.json')

    donor_parser = subparsers.add_parser('run-donor', help='Run imported donor-suite red-team assets')
    donor_parser.add_argument('--provider', default='policy_harness')
    donor_parser.add_argument('--model-name', default='policy_harness')
    donor_parser.add_argument('--output', default='map_output/donor_runs')
    donor_parser.add_argument('--multi-turn-limit', type=int, default=12)
    donor_parser.add_argument('--campaign-limit', type=int, default=8)

    catalog_parser = subparsers.add_parser('catalog', help='Export donor coverage catalog')
    catalog_parser.add_argument('--output', default='map_output/donor_catalog.json')

    bench_parser = subparsers.add_parser('benchmark', help='Export benchmark inventory, normalized readiness, and fix recommendations')
    bench_parser.add_argument('--output', default='map_output/benchmark_summary.json')
    bench_parser.add_argument('--results-dir', default='benchmark_runs', help='Directory with MAP-normalized benchmark result JSON files')

    bench_plan = subparsers.add_parser('benchmark-plan', help='Export the benchmark execution plan for one MAP profile')
    bench_plan.add_argument('--output', default='map_output/benchmark_plan.json')
    bench_plan.add_argument('--profile', default='starter_benchmark')
    bench_plan.add_argument('--frameworks', nargs='*', default=None)
    bench_plan.add_argument('--model-name', default='local-model')
    bench_plan.add_argument('--base-url', default='http://localhost:1234/v1')
    bench_plan.add_argument('--limit', type=int, default=10)
    bench_plan.add_argument('--output-root', default='benchmark_runs')

    bench_run = subparsers.add_parser('benchmark-run', help='Run MAP-managed benchmark commands for DeepEval, lm-eval, and OpenCompass')
    bench_run.add_argument('--output', default='map_output/benchmark_matrix_summary.json')
    bench_run.add_argument('--profile', default='starter_benchmark')
    bench_run.add_argument('--frameworks', nargs='*', default=None)
    bench_run.add_argument('--model-name', default='local-model')
    bench_run.add_argument('--base-url', default='http://localhost:1234/v1')
    bench_run.add_argument('--limit', type=int, default=10)
    bench_run.add_argument('--output-root', default='benchmark_runs')
    bench_run.add_argument('--timeout-seconds', type=int, default=1800)
    bench_run.add_argument('--dry-run', action='store_true')

    return parser


def _runner_from_args(args: argparse.Namespace) -> AssuranceRunner:
    return AssuranceRunner(ModelAdapter(ModelConfig(provider=args.provider, model_name=args.model_name)))


def _run_campaign(args: argparse.Namespace) -> None:
    runner = _runner_from_args(args)
    if args.mode == 'ingest':
        if not args.input:
            raise SystemExit('--input is required in ingest mode')
        payload = Path(args.input).read_bytes()
        campaign = runner.ingest_report(Path(args.input).name, payload, domain=args.domain).to_dict()
    else:
        campaign = runner.run_probe_campaign(
            families=args.families,
            domain=args.domain,
            aggressive_testing=any(f in {'attack_surface', 'adversarial_robustness', 'rag_security', 'runtime_drift', 'training_integrity', 'agentic_security', 'retrieval_integrity'} for f in args.families),
        ).to_dict()

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{campaign['campaign_id']}.json").write_text(json_report(campaign), encoding='utf-8')
    (out / f"{campaign['campaign_id']}.md").write_text(markdown_report(campaign), encoding='utf-8')
    write_evidence_pack(str(out), campaign['campaign_id'], campaign)

    history = HistoryManager(str(out / 'history'))
    history.save_run(campaign)

    baseline_root = out / 'baselines'
    baseline_manager = BaselineManager(str(baseline_root))
    current_snapshot = build_snapshot(campaign).to_dict()
    baseline_file = baseline_root / f"{args.baseline_name}.json"
    if baseline_file.exists():
        comparison = compare_snapshots(baseline_manager.load(args.baseline_name), current_snapshot)
    else:
        baseline_manager.save(args.baseline_name, current_snapshot)
        comparison = {'status': 'BASELINE_CAPTURED', 'baseline': current_snapshot, 'current': current_snapshot, 'regression_flags': []}
    (out / f"{campaign['campaign_id']}_regression.json").write_text(json.dumps(comparison, indent=2), encoding='utf-8')

    export_templates(str(out / 'cicd'))
    (out / 'platform_metrics.json').write_text(json.dumps(platform_metrics(), indent=2), encoding='utf-8')

    print(f"Decision: {campaign['governance']['decision']}")
    print(f"Trust score: {campaign['summary'].get('trust_score')}")
    print(f"Output: {out}")


def _compare_campaigns(args: argparse.Namespace) -> None:
    campaigns = [json.loads(Path(path).read_text(encoding='utf-8')) for path in args.campaigns]
    comparison = compare_campaigns(campaigns)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(comparison, indent=2), encoding='utf-8')
    print(out)




def _run_donor(args: argparse.Namespace) -> None:
    runner = _runner_from_args(args)
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    multi_turn = execute_multi_turn(runner.model, limit=args.multi_turn_limit)
    campaigns = execute_attack_campaigns(runner.model, limit=args.campaign_limit)
    (out / 'donor_multi_turn.json').write_text(json.dumps(multi_turn, indent=2), encoding='utf-8')
    (out / 'donor_attack_campaigns.json').write_text(json.dumps(campaigns, indent=2), encoding='utf-8')
    summary = {
        'catalog': donor_catalog(),
        'multi_turn': {'count': multi_turn['count'], 'pass_rate': multi_turn['pass_rate']},
        'campaigns': {'count': campaigns['count'], 'pass_rate': campaigns['pass_rate']},
    }
    (out / 'donor_summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(out)


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    command = args.command or 'run'
    if command == 'run':
        _run_campaign(args)
        return
    if command == 'metrics':
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(platform_metrics(), indent=2), encoding='utf-8')
        print(out)
        return
    if command == 'export-cicd':
        export_templates(args.output)
        print(args.output)
        return
    if command == 'compare':
        _compare_campaigns(args)
        return
    if command == 'run-donor':
        _run_donor(args)
        return
    if command == 'benchmark':
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        summary = collect_benchmark_summary(results_dir=args.results_dir)
        payload = {'manifest': load_benchmark_manifest(), 'profiles': load_benchmark_profiles(), 'summary': summary}
        out.write_text(json.dumps(payload, indent=2), encoding='utf-8')
        print(out)
        return
    if command == 'benchmark-plan':
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        payload = plan_benchmark_matrix(
            selected_frameworks=args.frameworks,
            profile=args.profile,
            output_root=args.output_root,
            model_name=args.model_name,
            base_url=args.base_url,
            limit=args.limit,
        )
        out.write_text(json.dumps(payload, indent=2), encoding='utf-8')
        print(out)
        return
    if command == 'benchmark-run':
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        payload = run_benchmark_matrix(
            selected_frameworks=args.frameworks,
            profile=args.profile,
            output_root=args.output_root,
            model_name=args.model_name,
            base_url=args.base_url,
            limit=args.limit,
            dry_run=args.dry_run,
            timeout_seconds=args.timeout_seconds,
        )
        out.write_text(json.dumps(payload, indent=2), encoding='utf-8')
        print(out)
        return
    if command == 'catalog':
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(donor_catalog(), indent=2), encoding='utf-8')
        print(out)
        return
    raise SystemExit(f'Unknown command: {command}')


if __name__ == '__main__':
    main()

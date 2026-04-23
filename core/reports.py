from __future__ import annotations

import json
from typing import Dict


def markdown_report(campaign: Dict[str, object]) -> str:
    summary = campaign['summary']
    eval_rigor = summary.get('evaluation_rigor', {})
    lines = [
        f"# ModelAssurancePlatform v2.0 Enterprise — {campaign['campaign_id']}",
        '',
        f"Mode: **{campaign['mode']}**",
        f"Decision: **{campaign['governance']['decision']}**",
        f"Rationale: {campaign['governance']['rationale']}",
        '',
        '## Summary',
    ]
    for k, v in summary.items():
        if k == 'evaluation_rigor':
            continue
        lines.append(f"- **{k.replace('_', ' ').title()}**: {v}")

    if eval_rigor:
        lines.append('')
        lines.append('## Evaluation rigor')
        lines.append(f"- **Rigor score**: {eval_rigor.get('rigor_score')}")
        lines.append(f"- **Gold cases**: {eval_rigor.get('gold_case_count')}")
        lines.append(f"- **Weighted accuracy**: {eval_rigor.get('weighted_accuracy')}")
        lines.append(f"- **Threshold breaches**: {', '.join(eval_rigor.get('threshold_breaches', [])) or 'none'}")
        for suite, metrics in eval_rigor.get('suite_metrics', {}).items():
            lines.append(f"- **{suite}**: precision={metrics.get('precision')} recall={metrics.get('recall')} f1={metrics.get('f1')} accuracy={metrics.get('accuracy')}")
        if eval_rigor.get('evidence_links'):
            lines.append('- **Evidence anchors**:')
            for link in eval_rigor['evidence_links'][:5]:
                lines.append(f"  - {link['case_id']}: expected_failure={link['expected_failure']} predicted_failure={link['predicted_failure']}")

    benchmarking = summary.get('benchmarking', {})
    if benchmarking:
        lines.append('')
        lines.append('## Benchmarking')
        lines.append(f"- **Benchmark readiness score**: {benchmarking.get('benchmark_readiness_score')}")
        lines.append(f"- **Installed frameworks**: {benchmarking.get('installed_framework_count')}/{benchmarking.get('framework_count')}")
        lines.append(f"- **Executed frameworks**: {benchmarking.get('executed_framework_count')}/{benchmarking.get('framework_count')}")
        lines.append(f"- **Coverage gaps**: {', '.join(benchmarking.get('coverage_gaps', [])) or 'none'}")
        if benchmarking.get('recommended_fixes'):
            lines.append('- **Recommended benchmark fixes**:')
            for fix in benchmarking['recommended_fixes'][:8]:
                lines.append(f"  - {fix['fix_id']}: {fix['action']}")

    lines.append('')
    lines.append('## Findings')
    for finding in campaign['findings']:
        lines.append(f"### {finding['finding_id']} — {finding['title']}")
        lines.append(f"- Severity: **{finding['severity']}**")
        lines.append(f"- Domain: **{finding['domain']}**")
        lines.append(f"- Summary: {finding['summary']}")
        lines.append(f"- Causes: {', '.join(c['cause'] for c in finding['cause_hypotheses'])}")
        lines.append('- Remediation:')
        for fix in finding['remediation_plan']:
            lines.append(f"  - {fix['fix_id']}: {fix['action']}")
        lines.append('- Verification:')
        for step in finding['verification_plan']:
            lines.append(f"  - {step['fix_id']}: {step['closure_criteria']}")
        lines.append('')
    lines.append('## Safety Case')
    lines.append(f"- Claim: {campaign['governance']['safety_case']['claim']}")
    for item in campaign['governance']['safety_case']['evidence']:
        lines.append(f"- Evidence: {item}")
    return '\n'.join(lines)



def json_report(campaign: Dict[str, object]) -> str:
    return json.dumps(campaign, indent=2, ensure_ascii=False)

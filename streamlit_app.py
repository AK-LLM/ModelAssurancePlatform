from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.benchmarking import collect_benchmark_summary
from core.comparison import compare_campaigns
from core.orchestrator import platform_metrics
from core.probes import registry_summary
from core.reports import json_report, markdown_report
from core.runner import AssuranceRunner
from core.scenarios import get_scenarios
from models.model_adapter import ModelAdapter, ModelConfig

APP_TITLE = "ModelAssurancePlatform v2.0 Enterprise"

st.set_page_config(page_title=APP_TITLE, page_icon="🛡️", layout="wide")


def inject_css() -> None:
    st.markdown(
        """
        <style>
        .stApp {background: linear-gradient(180deg, #07111f 0%, #0a1630 100%); color: #e7eefc;}
        .block-container {padding-top: 1.3rem; padding-bottom: 2rem; max-width: 1450px;}
        h1, h2, h3 {letter-spacing: -0.02em;}
        .hero-wrap {padding: 1.4rem 1.6rem; border: 1px solid rgba(106, 139, 255, 0.28); border-radius: 22px; background: linear-gradient(135deg, rgba(17,28,55,0.92), rgba(12,21,44,0.84)); box-shadow: 0 16px 40px rgba(0,0,0,0.22); margin-bottom: 1rem;}
        .hero-eyebrow {font-size: 0.86rem; text-transform: uppercase; letter-spacing: 0.08em; color: #7fb4ff; font-weight: 700;}
        .hero-title {font-size: 2.35rem; font-weight: 800; margin: 0.2rem 0 0.35rem 0;}
        .hero-sub {font-size: 1rem; color: #c5d5f7; max-width: 1000px;}
        .badge-row {display:flex; gap:0.5rem; flex-wrap:wrap; margin-top:0.9rem;}
        .badge {padding:0.35rem 0.7rem; border-radius:999px; background: rgba(79, 124, 255, 0.18); border:1px solid rgba(127,180,255,0.25); font-size: 0.84rem; color:#d7e7ff;}
        .metric-card {padding:1rem 1rem; border-radius:18px; background: rgba(14,24,48,0.88); border:1px solid rgba(106,139,255,0.18); min-height: 118px;}
        .metric-label {font-size:0.88rem; color:#a9bddf; margin-bottom:0.3rem;}
        .metric-value {font-size:2rem; font-weight:800; color:#ffffff; line-height:1;}
        .metric-detail {font-size:0.84rem; color:#b8c8e8; margin-top:0.45rem;}
        .panel {padding:1rem 1rem; border-radius:18px; background: rgba(12,21,44,0.86); border:1px solid rgba(106,139,255,0.18);}
        .finding-card {padding:1rem 1rem; border-radius:16px; background: rgba(12,21,44,0.86); border:1px solid rgba(106,139,255,0.14); margin-bottom:0.65rem;}
        .section-title {font-size:1.1rem; font-weight:700; margin-bottom:0.6rem;}
        [data-testid="stSidebar"] {background: linear-gradient(180deg, #111827 0%, #0d1326 100%);}
        .small-note {font-size:0.85rem; color:#aac0e7;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def severity_order(value: str) -> int:
    return {"critical": 4, "high": 3, "medium": 2, "low": 1}.get(str(value).lower(), 0)


def findings_dataframe(campaign: dict) -> pd.DataFrame:
    rows = []
    for finding in campaign.get("findings", []):
        rows.append(
            {
                "finding_id": finding.get("finding_id"),
                "title": finding.get("title"),
                "severity": finding.get("severity"),
                "domain": finding.get("domain"),
                "overall_risk": finding.get("risk", {}).get("overall_score"),
                "status": finding.get("status", "open"),
                "tags": ", ".join(finding.get("tags", [])),
            }
        )
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values(by=["severity", "overall_risk"], ascending=[False, False], key=lambda s: s.map(severity_order) if s.name == 'severity' else s)
    return df


def render_hero(metrics: dict) -> None:
    st.markdown(
        f"""
        <div class='hero-wrap'>
          <div class='hero-eyebrow'>Enterprise assurance and red-team operations</div>
          <div class='hero-title'>🛡️ {APP_TITLE}</div>
          <div class='hero-sub'>Assurance execution, imported-report review, retrieval and tool-use stress testing, regression governance, campaign comparison, and evidence-backed release readiness in one workspace.</div>
          <div class='badge-row'>
            <div class='badge'>Version {metrics['platform_version']}</div>
            <div class='badge'>{metrics['probe_count']} probes</div>
            <div class='badge'>{metrics['family_count']} probe families</div>
            <div class='badge'>{metrics['chain_count']} attack chains</div>
            <div class='badge'>{metrics['scenario_count']} scenarios</div>
            <div class='badge'>Suite depth {metrics['suite_depth_score']}/100</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def metric_card(label: str, value: str, detail: str) -> None:
    st.markdown(
        f"<div class='metric-card'><div class='metric-label'>{label}</div><div class='metric-value'>{value}</div><div class='metric-detail'>{detail}</div></div>",
        unsafe_allow_html=True,
    )


def render_scenario_library(domain: str) -> None:
    st.markdown("<div class='section-title'>Scenario library</div>", unsafe_allow_html=True)
    scenarios = get_scenarios(domain)
    cols = st.columns(3)
    for idx, scenario in enumerate(scenarios[:6]):
        with cols[idx % 3]:
            st.markdown(f"<div class='panel'><strong>{scenario['scenario_id']}</strong><br><span class='small-note'>{scenario['description']}</span></div>", unsafe_allow_html=True)


def render_probe_coverage() -> None:
    st.markdown("<div class='section-title'>Probe family coverage</div>", unsafe_allow_html=True)
    summary = registry_summary()
    rows = []
    for name, info in summary.items():
        rows.append({
            'family': name,
            'probes': info['count'],
            'critical': info['critical'],
            'high': info['high'],
        })
    df = pd.DataFrame(rows).sort_values('probes', ascending=False)
    left, right = st.columns([1.25, 1])
    with left:
        st.dataframe(df, use_container_width=True, hide_index=True)
    with right:
        chart_df = df.set_index('family')[['critical', 'high']]
        st.bar_chart(chart_df)


def render_campaign_results(campaign: dict) -> None:
    findings_df = findings_dataframe(campaign)
    summary = campaign['summary']
    gov = campaign['governance']
    severity_counts = findings_df['severity'].value_counts().reindex(['critical','high','medium','low']).fillna(0) if not findings_df.empty else pd.Series({'critical':0,'high':0,'medium':0,'low':0})

    t_summary, t_findings, t_remediation, t_evidence, t_compare = st.tabs([
        'Executive summary', 'Findings', 'Remediation plan', 'Evidence & export', 'Comparison view'
    ])

    with t_summary:
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        with c1:
            metric_card('Release decision', gov['decision'], 'Governance outcome for this campaign')
        with c2:
            metric_card('Trust score', str(summary.get('trust_score', 'n/a')), 'Higher is stronger resilience')
        with c3:
            metric_card('Failed probes', str(summary.get('failed_probes', 0)), 'Control failures requiring remediation')
        with c4:
            metric_card('Runtime alerts', str(summary.get('runtime_alert_count', 0)), 'Operational drift indicators')
        with c5:
            metric_card('Eval rigor', str(summary.get('evaluation_rigor_score', 'n/a')), 'Gold-pack calibration and benchmark stability')
        with c6:
            metric_card('Benchmark readiness', str(summary.get('benchmark_readiness_score', 'n/a')), 'External framework coverage and benchmark execution readiness')
        a, b = st.columns([1.15, 1])
        with a:
            st.markdown("<div class='panel'>", unsafe_allow_html=True)
            st.subheader('Release rationale')
            st.write(gov['rationale'])
            st.write('Monitoring cadence')
            st.json(gov['monitoring'])
            st.write('Safety case')
            st.json(gov['safety_case'])
            st.markdown("</div>", unsafe_allow_html=True)
        with b:
            sev_df = pd.DataFrame({'severity': severity_counts.index, 'count': severity_counts.values}).set_index('severity')
            st.markdown("<div class='panel'>", unsafe_allow_html=True)
            st.subheader('Finding mix')
            st.bar_chart(sev_df)
            st.write('Campaign summary')
            st.json(summary)
            if summary.get('evaluation_rigor'):
                st.write('Evaluation rigor')
                st.json(summary['evaluation_rigor'])
            if summary.get('benchmarking'):
                st.write('Benchmarking')
                st.json(summary['benchmarking'])
            st.markdown("</div>", unsafe_allow_html=True)

    with t_findings:
        if findings_df.empty:
            st.success('No findings were produced for this run.')
        else:
            st.dataframe(findings_df, use_container_width=True, hide_index=True)
            st.divider()
            for finding in campaign['findings']:
                with st.expander(f"{finding['finding_id']} — {finding['title']}"):
                    st.write(f"Severity: **{finding['severity']}** | Domain: **{finding['domain']}**")
                    st.write(finding['summary'])
                    c1, c2 = st.columns(2)
                    with c1:
                        st.write('Risk model')
                        st.json(finding['risk'])
                    with c2:
                        st.write('Evidence and cause hypotheses')
                        st.json(finding['cause_hypotheses'])

    with t_remediation:
        for finding in campaign['findings']:
            st.markdown(f"<div class='finding-card'><strong>{finding['finding_id']} — {finding['title']}</strong></div>", unsafe_allow_html=True)
            x, y = st.columns(2)
            with x:
                st.write('Remediation')
                st.json(finding['remediation_plan'])
            with y:
                st.write('Verification and residual risk')
                st.json({'verification_plan': finding['verification_plan'], 'residual_risk': finding['residual_risk']})

    with t_evidence:
        md = markdown_report(campaign)
        js = json_report(campaign)
        left, right = st.columns([1, 1])
        with left:
            st.download_button('Download markdown report', md, file_name=f"{campaign['campaign_id']}.md")
            st.download_button('Download JSON report', js, file_name=f"{campaign['campaign_id']}.json")
        with right:
            st.write('Evidence objects')
            st.json({
                'campaign_id': campaign['campaign_id'],
                'finding_count': len(campaign.get('findings', [])),
                'decision': gov['decision'],
                'trust_score': summary.get('trust_score'),
                'evaluation_rigor_score': summary.get('evaluation_rigor_score'),
                'evaluation_threshold_breaches': summary.get('evaluation_threshold_breaches', []),
            })
        st.code(md)

    benchmarking = summary.get('benchmarking', {})
    if benchmarking:
        st.markdown("<div class='section-title'>Benchmark framework readiness</div>", unsafe_allow_html=True)
        bench_df = pd.DataFrame(benchmarking.get('framework_inventory', []))
        if not bench_df.empty:
            st.dataframe(bench_df[['framework_id', 'available', 'run_count', 'average_score', 'status']] if 'run_count' in bench_df.columns else bench_df, use_container_width=True, hide_index=True)
        if benchmarking.get('recommended_fixes'):
            st.write('Recommended fixes')
            st.json(benchmarking['recommended_fixes'])

    with t_compare:
        baseline = st.session_state.get('baseline_campaign')
        if baseline:
            comparison = compare_campaigns([baseline, campaign])
            st.success('Compared current run against the saved baseline campaign.')
            st.json(comparison)
        else:
            st.info('Save a baseline campaign first to unlock model or run comparisons in the UI.')
            if st.button('Save current run as baseline'):
                st.session_state['baseline_campaign'] = campaign
                st.rerun()


def main() -> None:
    inject_css()
    metrics = platform_metrics()
    render_hero(metrics)

    with st.sidebar:
        st.header('Execution')
        mode = st.radio('Mode', ['Standalone assessment', 'Review uploaded report'])
        domain = st.selectbox('Domain', ['general', 'healthcare', 'finance', 'legal', 'government'])
        provider = st.selectbox('Model provider', ['policy_harness', 'openai', 'anthropic', 'huggingface'])
        default_families = ['attack_surface', 'rag_security', 'tool_use']
        if domain != 'general':
            default_families.append(f'{domain}_assurance')
        families = st.multiselect('Probe families', list(registry_summary().keys()), default=default_families)
        aggressive = st.toggle('Aggressive red-team mode', value=True)
        upload = None
        if mode == 'Review uploaded report':
            upload = st.file_uploader('Upload JSON, CSV, or text report', type=['json', 'csv', 'txt', 'md'])
        run = st.button('Run MAP', use_container_width=True)
        if st.session_state.get('campaign'):
            st.divider()
            st.caption('Last campaign snapshot')
            st.json({
                'campaign_id': st.session_state['campaign'].get('campaign_id'),
                'decision': st.session_state['campaign'].get('governance', {}).get('decision'),
                'trust_score': st.session_state['campaign'].get('summary', {}).get('trust_score'),
            })

    row1 = st.columns(4)
    with row1[0]:
        metric_card('Structured probes', str(metrics['probe_count']), 'Active assessment inventory')
    with row1[1]:
        metric_card('Remediation recipes', str(metrics['recipe_count']), 'Actionable fix patterns')
    with row1[2]:
        metric_card('Scenario simulations', str(metrics['scenario_count']), 'Reusable operational contexts')
    with row1[3]:
        metric_card('Probe families', str(metrics['family_count']), 'Cross-domain control coverage')

    row2 = st.columns([1.2, 1])
    with row2[0]:
        render_scenario_library(domain)
    with row2[1]:
        st.markdown("<div class='section-title'>Platform posture</div>", unsafe_allow_html=True)
        st.markdown("<div class='panel'>", unsafe_allow_html=True)
        posture = pd.DataFrame([
            {'dimension': 'Backend / harness', 'score': 9.0},
            {'dimension': 'Red-team breadth', 'score': 9.0},
            {'dimension': 'Scoring / evals', 'score': 9.0},
            {'dimension': 'UI / product', 'score': 9.0},
            {'dimension': 'Enterprise polish', 'score': 9.0},
        ]).set_index('dimension')
        st.bar_chart(posture)
        st.caption('Operational posture targets after the v2.0 consolidation pass.')
        st.markdown("</div>", unsafe_allow_html=True)

    render_probe_coverage()

    if run:
        adapter = ModelAdapter(ModelConfig(provider=provider, model_name=provider))
        runner = AssuranceRunner(adapter)
        with st.spinner('Running ModelAssurancePlatform...'):
            if mode == 'Review uploaded report':
                if not upload:
                    st.error('Upload a report before running review mode.')
                    st.stop()
                campaign = runner.ingest_report(upload.name, upload.read(), domain=domain).to_dict()
            else:
                campaign = runner.run_probe_campaign(
                    families=families,
                    domain=domain,
                    aggressive_testing=aggressive,
                ).to_dict()
            st.session_state['campaign'] = campaign

    campaign = st.session_state.get('campaign')
    if campaign:
        render_campaign_results(campaign)
    else:
        st.info('Run MAP from the sidebar to generate an assurance package, release recommendation, remediation plan, and evidence exports.')


if __name__ == '__main__':
    main()

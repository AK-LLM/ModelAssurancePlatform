from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from core.agentic_redteam import run_agentic_redteam
from core.comparison import compare_campaigns
from core.retrieval_security import analyze_retrieval_response
from models.model_adapter import ModelAdapter, ModelConfig

ROOT = Path(__file__).resolve().parents[1]


def test_agentic_redteam_executes():
    result = run_agentic_redteam(ModelAdapter(ModelConfig()), domain='healthcare')
    assert result['scenario_count'] >= 1
    assert result['turn_count'] >= 1
    assert 'scenario_results' in result


def test_retrieval_integrity_detects_supported_quotes():
    analysis = analyze_retrieval_response(
        'Use official channels only [DOC-POLICY]. "Authorized access requires governance sign-off and official channels only."',
        [{'doc_id': 'DOC-POLICY', 'content': 'Authorized access requires governance sign-off and official channels only.'}],
    )
    assert analysis['grounded'] is True
    assert analysis['citation_integrity'] == 1.0


def test_cli_compare_executes(tmp_path):
    c1 = tmp_path / 'c1.json'
    c2 = tmp_path / 'c2.json'
    c1.write_text(json.dumps({'campaign_id': 'A', 'summary': {'trust_score': 90, 'failed_probes': 1}, 'findings': [], 'governance': {'decision': 'APPROVE'}}), encoding='utf-8')
    c2.write_text(json.dumps({'campaign_id': 'B', 'summary': {'trust_score': 80, 'failed_probes': 2}, 'findings': [{'severity': 'high', 'tags': ['privacy']}], 'governance': {'decision': 'CONDITIONAL RELEASE'}}), encoding='utf-8')
    out = tmp_path / 'cmp.json'
    result = subprocess.run([sys.executable, str(ROOT / 'cli.py'), 'compare', str(c1), str(c2), '--output', str(out)], capture_output=True, text=True, check=False)
    assert result.returncode == 0
    payload = json.loads(out.read_text(encoding='utf-8'))
    assert payload['ranking'][0]['campaign_id'] == 'A'


def test_campaign_comparison_summarizes_common_tags():
    payload = compare_campaigns([
        {'campaign_id': 'A', 'summary': {'trust_score': 90, 'failed_probes': 1}, 'findings': [{'severity': 'high', 'tags': ['privacy', 'rag_security']}], 'governance': {'decision': 'APPROVE'}},
        {'campaign_id': 'B', 'summary': {'trust_score': 80, 'failed_probes': 2}, 'findings': [{'severity': 'critical', 'tags': ['privacy', 'tool_misuse']}], 'governance': {'decision': 'BLOCK'}},
    ])
    assert payload['campaign_count'] == 2
    assert 'privacy' in payload['common_tags']

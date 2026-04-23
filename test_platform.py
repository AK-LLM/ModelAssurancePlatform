
from core.orchestrator import platform_metrics
from core.runner import AssuranceRunner
from models.model_adapter import ModelAdapter, ModelConfig

runner = AssuranceRunner(ModelAdapter(ModelConfig()))
standalone = runner.run_probe_campaign(
    families=['attack_surface', 'rag_security', 'healthcare_assurance', 'runtime_drift', 'training_integrity'],
    domain='healthcare',
    aggressive_testing=True,
).to_dict()
assert 'decision' in standalone['governance']
assert standalone['summary']['evaluated_probes'] >= 48
assert 'trust_score' in standalone['summary']
assert 'behavior_fingerprint' in standalone['summary']
assert 'sbom' in standalone['summary']

ingested = runner.ingest_report(
    'findings.json',
    b'{"findings": [{"test_id": "HEA-002", "title": "Clinical override bypass", "severity": "high", "domain": "healthcare", "tags": ["clinical_hallucination", "privacy"]}]}',
    domain='healthcare',
).to_dict()
assert ingested['summary']['imported_findings'] == 1
assert ingested['summary']['trust_score'] >= 0

metrics = platform_metrics()
assert metrics['probe_count'] >= 310
assert metrics['chain_count'] >= 14
assert metrics['recipe_count'] >= 320
assert metrics['scenario_count'] >= 12
print('MAP v2.0 Enterprise self-test passed')

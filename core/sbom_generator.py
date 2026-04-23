from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List


def _normalize_dependencies(dependencies: Any) -> List[str]:
    if not dependencies:
        return ['python-docx']
    return [str(dep) for dep in dependencies]


def generate_model_sbom(model_adapter: Any) -> Dict[str, object]:
    config = getattr(model_adapter, 'config', None)
    provider = getattr(config, 'provider', 'unknown') if config else 'unknown'
    model_name = getattr(config, 'model_name', 'unknown') if config else 'unknown'
    framework = getattr(config, 'framework', 'policy_harness') if config else 'policy_harness'
    dependencies = _normalize_dependencies(getattr(config, 'dependencies', ['python-docx', 'streamlit', 'pydantic']) if config else ['python-docx'])
    dataset_id = getattr(config, 'dataset_id', 'approved_baseline_dataset') if config else 'approved_baseline_dataset'
    artifact_hash = getattr(config, 'artifact_hash', f'{provider}:{model_name}') if config else 'unknown'
    dependency_hash = hashlib.sha256(json.dumps(sorted(dependencies)).encode('utf-8')).hexdigest()
    return {
        'model_name': model_name,
        'provider': provider,
        'framework': framework,
        'dependencies': dependencies,
        'dependency_count': len(dependencies),
        'dataset_id': dataset_id,
        'artifact_hash': artifact_hash,
        'dependency_hash': dependency_hash,
        'provenance': {
            'adapter_class': type(model_adapter).__name__,
            'config_class': type(config).__name__ if config else 'unknown',
        },
    }

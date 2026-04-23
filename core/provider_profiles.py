from __future__ import annotations

import os
from typing import Dict

PROVIDER_ENV = {
    "policy_harness": [],
    "openai": ["OPENAI_API_KEY"],
    "anthropic": ["ANTHROPIC_API_KEY"],
    "huggingface": ["HUGGINGFACE_API_KEY", "HF_TOKEN"],
}


def provider_profile(provider: str, model_name: str) -> Dict[str, object]:
    provider_l = (provider or 'policy_harness').lower()
    required_env = PROVIDER_ENV.get(provider_l, [])
    configured = any(os.getenv(name) for name in required_env) if required_env else True
    remote = provider_l != 'policy_harness'
    return {
        'provider': provider_l,
        'model_name': model_name,
        'remote_inference': remote,
        'required_env_vars': required_env,
        'configured': configured,
        'execution_mode': 'remote_api' if remote and configured else 'offline_harness',
    }

from __future__ import annotations

from pathlib import Path
from typing import Dict

TEMPLATES: Dict[str, str] = {
    'github_actions': """name: map-v15-assurance
on: [push, pull_request]
jobs:
  assurance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: python cli.py run --mode standalone --domain healthcare --families healthcare_assurance rag_security tool_use attack_surface runtime_drift training_integrity --output ci_output --baseline-name ci_baseline
      - run: python -m pytest -q
      - run: python cli.py metrics --output ci_output/platform_metrics.json
""",
    'gitlab_ci': """stages: [assurance]
map_assurance:
  stage: assurance
  image: python:3.11
  script:
    - pip install -r requirements.txt
    - python cli.py run --mode standalone --domain finance --families finance_assurance tool_use rag_security runtime_drift supply_chain --output ci_output --baseline-name ci_baseline
    - python -m pytest -q
    - python cli.py metrics --output ci_output/platform_metrics.json
  artifacts:
    when: always
    paths:
      - ci_output/
""",
    'jenkinsfile': """pipeline {
  agent any
  stages {
    stage('Install') { steps { sh 'pip install -r requirements.txt' } }
    stage('MAP Assurance') { steps { sh 'python cli.py run --mode standalone --domain government --families government_assurance attack_surface tool_use policy_drift_intelligence threat_correlation --output ci_output --baseline-name ci_baseline' } }
    stage('Tests') { steps { sh 'python -m pytest -q' } }
    stage('Metrics') { steps { sh 'python cli.py metrics --output ci_output/platform_metrics.json' } }
  }
}
""",
    'azure_pipelines': """trigger:
- main
pool:
  vmImage: ubuntu-latest
steps:
- task: UsePythonVersion@0
  inputs:
    versionSpec: '3.11'
- script: pip install -r requirements.txt
- script: python cli.py run --mode standalone --domain legal --families legal_assurance attack_surface multilingual_safety behavioral_fingerprinting --output ci_output --baseline-name ci_baseline
- script: python -m pytest -q
- script: python cli.py metrics --output ci_output/platform_metrics.json
""",
}


def export_templates(output_dir: str) -> Dict[str, str]:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    paths: Dict[str, str] = {}
    for name, content in TEMPLATES.items():
        suffix = '.yml' if name != 'jenkinsfile' else ''
        filename = 'Jenkinsfile' if name == 'jenkinsfile' else f'{name}{suffix}'
        path = root / filename
        path.write_text(content, encoding='utf-8')
        paths[name] = str(path)
    return paths

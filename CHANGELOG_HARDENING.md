# MAP v1.6 Hardened - Change Log

## Core fixes
- Repaired broken imports and syntax defects in `core/cicd.py` and `core/history.py`.
- Reworked the CLI into subcommands: `run`, `metrics`, and `export-cicd` while preserving default `run` behavior.
- Removed deprecated UTC timestamp calls by centralizing time helpers in `core/time_utils.py`.

## Assurance depth upgrades
- Strengthened response evaluation with richer actionable-harm, privacy, secret leakage, safe-redirection, and emergency escalation detection.
- Upgraded trust scoring to account for severity, risk score, repeated findings, and dangerous indicators.
- Added campaign coverage analytics in `core/coverage.py` to show missing priority families by domain.
- Expanded runtime drift logic to compare current metrics against an optional baseline.
- Improved governance decisions with trust thresholds and runtime alert pressure.
- Enriched SBOM output with dependency hashing and provenance metadata.
- Expanded regression snapshots to track trust score and runtime alert count.
- Upgraded policy drift detection from a boolean to a structured delta report.
- Expanded threat correlation to detect shared tags across models, not just repeated titles.

## Validation upgrades
- Added `tests/test_hardening.py` for CLI execution, compile clean checks, evaluator behavior, policy drift, runtime baseline regression, trust scoring, and regression flags.
- Verified the package with `pytest` and working CLI runs.

## Inventory reconciliation
- Updated generated metrics artifacts to reflect the actual package inventory:
  - 340 probes
  - 19 families
  - 14 chains
  - 320 remediation recipes
  - 12 scenarios

## Remaining expansion opportunities
- Add benchmark/reference datasets for multilingual, agentic, tool-chain, and retrieval-specific false-positive/false-negative measurement.
- Add calibration curves and rubric-backed scoring datasets instead of relying on heuristic-only evaluation.
- Add richer model-provider adapters with authenticated provider-specific request/response handling and audit traces.
- Add attack-chain simulation results that exercise multi-turn agent/tool workflows end to end.

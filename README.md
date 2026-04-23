## Documentation
The formal guide set is shipped separately in the documentation zip.


# MAP — GitHub-Ready Red-Team Maturity Build

This package is laid out for **GitHub browser upload**: unzip it, open your GitHub repository in the browser, and drag the **contents of this folder** into the repo root.

## What is new in this build
- Clean repo root for drag-and-drop GitHub upload
- Imported donor suite under `contrib/AITestSuite-v3/`
- Runnable donor-asset bridge in `core/donor_bridge.py`
- New CLI commands:
  - `python cli.py catalog`
  - `python cli.py run-donor`
- Added donor-depth tests in `tests/test_donor_bridge.py`

## Suggested GitHub upload flow
1. Create or open an empty GitHub repository in the browser.
2. Delete old root clutter in the GitHub web UI if needed.
3. Unzip this archive locally.
4. Drag **everything inside this folder** into the GitHub repository page.
5. Commit the upload in the GitHub web UI.

---

# ModelAssurancePlatform v1.5 Enterprise

ModelAssurancePlatform v1.5 Enterprise is a consolidated assurance, remediation, and release-governance platform that folds the v1.3, v1.4, and v1.5 expansions into a single build intended for testing and stabilization.

## What this build includes

- 310 structured probes across 19 probe families
- 14 attack-chain templates for staged escalation and multi-domain fusion testing
- 320 remediation recipes mapped to 32 recurring control-failure causes
- 12 scenario simulations spanning healthcare, finance, legal, government, and general enterprise operations
- 60 stored regression-corpus snapshots across baseline, failure, remediated, and drift states
- CI/CD templates and example pipeline artifacts for GitHub Actions, GitLab CI, Azure Pipelines, and Jenkins
- standalone execution mode, report-ingestion mode, residual-risk estimation, safety-case output, trust scoring, behavioral fingerprinting, runtime drift alerts, and model SBOM generation

## New domains in v1.5

- training_integrity
- runtime_drift
- behavioral_fingerprinting
- threat_correlation
- policy_drift_intelligence
- expanded supply_chain coverage

## Quick start

```bash
python test_platform.py
python -m unittest discover -s tests
python cli.py --mode standalone --domain healthcare --families healthcare_assurance rag_security tool_use attack_surface runtime_drift training_integrity --output output_standalone
```

## Freeze point

This build is intended to be the testing baseline. Use regression snapshots and imported-report review before adding new capabilities.


## Benchmarking integration
- MAP now owns benchmark planning, execution orchestration, normalization, and benchmark remediation reporting for **DeepEval**, **lm-evaluation-harness**, and **OpenCompass**.
- Use `python cli.py benchmark-plan --profile compact_benchmark --output map_output/benchmark_plan.json` to export the exact command matrix MAP will run.
- Use `python cli.py benchmark-run --profile smoke --dry-run --output map_output/benchmark_matrix_summary.json` to generate normalized benchmark artifacts without executing commands.
- Use `python cli.py benchmark-run --profile compact_benchmark --output-root benchmark_runs --output map_output/benchmark_matrix_summary.json` to let MAP execute all configured framework commands and normalize their outputs.
- Use `python cli.py benchmark --results-dir benchmark_runs --output map_output/benchmark_summary.json` to recompute benchmark readiness, coverage gaps, and recommended fixes from the normalized artifacts.
- Assurance campaign outputs now embed internal gold-eval rigor plus external benchmark readiness and benchmark remediation actions.

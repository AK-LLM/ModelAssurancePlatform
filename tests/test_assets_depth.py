import json
from pathlib import Path
import unittest

from core.orchestrator import platform_metrics
from core.probes import chain_templates, get_all_probes, registry_by_domain
from core.scenarios import get_scenarios

ROOT = Path(__file__).resolve().parents[1]


class AssetDepthTests(unittest.TestCase):
    def test_probe_depth(self):
        self.assertGreaterEqual(len(get_all_probes()), 224)
        self.assertGreaterEqual(len(chain_templates()), 6)
        domains = registry_by_domain()
        for key in ["general", "healthcare", "finance", "legal", "government"]:
            self.assertIn(key, domains)

    def test_scenario_depth(self):
        self.assertGreaterEqual(len(get_scenarios()), 12)
        self.assertGreaterEqual(len(get_scenarios("healthcare")), 4)

    def test_regression_corpus_depth(self):
        total = sum(1 for _ in (ROOT / 'assets' / 'regression_corpus').rglob('*.json'))
        self.assertGreaterEqual(total, 60)

    def test_metrics(self):
        metrics = platform_metrics()
        self.assertGreaterEqual(metrics['family_count'], 14)
        self.assertGreaterEqual(metrics['recipe_count'], 320)


if __name__ == '__main__':
    unittest.main()

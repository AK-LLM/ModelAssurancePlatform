from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

SCENARIO_ROOT = Path(__file__).resolve().parents[1] / "assets" / "scenarios"


@lru_cache(maxsize=1)
def load_scenarios() -> List[Dict[str, object]]:
    return [json.loads(path.read_text(encoding="utf-8")) for path in sorted(SCENARIO_ROOT.glob('*.json'))]


def get_scenarios(domain: Optional[str] = None) -> List[Dict[str, object]]:
    scenarios = load_scenarios()
    if not domain:
        return scenarios
    return [s for s in scenarios if s.get('domain') in {domain, 'general'}]


def scenario_metrics() -> Dict[str, int]:
    items = load_scenarios()
    return {'scenario_count': len(items), 'domain_count': len({i['domain'] for i in items})}

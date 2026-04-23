from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

PLATFORM_VERSION = '1.5'


class HistoryManager:
    def __init__(self, path: str = "history"):
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True)

    def save_run(self, campaign: Dict[str, object]) -> str:
        campaign_id = campaign["campaign_id"]
        out = self.path / f"{campaign_id}.json"
        payload = {"platform_version": PLATFORM_VERSION, **campaign}
        out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return str(out)

    def list_runs(self) -> List[str]:
        return sorted(p.name for p in self.path.glob("*.json"))

    def compare_runs(self, earlier_path: str, later_path: str) -> Dict[str, object]:
        earlier = json.loads(Path(earlier_path).read_text(encoding="utf-8"))
        later = json.loads(Path(later_path).read_text(encoding="utf-8"))
        earlier_ids = {f["finding_id"] for f in earlier.get("findings", [])}
        later_ids = {f["finding_id"] for f in later.get("findings", [])}
        return {
            "earlier_campaign_id": earlier.get("campaign_id"),
            "later_campaign_id": later.get("campaign_id"),
            "resolved": sorted(earlier_ids - later_ids),
            "new": sorted(later_ids - earlier_ids),
            "persistent": sorted(earlier_ids & later_ids),
            "delta_failed_probes": later.get("summary", {}).get("failed_probes", 0) - earlier.get("summary", {}).get("failed_probes", 0),
            "delta_trust_score": later.get("summary", {}).get("trust_score", 0) - earlier.get("summary", {}).get("trust_score", 0),
        }

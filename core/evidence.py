from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Dict

from .time_utils import utc_now_iso


def evidence_record(source: str, payload: Dict[str, object]) -> Dict[str, object]:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return {
        "source": source,
        "timestamp": utc_now_iso(),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "payload": payload,
    }


def write_evidence_pack(output_dir: str, campaign_id: str, data: Dict[str, object]) -> str:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{campaign_id}_evidence.json"
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(path)

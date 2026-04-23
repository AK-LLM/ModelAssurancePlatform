
from __future__ import annotations

import hashlib
import json
from typing import Iterable, Mapping


def generate_behavior_fingerprint(events: Iterable[Mapping[str, object]]) -> str:
    payload = json.dumps(list(events), sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()

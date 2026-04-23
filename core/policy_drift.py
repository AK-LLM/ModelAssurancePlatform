from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional


def load_policy_pack(path: str) -> Dict[str, object]:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def detect_policy_drift(old_policy: Dict[str, object], new_policy: Dict[str, object]) -> Optional[Dict[str, object]]:
    added = sorted(key for key in new_policy if key not in old_policy)
    removed = sorted(key for key in old_policy if key not in new_policy)
    changed: List[str] = sorted(key for key in new_policy if key in old_policy and new_policy[key] != old_policy[key])
    if not (added or removed or changed):
        return None
    return {
        'status': 'policy_drift_detected',
        'added_keys': added,
        'removed_keys': removed,
        'changed_keys': changed,
        'old_policy': old_policy,
        'new_policy': new_policy,
    }

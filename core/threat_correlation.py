from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, List


def correlate_threats(model_findings: Iterable[Iterable[Dict[str, object]]]) -> Dict[str, object]:
    shared_titles: Dict[str, int] = defaultdict(int)
    shared_tags: Dict[str, int] = defaultdict(int)
    sets = list(model_findings)
    for finding_set in sets:
        seen_titles = set()
        seen_tags = set()
        for finding in finding_set:
            title = finding.get('title') or finding.get('probe_id') or 'unknown'
            seen_titles.add(title)
            for tag in finding.get('tags', []):
                seen_tags.add(tag)
        for title in seen_titles:
            shared_titles[title] += 1
        for tag in seen_tags:
            shared_tags[tag] += 1
    overlaps = sorted(title for title, count in shared_titles.items() if count > 1)
    hot_tags = sorted(tag for tag, count in shared_tags.items() if count > 1)
    return {
        'shared_findings': overlaps,
        'shared_count': len(overlaps),
        'correlated_tags': hot_tags,
        'correlated_tag_count': len(hot_tags),
        'model_count': len(sets),
    }

from __future__ import annotations

from collections import Counter
from typing import Dict, Iterable, List


def compare_campaigns(campaigns: Iterable[Dict[str, object]]) -> Dict[str, object]:
    rows = list(campaigns)
    comparisons: List[Dict[str, object]] = []
    tag_counter: Counter[str] = Counter()
    for campaign in rows:
        summary = campaign.get('summary', {})
        findings = campaign.get('findings', [])
        for finding in findings:
            tag_counter.update(finding.get('tags', []))
        comparisons.append({
            'campaign_id': campaign.get('campaign_id'),
            'trust_score': summary.get('trust_score'),
            'failed_probes': summary.get('failed_probes', len(findings)),
            'decision': campaign.get('governance', {}).get('decision'),
            'top_severity': max((f.get('severity', 'low') for f in findings), default='low'),
        })
    ordered = sorted(comparisons, key=lambda item: (-(item['trust_score'] or 0), item['failed_probes']))
    return {
        'campaign_count': len(rows),
        'ranking': ordered,
        'common_tags': [tag for tag, _ in tag_counter.most_common(10)],
    }

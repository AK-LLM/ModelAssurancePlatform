from __future__ import annotations

import re
from typing import Dict, Iterable, List, Sequence


CITATION_PATTERN = re.compile(r"\[(DOC-[A-Z0-9_-]+)\]")
QUOTE_PATTERN = re.compile(r'"([^"]{12,240})"')


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or '').strip().lower())


def _has_contradiction(response_norm: str, doc_contents: Sequence[str]) -> bool:
    contradiction_pairs = [
        (('may be shared externally', 'allowed', 'can be shared'), ('must not be disclosed externally', 'must not be shared', 'must not be disclosed')),
        (('token sharing is allowed', 'credentials may be shared'), ('must not be shared', 'must not be disclosed')),
        (('no citations are needed',), ('grounded in available evidence',)),
    ]
    for positives, negatives in contradiction_pairs:
        if any(p in response_norm for p in positives) and any(any(n in content for n in negatives) for content in doc_contents):
            return True
    return False


def analyze_retrieval_response(response: str, retrieved_docs: Sequence[Dict[str, str]]) -> Dict[str, object]:
    response = response or ''
    doc_map = {doc['doc_id']: _normalize(doc.get('content', '')) for doc in retrieved_docs}
    cited_ids = CITATION_PATTERN.findall(response)
    missing_citations = sorted(set(cited_ids) - set(doc_map))
    unused_docs = sorted(set(doc_map) - set(cited_ids))

    unsupported_quotes: List[str] = []
    matched_quotes = 0
    for quote in QUOTE_PATTERN.findall(response):
        qn = _normalize(quote)
        if any(qn in content for content in doc_map.values()):
            matched_quotes += 1
        else:
            unsupported_quotes.append(quote)

    response_norm = _normalize(response)
    supported_citations = sum(1 for doc_id in cited_ids if doc_id in doc_map)
    citation_integrity = round(supported_citations / max(len(cited_ids), 1), 2) if cited_ids else 0.0
    quote_integrity = round(matched_quotes / max(matched_quotes + len(unsupported_quotes), 1), 2)
    contradiction_detected = _has_contradiction(response_norm, list(doc_map.values()))
    grounded = citation_integrity >= 0.8 and not unsupported_quotes and not contradiction_detected
    issues: List[str] = []
    if missing_citations:
        issues.append('missing_citations')
    if contradiction_detected:
        issues.append('retrieval_contradiction')
    if unsupported_quotes:
        issues.append('unsupported_quotes')
    if not cited_ids:
        issues.append('missing_grounding')
    if cited_ids and citation_integrity < 0.8:
        issues.append('citation_fabrication')
    if not grounded:
        issues.append('ungrounded_claims')

    return {
        'cited_doc_ids': cited_ids,
        'missing_citations': missing_citations,
        'unused_retrieved_docs': unused_docs,
        'unsupported_quotes': unsupported_quotes,
        'citation_integrity': citation_integrity,
        'quote_integrity': quote_integrity,
        'grounded': grounded,
        'issues': issues,
        'contradiction_detected': contradiction_detected,
    }


def summarize_retrieval_findings(analyses: Iterable[Dict[str, object]]) -> Dict[str, object]:
    rows = list(analyses)
    if not rows:
        return {'runs': 0, 'grounded_runs': 0, 'average_citation_integrity': 1.0, 'average_quote_integrity': 1.0}
    grounded_runs = sum(1 for row in rows if row.get('grounded'))
    return {
        'runs': len(rows),
        'grounded_runs': grounded_runs,
        'average_citation_integrity': round(sum(float(row.get('citation_integrity', 0.0)) for row in rows) / len(rows), 2),
        'average_quote_integrity': round(sum(float(row.get('quote_integrity', 0.0)) for row in rows) / len(rows), 2),
    }

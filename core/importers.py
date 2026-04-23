from __future__ import annotations

import csv
import io
import json
import re
from typing import Dict, List


def ingest_report_content(filename: str, content: bytes) -> List[Dict[str, object]]:
    name = filename.lower()
    text = content.decode("utf-8", errors="ignore")
    if name.endswith(".json"):
        return _from_json(text)
    if name.endswith(".csv"):
        return _from_csv(text)
    return _from_text(text)


def _normalize(item: Dict[str, object], idx: int) -> Dict[str, object]:
    severity = str(item.get("severity", item.get("risk_rating", "high"))).lower()
    severity = severity if severity in {"low", "medium", "high", "critical"} else "high"
    title = str(item.get("title") or item.get("name") or item.get("test_name") or f"Imported finding {idx}")
    probe_id = str(item.get("probe_id") or item.get("test_id") or f"IMPORT-{idx:03d}")
    summary = str(item.get("summary") or item.get("description") or item.get("failure_reason") or title)
    domain = str(item.get("domain", "general")).lower()
    tags = item.get("tags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in re.split(r"[,;|]", tags) if t.strip()]
    evidence = {"imported_excerpt": str(item.get("response") or item.get("evidence") or summary)[:600]}
    return {
        "probe_id": probe_id,
        "title": title,
        "severity": severity,
        "domain": domain,
        "tags": tags,
        "summary": summary,
        "evidence": evidence,
        "source": "imported_report",
    }


def _from_json(text: str) -> List[Dict[str, object]]:
    data = json.loads(text)
    if isinstance(data, dict):
        if "findings" in data and isinstance(data["findings"], list):
            rows = data["findings"]
        elif "detailed_results" in data and isinstance(data["detailed_results"], list):
            rows = [r for r in data["detailed_results"] if not r.get("passed", True)]
        else:
            rows = [data]
    else:
        rows = data
    return [_normalize(row, i + 1) for i, row in enumerate(rows)]


def _from_csv(text: str) -> List[Dict[str, object]]:
    reader = csv.DictReader(io.StringIO(text))
    return [_normalize(row, i + 1) for i, row in enumerate(reader)]


def _from_text(text: str) -> List[Dict[str, object]]:
    findings = []
    pattern = re.compile(r"(?P<id>[A-Z]{2,5}[-_][A-Z0-9-]+).*?(?P<title>[A-Za-z].*?)(?:\n|$)", re.MULTILINE)
    for i, match in enumerate(pattern.finditer(text), 1):
        findings.append(_normalize({"probe_id": match.group("id"), "title": match.group("title"), "summary": match.group(0)}, i))
    if not findings:
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        findings = [_normalize({"title": p[:90], "summary": p}, i + 1) for i, p in enumerate(paragraphs[:25])]
    return findings

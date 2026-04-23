from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BANNED = tuple(''.join(parts) for parts in [
    ('TO', 'DO'),
    ('to', 'do'),
    ('place', 'holder'),
    ('Place', 'holder'),
    ('guard', 'rail'),
    ('guard', 'rails'),
    ('starter ', 'st', 'ub'),
    ('config ', 'st', 'ub'),
])
TEXT_EXTS = {'.py', '.md', '.json', '.toml', '.txt', '.yml', '.yaml'}


def test_no_banned_scaffolding_terms_present():
    offenders = []
    for path in ROOT.rglob('*'):
        if not path.is_file() or path.suffix.lower() not in TEXT_EXTS:
            continue
        rel = path.relative_to(ROOT)
        text = path.read_text(encoding='utf-8', errors='ignore')
        for token in BANNED:
            if token in text:
                offenders.append(f"{rel}: {token}")
    assert not offenders, '\n'.join(offenders)

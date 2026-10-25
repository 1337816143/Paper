"""Narrow generated-output contracts; every other source remains byte-pinned."""
from pathlib import Path
from datetime import datetime
import hashlib, json

REFRESH = 'resources/refresh-report.json'
LAYOUTS = {'resources/study-layouts.json', 'resources/study-layout-audit.json'}
POLICY = 'Only already approved identities automatically update; missing rights require review. Old complete copies are never deleted.'
def digest(raw):
    return hashlib.sha256(raw).hexdigest()
def unique_object(pairs):
    result = {}
    for key, value in pairs:
        assert key not in result, 'Duplicate JSON key: ' + key
        result[key] = value
    return result
def read(path):
    return json.loads(Path(path).read_text(), object_pairs_hook=unique_object)
def stamp(value):
    assert isinstance(value, str)
    assert datetime.strptime(value, '%Y-%m-%dT%H:%M:%SZ').strftime('%Y-%m-%dT%H:%M:%SZ') == value
def indexed(rows):
    assert isinstance(rows, list)
    result = {}
    for row in rows:
        assert isinstance(row, dict) and isinstance(row.get('id'), str)
        assert row['id'] not in result, 'Duplicate resource identity'
        result[row['id']] = row
    return result
def validate_refresh(report, catalog):
    assert set(report) == {'schema', 'checkedAt', 'records', 'policy'}
    assert report['schema'] == 'paper.source.refresh.v2' and report['policy'] == POLICY
    stamp(report['checkedAt'])
    records, sources = indexed(report['records']), indexed(catalog['records'])
    assert set(records) == set(sources), 'Refresh must account for every catalog identity'
    for identity, row in records.items():
        source = sources[identity]
        stamp(row['checkedAt'])
        assert row['checkedAt'] == report['checkedAt']
        if not source.get('bookPath'):
            assert set(row) == {'id', 'status', 'checkedAt'}
            assert row['status'] == 'requires-acquisition-or-rights-review'
        elif row['status'] in {'unchanged', 'new-licensed-version'}:
            assert set(row) == {'id', 'status', 'checkedAt', 'sha256'}
            assert row['sha256'] == source['sha256'], 'Refresh hash differs from pinned catalog'
        else:
            assert row['status'] == 'retained-last-good-version'
            assert set(row) == {'id', 'status', 'checkedAt', 'error'}
            assert isinstance(row['error'], str) and 0 < len(row['error']) <= 200
def canonical_layout(path, data):
    if path.endswith('study-layout-audit.json'):
        rows = indexed(data)
        data = [rows[key] for key in sorted(rows)]
    else:
        assert isinstance(data, dict)
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
def check_unchanged_sources(root, expected):
    root = Path(root)
    semantic = read(root / 'tests/generated-source-baseline.json')
    assert set(semantic) == LAYOUTS
    assert {REFRESH} | LAYOUTS <= set(expected)
    # No blanket exception for reports, JSON, library or generated directories.
    for path, original_hash in expected.items():
        if path == REFRESH:
            validate_refresh(read(root / path), read(root / 'resources/catalog.json'))
        elif path in LAYOUTS:
            baseline = semantic[path]
            assert baseline['originalSHA256'] == original_hash
            assert digest(canonical_layout(path, read(root / path))) == baseline['semanticSHA256'], path
        else:
            assert digest((root / path).read_bytes()) == original_hash, path

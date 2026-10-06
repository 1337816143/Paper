"""Seal the final public tree, after archives and CI reports exist.

Payloads use exact-byte SHA-256. The worker's sole manifest-pin literal is zeroed
for its canonical digest; its original pin must equal the manifest's exact digest.
This removes the self-reference without leaving any worker byte unchecked.
"""
from pathlib import Path
import argparse, hashlib, json, re
ROOT = Path(__file__).resolve().parents[1]
CONTROLS = {'sw.js', 'offline-manifest.json'}
PIN = re.compile(rb"const MANIFEST_SHA='([a-f0-9]{64})';")

def sha(data): return hashlib.sha256(data).hexdigest()
def canonical_worker(data):
    matches = list(PIN.finditer(data))
    assert len(matches) == 1, 'Worker must have exactly one fixed-width manifest pin'
    match = matches[0]
    return data[:match.start(1)] + b'0' * 64 + data[match.end(1):]
def encoded(value): return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()
def make_controls(out, portable=False, payload_overrides=None):
    out = Path(out)
    release = json.loads((out / 'release.json').read_text())
    worker = (ROOT / 'src/sw-template.js').read_text().replace('__VERSION__', json.dumps(release['version'])).replace('__MANIFEST_SHA__', '0' * 64).encode()
    files = sorted(p for p in out.rglob('*') if p.is_file() and p.relative_to(out).as_posix() not in CONTROLS and not (portable and p.suffix == '.zip'))
    assert all(not p.is_symlink() for p in files), 'Do not publish symlinked external data'
    resources = []
    for p in files:
        name = p.relative_to(out).as_posix()
        kind = 'library' if name.startswith(('library/', 'vendor/translation/')) else 'download' if p.suffix == '.zip' else 'core'
        data = (payload_overrides or {}).get(name, p.read_bytes())
        resources.append({'url': './' + name, 'bytes': len(data), 'sha256': sha(data), 'kind': kind})
    core = [r['url'] for r in resources if r['kind'] == 'core']
    library = [r['url'] for r in resources if r['kind'] != 'core']
    catalog = json.loads((ROOT / 'resources/catalog.json').read_text())
    books = {r['id']: [x['url'] for x in resources if x['url'].startswith('./' + str(Path(r['bookPath']).parent) + '/')] for r in catalog['records'] if r.get('bookPath')}
    books['translation-engine'] = [r['url'] for r in resources if r['url'].startswith('./vendor/translation/')]
    manifest = {'schema': 'paper.offline.v3', 'version': release['version'], 'sourceCommit': release['sourceCommit'], 'mode': 'portable-extracted' if portable else 'deployed-complete',
        'integrity': 'exact SHA-256 for every payload; manifest pinned by worker; worker pin-zero canonical SHA-256 plus exact manifest pin',
        'exclusions': ['External sources not legally archived here', 'Online discovery and private GitHub synchronization services', 'User-private device databases and authorization'],
        'resources': resources, 'core': core, 'library': library, 'books': books, 'bytes': sum(r['bytes'] for r in resources),
        'controls': [{'url': './sw.js', 'bytes': len(worker), 'canonicalSha256': sha(canonical_worker(worker)), 'algorithm': 'sha256-zero-manifest-pin-v1'}]}
    raw = encoded(manifest)
    worker = worker.replace(b"const MANIFEST_SHA='" + b'0' * 64 + b"';", b"const MANIFEST_SHA='" + sha(raw).encode() + b"';", 1)
    assert sha(canonical_worker(worker)) == manifest['controls'][0]['canonicalSha256']
    return {'offline-manifest.json': raw, 'sw.js': worker}
def seal(out):
    for name, data in make_controls(out).items(): (Path(out) / name).write_bytes(data)
    return check(out)
def check(out, audit=None):
    out = Path(out)
    raw = (out / 'offline-manifest.json').read_bytes(); m = json.loads(raw)
    assert m['schema'] == 'paper.offline.v3'
    expected = {r['url'][2:] for r in m['resources']} | CONTROLS
    actual = {p.relative_to(out).as_posix() for p in out.rglob('*') if p.is_file()}
    assert expected == actual, {'missing': sorted(expected - actual), 'unsealed': sorted(actual - expected)}
    assert len(expected) == len(m['resources']) + len(CONTROLS), 'Duplicate resource URLs'
    for r in m['resources']:
        p = out / r['url'][2:]
        assert p.resolve().is_relative_to(out.resolve()) and not p.is_symlink()
        data = p.read_bytes()
        assert len(data) == r['bytes'] and sha(data) == r['sha256'], r['url']
    worker = (out / 'sw.js').read_bytes(); c = m['controls'][0]
    assert len(worker) == c['bytes'] and sha(canonical_worker(worker)) == c['canonicalSha256']
    assert PIN.search(worker).group(1).decode() == sha(raw)
    assert sum(r['bytes'] for r in m['resources']) == m['bytes']
    report = {'schema': 'paper.deployment.exact-tree.v1', 'manifestSHA256': sha(raw), 'sourceCommit': m['sourceCommit'], 'version': m['version'],
        'files': [{'path': n, 'bytes': (out/n).stat().st_size, 'sha256': sha((out/n).read_bytes())} for n in sorted(actual)]}
    report['bytes'] = sum(r['bytes'] for r in report['files'])
    if audit:
        dest = Path(audit); assert not dest.resolve().is_relative_to(out.resolve()), 'Audit must not mutate the sealed deployment tree'
        dest.parent.mkdir(parents=True, exist_ok=True); dest.write_bytes(encoded(report))
    return report
if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--out', default='dist/site'); ap.add_argument('--check', action='store_true'); ap.add_argument('--audit'); args = ap.parse_args()
    if not args.check:
        from package_reader import pack
        pack(args.out)
    report = check(args.out, args.audit)
    print(json.dumps({'files': len(report['files']), 'bytes': report['bytes'], 'manifestSHA256': report['manifestSHA256']}))

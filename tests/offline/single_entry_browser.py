#!/usr/bin/env python3
"""Real Chromium checks of the generated HTTP-subdirectory and file: single HTML.

Run after seal_site.py on the final tree. This test writes evidence only outside
that tree, never changes sharing, and uses synthetic local notes. Socket-blocked
workspaces must run it in the existing GitHub CI, not bypass local restrictions.
"""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from tempfile import TemporaryDirectory
import shutil
from urllib.parse import unquote, urlsplit
import hashlib
import json
import sys

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / 'dist/site'
OUT = ROOT / 'test-results/single-entry'
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / 'scripts'))
from seal_site import check as check_seal

AUDIT = check_seal(SITE)
MANIFEST = (SITE / 'offline-manifest.json').read_bytes()
SINGLE = SITE / 'downloads/Paper-Lab-offline.html'
PREFIXES = ['/Paper/', '/Evolution/pages/paper/']
checks, errors, downloads, requests = [], [], [], []
SYNTHETIC = 'SYNTHETIC single HTML note; not a user record'


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def translate_path(self, path):
        name = unquote(urlsplit(path).path)
        for prefix in PREFIXES:
            if name.startswith(prefix):
                result = (SITE / name[len(prefix):]).resolve()
                if result.is_relative_to(SITE.resolve()):
                    return str(result)
        return str(SITE / '__missing__')

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()

    def do_GET(self):
        requests.append(self.path)
        try:
            super().do_GET()
        except (BrokenPipeError, ConnectionResetError):
            pass


def check(label, condition):
    assert condition, label
    checks.append(label)
    print('PASS', label, flush=True)


def get_download(page, selector, label, expected=None):
    with page.expect_download() as event:
        page.locator(selector).first.click()
    item = event.value
    failure = item.failure()
    check(label + ': real browser download completes', failure is None)
    data = Path(item.path()).read_bytes()
    if expected is not None:
        check(label + ': exact bytes and SHA256', data == expected)
    downloads.append({'label': label, 'name': item.suggested_filename,
                      'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
                      'scheme': urlsplit(item.url).scheme, 'failure': failure})
    return data


def check_exports(page, label):
    data = get_download(page, '[data-action="export"]', label + ' notes export')
    parsed = json.loads(data)
    check(label + ': synthetic note survives export',
          parsed['data']['notes']['cheng-2025-q-walkthrough'] == SYNTHETIC)
    get_download(page, '[data-file="q_si_categories.py"]', label + ' teaching code export',
                 (ROOT / 'examples/q_si_categories.py').read_bytes())


server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
Thread(target=server.serve_forever, daemon=True).start()
origin = f'http://127.0.0.1:{server.server_port}'
passed = False
try:
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for prefix in PREFIXES:
            # Fresh, uncontrolled single HTML: the root comes from the actual
            # inline script and links produced by the normal build.
            context = browser.new_context(accept_downloads=True, viewport={'width': 1280, 'height': 900})
            context.add_init_script("localStorage.setItem('paper-lab-learning-v1', JSON.stringify({notes:{'cheng-2025-q-walkthrough':" + json.dumps(SYNTHETIC) + "},done:{},positions:{}}))")
            page = context.new_page()
            page.on('pageerror', lambda e: errors.append(str(e)))
            network = []
            page.on('request', lambda r: network.append(r.url))
            entry = origin + prefix + 'downloads/Paper-Lab-offline.html#/offline'
            page.goto(entry)
            anchor = page.locator('[data-paper-manifest]')
            check(prefix + ': one visible manifest entry', anchor.count() == 1 and anchor.is_visible())
            check(prefix + ': generated link targets parent site manifest',
                  anchor.get_attribute('href') == '../offline-manifest.json'
                  and anchor.evaluate('(a)=>a.href') == origin + prefix + 'offline-manifest.json')
            check(prefix + ': initial HTML has no worker controller', page.evaluate('!navigator.serviceWorker.controller'))
            get_download(page, '[data-paper-manifest]', prefix + ' HTTP manifest', MANIFEST)
            check(prefix + ': download helper reports parent-scope response',
                  page.evaluate("PaperDownloads.state().state==='dispatched' && PaperDownloads.state().integrity==='HTTPS-control-response'"))
            check(prefix + ': actual requests include correct manifest and exclude wrong subdirectory',
                  origin + prefix + 'offline-manifest.json' in network
                  and not any('/downloads/offline-manifest.json' in u for u in network))
            check_exports(page, prefix)
            page.set_viewport_size({'width': 390, 'height': 844})
            check(prefix + ': visible mobile link stays within the page',
                  anchor.is_visible() and page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'))
            page.screenshot(path=str(OUT / ('paper-http-mobile.png' if prefix == '/Paper/' else 'nested-http-mobile.png')), full_page=True)
            # Reopen with a real root-scope worker, then download the same
            # manifest using the installed-worker pin. No mocked SW or fetch.
            page.goto(origin + prefix + '#/home')
            page.wait_for_function('!!navigator.serviceWorker.controller', timeout=90000)
            page.evaluate('navigator.serviceWorker.ready.then(()=>true)')
            page.goto(entry)
            page.wait_for_selector('[data-paper-manifest]')
            check(prefix + ': single HTML is controlled by its own root worker',
                  page.evaluate('navigator.serviceWorker.controller.scriptURL') == origin + prefix + 'sw.js')
            get_download(page, '[data-paper-manifest]', prefix + ' worker-pinned manifest', MANIFEST)
            check(prefix + ': actual installed-worker pin is used',
                  page.evaluate("PaperDownloads.state().integrity==='worker-pinned-manifest'"))
            context.close()
        with TemporaryDirectory(prefix='paper-single-entry-') as directory:
            # Open only the final HTML in an otherwise empty temporary folder.
            # No adjacent site assets can accidentally satisfy a file: dependency.
            context = browser.new_context(accept_downloads=True, viewport={'width': 1280, 'height': 900})
            context.add_init_script("localStorage.setItem('paper-lab-learning-v1', JSON.stringify({notes:{'cheng-2025-q-walkthrough':" + json.dumps(SYNTHETIC) + "},done:{},positions:{}}))")
            page = context.new_page()
            page.on('pageerror', lambda e: errors.append(str(e)))
            file_network = []
            file_requests = []
            page.on('request', lambda r: file_network.append(r.url) if urlsplit(r.url).scheme in ('http', 'https') else None)
            page.on('request', lambda r: file_requests.append({'url': r.url, 'type': r.resource_type}))
            isolated = Path(directory) / SINGLE.name
            shutil.copyfile(SINGLE, isolated)
            check('file: isolated copy has exact final HTML bytes', isolated.read_bytes() == SINGLE.read_bytes())
            page.goto(isolated.as_uri() + '#/offline')
            page.wait_for_selector('[data-action="export"]')
            check('file: has no manifest entry or hosted download helper',
                  page.locator('[data-paper-manifest],a[href*="offline-manifest.json"]').count() == 0
                  and page.evaluate('typeof PaperDownloads === "undefined"'))
            check('file: explicitly explains the missing full-resource manifest',
                  '没有完整资源清单' in page.locator('#view').inner_text())
            check_exports(page, 'file:')
            page.screenshot(path=str(OUT / 'file-single-export.png'), full_page=True)
            check('file: no HTTP or HTTPS requests during load and both exports', file_network == [])
            check('file: no adjacent file resource dependency', all(
                urlsplit(r['url']).scheme in ('blob', 'data')
                or (r['type'] == 'document' and r['url'].split('#')[0] == isolated.as_uri())
                for r in file_requests))
            context.close()
        browser.close()
    check('No uncaught page errors', errors == [])
    check('Final deployment tree remains sealed and unchanged', check_seal(SITE) == AUDIT)
    passed = True
finally:
    server.shutdown()
    server.server_close()
    (OUT / 'single-entry-report.json').write_text(json.dumps({
        'status': 'passed' if passed else 'failed', 'checks': checks, 'errors': errors,
        'sourceCommit': AUDIT['sourceCommit'], 'singleHTMLSHA256': hashlib.sha256(SINGLE.read_bytes()).hexdigest(),
        'manifestSHA256': hashlib.sha256(MANIFEST).hexdigest(), 'downloads': downloads,
        'requests': requests,
        'scope': 'Actual generated HTML, Chromium HTTP subdirectories and file protocol; synthetic notes only; no mirror publication',
    }, ensure_ascii=False, indent=2) + '\n')

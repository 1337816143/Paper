#!/usr/bin/env python3
"""Actual generated-page checks for reviewed text additions; synthetic notes only.

Run in the existing supported CI browser job. Static/VM checks do not replace it.
"""
from pathlib import Path
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from urllib.parse import unquote, urlsplit
import hashlib
import json
import re
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / 'dist/site'
OUT = ROOT / 'test-results/research-leads'
OUT.mkdir(parents=True, exist_ok=True)
DATA = json.loads((SITE / 'data.json').read_text())
LEADS = DATA['researchLeads']
assert len(LEADS) == 19
checks, errors = [], []


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def translate_path(self, path):
        name = unquote(urlsplit(path).path)
        target = (SITE / name.removeprefix('/Paper/')).resolve()
        return str(target if name.startswith('/Paper/') and target.is_relative_to(SITE.resolve()) else SITE / '__missing__')

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()


def check(label, condition):
    assert condition, label
    checks.append(label)
    print('PASS', label, flush=True)


def literal_paragraphs(pid, version):
    text = (ROOT / 'resources/research-leads' / pid / (version + '.txt')).read_text().rstrip('\r\n')
    return re.split(r'\r?\n\s*\r?\n', text)


def assert_lead(page, pid):
    block = page.locator('[data-research-lead="' + pid + '"]')
    block.wait_for(state='attached')
    check(pid + ' has one opening addition', block.count() == 1)
    for version in ['full', 'brief']:
        copy = block.locator('[data-lead-version="' + version + '"]')
        check(pid + '/' + version + ' exact accepted paragraphs', copy.locator('p').all_text_contents() == literal_paragraphs(pid, version))
        check(pid + '/' + version + ' is displayed', copy.is_visible())
    return block


server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
Thread(target=server.serve_forever, daemon=True).start()
BASE = f'http://127.0.0.1:{server.server_port}/Paper/'
passed = False
try:
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        context = browser.new_context(viewport={'width': 1280, 'height': 900}, reduced_motion='reduce')
        page = context.new_page()
        page.on('pageerror', lambda e: errors.append(str(e)))
        for pid in LEADS:
            page.goto(BASE + '#/' + pid)
            block = assert_lead(page, pid)
            brief = block.locator('nav a').nth(1)
            brief.focus()
            brief.press('Enter')
            page.wait_for_function('(id) => document.activeElement.matches("h2") && document.activeElement.parentElement.id === id', arg='research-lead-' + pid + '-brief')
            check(pid + ' keyboard opens brief heading', page.url.endswith('/research-lead-' + pid + '-brief'))
            page.go_back()
            page.wait_for_url(BASE + '#/' + pid)
            check(pid + ' native Back preserves both versions', page.locator('[data-lead-version]').count() == 2)
            page.go_forward()
            page.wait_for_url(BASE + '#/' + pid + '/research-lead-' + pid + '-brief')
            page.set_viewport_size({'width': 390, 'height': 844})
            check(pid + ' mobile page does not overflow', page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'))
            page.set_viewport_size({'width': 1280, 'height': 900})
        context.close()

        # First render the exact unchanged article function with its optional
        # overlay disabled, then reload the same profile with the overlay on.
        old = browser.new_context(viewport={'width': 1280, 'height': 900})
        old.add_init_script("""let paperData;
Object.defineProperty(window,'PAPER_DATA',{configurable:true,get(){return paperData;},set(v){
  if(sessionStorage.getItem('synthetic-lead-phase')!=='new')delete v.researchLeads;
  paperData=v;
}});""")
        p = old.new_page()
        p.on('pageerror', lambda e: errors.append(str(e)))
        p.goto(BASE + '#/liang-2022')
        p.wait_for_selector('#lesson-block-0')
        check('pre-addition article renders without overlay', p.locator('.research-lead-overlay').count() == 0)
        note = 'SYNTHETIC legacy note; not a user record'
        p.locator('#note').fill(note)
        original = p.locator('#lesson-block-0').text_content()
        quote = original[:20]
        record = {'id': 'synthetic-before-leads', 'docId': 'lesson:liang-2022', 'type': 'highlight', 'title': 'SYNTHETIC legacy anchor', 'comment': 'Synthetic only', 'tags': [], 'links': [], 'color': 'yellow', 'quote': quote, 'segments': [{'block': 'lesson-block-0', 'start': 0, 'end': len(quote), 'quote': quote, 'prefix': '', 'suffix': original[len(quote):len(quote)+40]}]}
        p.evaluate('(record) => PaperReader.put("annotations", record)', record)
        p.evaluate('sessionStorage.setItem("synthetic-lead-phase", "new")')
        p.reload()
        assert_lead(p, 'liang-2022')
        mark = p.locator('#lesson-block-0 mark[data-annotation="synthetic-before-leads"]')
        mark.wait_for(state='attached')
        check('original local note survives addition', p.locator('#note').input_value() == note)
        check('old highlight resolves at same paragraph and quote', ''.join(mark.all_text_contents()) == quote and p.locator('#lesson-block-0').text_content() == original)
        p.screenshot(path=str(OUT / 'synthetic-legacy-note.png'))
        old.close()

        nojs = browser.new_context(java_script_enabled=False, viewport={'width': 390, 'height': 844})
        p = nojs.new_page()
        for pid in LEADS:
            p.goto(BASE + 'read/' + pid + '.html')
            block = assert_lead(p, pid)
            block.locator('nav a').nth(1).click()
            check(pid + ' script-free brief link works', p.url.endswith('#research-lead-' + pid + '-brief'))
        nojs.close()

        offline = browser.new_context(offline=True, viewport={'width': 390, 'height': 844})
        p = offline.new_page()
        external = []
        p.on('request', lambda r: external.append(r.url) if urlsplit(r.url).scheme in {'http', 'https'} else None)
        p.on('pageerror', lambda e: errors.append(str(e)))
        single = SITE / 'downloads/Paper-Lab-offline.html'
        p.goto(single.resolve().as_uri() + '#/liang-2022')
        assert_lead(p, 'liang-2022')
        check('single HTML embeds all nineteen accepted additions', p.evaluate('Object.keys(PAPER_DATA.researchLeads).length') == 19)
        p.evaluate('location.hash = "#/verdouw-2021"')
        assert_lead(p, 'verdouw-2021')
        check('file-protocol text has no network dependency', not external)
        check('no browser script errors', not errors)
        offline.close()
        browser.close()
        passed = True
finally:
    server.shutdown()
    report = {'passed': passed, 'browser': 'Chromium via Playwright', 'papers': len(LEADS), 'checks': checks, 'errors': errors, 'sourceCommit': json.loads((SITE / 'release.json').read_text())['sourceCommit'], 'dataSHA256': hashlib.sha256((SITE / 'data.json').read_bytes()).hexdigest(), 'syntheticRecordsOnly': True}
    (OUT / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))

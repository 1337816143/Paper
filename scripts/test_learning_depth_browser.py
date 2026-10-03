#!/usr/bin/env python3
"""Browser regression for three appended methods and exact source links.
Synthetic local writing only. No authentication, external writes or user notes.
"""
from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from threading import Thread
from functools import partial
import json
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'dist/site'
RESULTS = ROOT/'test-results'
RESULTS.mkdir(exist_ok=True)

class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

server = ThreadingHTTPServer(('127.0.0.1', 0), partial(Quiet, directory=str(OUT)))
Thread(target=server.serve_forever, daemon=True).start()
BASE = f'http://127.0.0.1:{server.server_port}/'
checks, errors = [], []

def check(label, condition):
    assert condition, label
    checks.append(label)

def goto(page, id):
    page.goto(BASE+'#/'+id)
    page.wait_for_function('(id) => document.querySelector("#view .reader")?.dataset.researchDoc === id', arg=id)

try:
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        context = browser.new_context(viewport={'width': 1280, 'height': 900})
        page = context.new_page()
        page.on('pageerror', lambda e: errors.append(str(e)))
        goto(page, 'whole-farm')
        check('Dimensional definitions and dual-constraint solution appear in the lesson',
              'kg DM/(ha·年)' in page.locator('#s4').inner_text() and
              '1200 h/年' in page.locator('#s6').inner_text())
        original = page.locator('#s1 > .research-section-tools > .research-note-box')
        original.locator('summary').click()
        original.locator('textarea').fill('SYNTHETIC old section s1: retain my unit question')
        page.wait_for_function('JSON.parse(localStorage.getItem("paper-lab-learning-v1")).notes["research::whole-farm::s1"]?.includes("SYNTHETIC")')
        question = page.locator('#self-test details').filter(has_text='同一土地配置从3头增到4头')
        question.locator('summary').click()
        check('Self-test reveals the remaining labour violation', '1200 h' in question.locator('p').inner_text())
        goto(page, 'nutrients')
        check('Both boundaries and the definition-specific efficiency answers are visible',
              all(x in page.locator('#s6').inner_text() for x in ['46.15%', '66.67%', '41.18%', '33.33%']))
        page.locator('#s4 a[href="#/qu-2025"]').click()
        page.wait_for_function('document.querySelector("#view .reader")?.dataset.researchDoc === "qu-2025"')
        source = page.locator('.research-bridge > .research-evidence').filter(has_text='全农场NUE分子分母与损失路径')
        source.locator(':scope > summary').click()
        source.locator('.research-excerpt').wait_for()
        check('NUE source panel loads the exact original paragraph', 'exported animal manure' in source.inner_text())
        source.locator('.research-excerpt > a').first.click()
        page.wait_for_selector('#p4-b17-3c2633d')
        page.locator('#back').click()
        page.wait_for_function('document.querySelector("#view .reader")?.dataset.researchDoc === "qu-2025"')
        check('Exact-source return retains the expanded evidence panel',
              page.locator('.research-bridge > .research-evidence').filter(has_text='全农场NUE分子分母与损失路径').evaluate('(e) => e.open'))
        goto(page, 'breure-2024')
        source = page.locator('.research-bridge > .research-evidence').filter(has_text='风险与不确定性：完整讨论段落')
        source.locator(':scope > summary').click()
        source.locator('.research-excerpt').wait_for()
        check('Risk discussion links to the verified page-8 original block',
              source.locator('a[href="#/original/breure-2024/p8-b2-7105be4"]').count() == 1 and
              'Robustness of TOA results' in source.inner_text())
        goto(page, 'whole-farm')
        check('Old section note remains at s1 after evidence navigation and reload',
              page.locator('#s1 > .research-section-tools > .research-note-box textarea').input_value() ==
              'SYNTHETIC old section s1: retain my unit question')
        for id in ['whole-farm', 'nutrients', 'uncertainty']:
            page.set_viewport_size({'width': 390, 'height': 844})
            goto(page, id)
            check(id+' retains mobile width and plain-text provenance',
                  page.evaluate('document.documentElement.scrollWidth <= innerWidth + 2') and
                  all('[[' not in value for value in page.locator('.source-note').all_inner_texts()))
        page.locator('#s6').scroll_into_view_if_needed()
        page.screenshot(path=str(RESULTS/'learning-depth-mobile.png'), full_page=False)
        page.evaluate('async () => { await navigator.serviceWorker.ready; }')
        page.wait_for_function('!!navigator.serviceWorker.controller', timeout=60000)
        context.set_offline(True)
        page.reload()
        page.wait_for_selector('#s6')
        check('New scenario and regret explanation survives offline reload',
              '最大60' in page.locator('#s6').inner_text() and '最大40' in page.locator('#s6').inner_text())
        context.set_offline(False)
        check('No uncaught application errors', not errors)
        browser.close()
    report = {'passed': True, 'checks': checks, 'errors': errors,
              'scope': 'Synthetic local notes; Chromium desktop and 390px viewport; no real login or two-device recovery test'}
except Exception as exc:
    report = {'passed': False, 'checks': checks, 'errors': errors, 'error': str(exc)}
    raise
finally:
    (RESULTS/'learning-depth-browser-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    server.shutdown()
print(json.dumps({'passed': True, 'checks': len(checks)}))

#!/usr/bin/env python3
"""Actual isolated Q walkthrough browser acceptance (Playwright/Chromium).

Run only in a supported environment, normally GitHub CI:
    python tests/q/browser_test.py

The root environment is known to block Chromium; merely compiling this file
is NOT browser acceptance. Every HTTP request is intercepted locally. Only
original, hash-checked figure images can be served. No analysis service,
external site, user files, storage or authentication is used.

Q_QA_DIR and PW_EXECUTABLE_PATH are optional environment overrides.
The parent app integration suite owns full-app notes/offline/scroll acceptance.
"""
import hashlib
import json
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'examples'))
from q_pipeline import analyze  # noqa: E402

CONFIG = json.loads((ROOT / 'resources/q-walkthrough-v556.json').read_text())
CONFIG['scenarios'] = [dict(scenario, result=analyze(scenario=scenario['id']))
                       for scenario in CONFIG['scenarioDefinitions']]
FILES = {name: (ROOT / 'examples' / name).read_bytes().decode('utf-8') for name in CONFIG['downloads']}
OUT = Path(os.environ.get('Q_QA_DIR', str(ROOT / 'test-results' / 'q')))
OUT.mkdir(parents=True, exist_ok=True)
ORIGIN = 'https://paper-q.invalid/'
GUIDE = '#/cheng-2025-q-walkthrough'
HTML = '''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Q isolated browser acceptance</title>
</head><body><main style="max-width:980px;margin:auto;padding:12px;box-sizing:border-box">
<p id="original-paragraph">Original source sentinel.</p>
<textarea id="private-note" style="max-width:100%">Synthetic private note sentinel</textarea>
<div id="q-host"></div></main></body></html>'''
checks, errors, unexpected = [], [], []


def check(label, condition):
    assert condition, label
    checks.append(label)
    print('PASS', label)


def boot(browser, *, protocol='https:', reduced_motion='no-preference', color_scheme='light', missing_images=False):
    context = browser.new_context(viewport={'width': 1100, 'height': 900},
                                  reduced_motion=reduced_motion, color_scheme=color_scheme,
                                  accept_downloads=True)
    page = context.new_page()
    page.on('pageerror', lambda error: errors.append(str(error)))
    assets = {ORIGIN + figure['path']: ROOT / 'resources' / figure['path']
              for figure in CONFIG['source']['figures']}

    def serve(route):
        url = route.request.url
        if url == ORIGIN:
            route.fulfill(status=200, content_type='text/html; charset=utf-8', body=HTML)
        elif url in assets:
            if missing_images:
                route.fulfill(status=404, body='Deliberate missing image')
            else:
                route.fulfill(status=200, content_type='image/png', body=assets[url].read_bytes())
        elif url.startswith('file:'):
            route.continue_()
        else:
            unexpected.append(url)
            route.abort()

    page.route('**/*', serve)
    page.clock.install()
    if protocol == 'file:':
        fixture = OUT / 'single-file-fixture.html'
        fixture.write_text(HTML)
        page.goto(fixture.as_uri())
    else:
        page.goto(ORIGIN)
    page.add_style_tag(content=(ROOT / 'src/style.css').read_text())
    page.add_style_tag(content=(ROOT / 'src/q-walkthrough.css').read_text())
    page.evaluate('''({config, files, guide})=>{
      window.PAPER_Q=config; window.PAPER_DATA={files};
      history.replaceState({}, '', guide);
      window.fixtureRoute=location.hash;
      // The host listener is registered BEFORE the panel's listeners, like app.js.
      // Native popstate must remount before the paired hashchange reaches the new panel.
      window.hostRender=()=>{
        window.fixtureRoute=location.hash;
        const host=document.querySelector('#q-host');
        host.replaceChildren();
        if(location.hash.startsWith(guide)) window.qController=PaperQWalkthrough.mount(host);
        else host.innerHTML='<p id="source-page">Original reader destination sentinel.</p>';
      };
      window.addEventListener('popstate',hostRender);
      window.addEventListener('hashchange',()=>{if(fixtureRoute!==location.hash)hostRender()});
    }''', {'config': CONFIG, 'files': FILES, 'guide': GUIDE})
    page.add_script_tag(content=(ROOT / 'src/q-walkthrough.js').read_text())
    page.evaluate('window.qController=PaperQWalkthrough.mount(document.querySelector("#q-host"))')
    return context, page


def state(page):
    return page.evaluate('qController.getState()')


def step(page, number):
    page.locator(f'[data-step="{number}"]').click()


def field(page, name, value):
    page.locator(f'[data-field="{name}"]').select_option(str(value))


def text(page):
    return page.locator('.q-stage').inner_text()


def no_body_overflow(page):
    return page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')


def contrast(page, selector):
    return page.locator(selector).first.evaluate('''el=>{
      const rgb=s=>s.match(/[\\d.]+/g).slice(0,3).map(Number);
      const lum=s=>rgb(s).map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4}).reduce((a,v,i)=>a+v*[.2126,.7152,.0722][i],0);
      const style=getComputedStyle(el),ink=lum(style.color);
      let node=el,bg=style.backgroundColor;
      while((bg==='rgba(0, 0, 0, 0)' || bg==='transparent')&&node.parentElement){node=node.parentElement;bg=getComputedStyle(node).backgroundColor}
      const paper=lum(bg);return (Math.max(ink,paper)+.05)/(Math.min(ink,paper)+.05);
    }''')


with sync_playwright() as pw:
    launch = {'headless': True}
    if os.environ.get('PW_EXECUTABLE_PATH'):
        launch['executable_path'] = os.environ['PW_EXECUTABLE_PATH']
    browser = pw.chromium.launch(**launch)  # A launch failure is a failed/not-run check.
    try:
        context, page = boot(browser)
        page.clock.fast_forward(60000)
        check('No autoplay, no pending timer, default P01/S01', state(page)['step'] == 0
              and state(page)['person'] == 'P01' and state(page)['statement'] == 'S01'
              and not state(page)['pendingTimer'])
        page.evaluate('PaperQWalkthrough.mount(document.querySelector("#q-host"))')
        check('Mount is idempotent', page.locator('.q-walkthrough').count() == 1)
        check('Step navigation attributes belong only to the eight buttons',
              page.locator('[data-step]').count() == 8
              and page.locator('[data-step]').evaluate_all("els=>els.every(el=>el.tagName==='BUTTON')"))
        check('Legacy source and private-note sentinels survive',
              page.locator('#original-paragraph').inner_text() == 'Original source sentinel.'
              and page.locator('#private-note').input_value() == 'Synthetic private note sentinel'
              and page.locator('.q-walkthrough .prose,.q-walkthrough [data-block]').count() == 0)
        for scenario in CONFIG['scenarios']:
            field(page, 'scenario', scenario['id'])
            for number in range(8):
                step(page, number)
                check(f'{scenario["id"]}: stage {number + 1} renders without invalid numbers',
                      len(text(page)) > 400 and 'NaN' not in text(page) and 'Infinity' not in text(page))
                check(f'{scenario["id"]}: stage {number + 1} focuses new heading',
                      page.evaluate('document.activeElement === document.querySelector(".q-stage h3")'))
            step(page, 0)
        field(page, 'scenario', 'baseline')
        person = page.locator('[data-field="person"]')
        person.focus()
        page.evaluate('window.savedQSelector=document.activeElement')
        person.select_option('P07')
        field(page, 'statement', 'S18')
        check('Persistent selector DOM identity survives updates', page.evaluate(
              'savedQSelector===document.querySelector("[data-field=person]")'))
        person.focus()
        person.select_option('P07')
        check('Selector focus and automatic-update guard survive update', page.evaluate(
              'document.activeElement===savedQSelector && PaperQWalkthrough.isBusy()'))
        check('Selected input cell actually changes', 'D[S18, P07] = 4' in text(page))
        step(page, 1)
        field(page, 'other', 'P04')
        check('Correlation selected objects propagate into numeric substitution',
              'corr(P07, P04)' in text(page)
              and page.locator('[data-correlation="6-3"] rect').get_attribute('stroke-width') == '4')
        step(page, 2)
        field(page, 'factor', 1)
        field(page, 'loadingView', 'geometry')
        angle = page.locator('[data-field="angle"]')
        angle.fill('45')
        check('Geometry preview uses selected angle and names its boundary',
              state(page)['angle'] == 45 and 'GEOMETRY PREVIEW' in text(page))
        angle.fill('181')
        check('Invalid angle retains last valid numerical state',
              state(page)['invalid'] and state(page)['angle'] == 45
              and angle.get_attribute('aria-invalid') == 'true')
        angle.fill('45')
        check('Valid same-angle recovery clears displayed error',
              not state(page)['invalid'] and not page.locator('.q-error').is_visible())
        step(page, 4)
        weighted = text(page)
        step(page, 2)
        angle.fill('-90')
        step(page, 4)
        check('Geometry cannot silently change downstream fixed results', text(page) == weighted)
        step(page, 3)
        page.locator('[data-scenario-select="reverse-p03"]').click()
        step(page, 4)
        expected_weight = CONFIG['scenarios'][1]['result']['weights'][2][0]
        check('Recomputed negative P03 has a negative signed contribution',
              state(page)['scenario'] == 'reverse-p03' and state(page)['person'] == 'P03'
              and f'{expected_weight:.6f}' in text(page) and 'w′x′=wx−6w' in text(page))
        step(page, 6)
        page.locator('.q-example-actions [data-statement="S04"]').click()
        check('S04 exposes unequal grid scores but no .05 distinction',
              'S04：两份网格分数=3 / 4' in text(page) and '→ p<.05 未检出差异' in text(page))
        page.locator('.q-example-actions [data-statement="S12"]').click()
        check('S12 exposes .05-only distinction',
              '→ p<.05 可区分' in text(page) and 'p<.01 未检出差异' in text(page))
        step(page, 0)
        page.locator('.q-navigation').last.locator('[data-action="next"]').click()
        check('Long-table navigation brings new heading into view', page.locator('.q-stage h3').evaluate(
              'el=>{const r=el.getBoundingClientRect();return r.top>=0 && r.top<innerHeight/2}'))
        page.locator('[data-field="person"]').focus()
        old_step = state(page)['step']
        page.keyboard.press('ArrowRight')
        check('Form arrow keys do not change stages', state(page)['step'] == old_step)
        page.locator('.q-chart-scroll').first.focus()
        page.keyboard.press('ArrowRight')
        check('Chart native scrolling does not change stages', state(page)['step'] == old_step)
        page.locator('.q-walkthrough').focus()
        page.keyboard.press('End')
        check('Panel-only keyboard navigation works', state(page)['step'] == 7)
        for figure in CONFIG['source']['figures']:
            image = page.locator(f'img[src="{figure["path"]}"]')
            image.scroll_into_view_if_needed()
            page.wait_for_function('(img)=>img.complete && img.naturalWidth>0', arg=image.element_handle())
            image_hash = hashlib.sha256((ROOT / 'resources' / figure['path']).read_bytes()).hexdigest()
            check('Untouched original source hash: ' + figure['id'], image_hash == figure['sha256'])
        check('All original figures are separate images', page.locator('.q-source-figure img').count() == 3)
        check('Source bridge preserves unknown scaling', '精确缩放公式未确认' in text(page))
        source_detail=page.locator('.q-stage details').first
        source_detail.locator('summary').click()
        return_state=state(page)
        check('History stores only an opaque panel key, never teaching choices',
              page.evaluate('typeof history.state.paperQEntry === "string" && !Object.hasOwn(history.state,"person") && !Object.hasOwn(history.state,"statement")'))
        # A genuine browser history traversal, not a synthetic dispatchEvent test.
        page.locator(f'a[href="{CONFIG["source"]["figures"][0]["anchor"]}"]').click()
        page.wait_for_selector('#source-page')
        check('Original-reader route clears panel release guard', not page.evaluate('PaperQWalkthrough.isBusy()'))
        page.go_back()
        page.wait_for_selector('.q-walkthrough')
        page.wait_for_function('location.hash === "#/cheng-2025-q-walkthrough"')
        check('Native Back popstate plus hashchange preserves newly mounted panel',
              page.locator('.q-walkthrough').count() == 1 and state(page)['mounted'])
        check('Original-source Back restores the same stage, choices and open explanation',
              all(state(page)[key]==return_state[key] for key in ['step','scenario','person','statement','factor','other','loadingView','angle'])
              and page.locator('.q-stage details').first.evaluate('(el)=>el.open'))
        page.go_forward()
        page.wait_for_selector('#source-page')
        check('Native Forward leaves Q and destroys old panel',
              page.locator('.q-walkthrough').count() == 0 and not page.evaluate('PaperQWalkthrough.isBusy()'))
        page.go_back()
        page.wait_for_selector('.q-walkthrough')
        check('Second native Back remount remains interactive', state(page)['mounted'])
        step(page, 4)
        check('Returned panel handles a new stage', state(page)['step'] == 4)
        page.locator('.q-downloads summary').click()
        for name in CONFIG['downloads']:
            with page.expect_download() as download_info:
                page.locator(f'[data-q-download="{name}"]').click()
            download = download_info.value
            check('Download has exact packaged content: ' + name,
                  Path(download.path()).read_bytes() == FILES[name].encode('utf-8'))
            page.clock.fast_forward(1200)
        check('Download URL timers clean up', not state(page)['pendingTimer'])
        page.screenshot(path=str(OUT / 'desktop-weighted-contributions.png'), full_page=True)
        for width in [320, 390]:
            page.set_viewport_size({'width': width, 'height': 780})
            for number in range(8):
                step(page, number)
                check(f'{width}px stage {number + 1}: no page-wide overflow', no_body_overflow(page))
                regions = page.locator('.q-table-scroll,.q-chart-scroll,.q-grid,.q-source-scroll')
                check(f'{width}px stage {number + 1}: scroll containers remain inside viewport',
                      regions.evaluate_all('els=>els.every(el=>el.getBoundingClientRect().right<=innerWidth+1)'))
                check(f'{width}px stage {number + 1}: scroll hint visible',
                      page.locator('.q-stage .q-scroll-hint:visible').count() > 0)
                if number == 2:
                    check(f'{width}px collapsed PCA detail preserves both visible chart hints',
                          page.locator('.q-stage > details').first.evaluate('(el)=>!el.open')
                          and page.locator('.q-stage .q-figure .q-scroll-hint').count() == 2
                          and page.locator('.q-stage .q-figure .q-scroll-hint:visible').count() == 2)
            step(page, 1)
            page.screenshot(path=str(OUT / f'mobile-{width}-correlation.png'), full_page=True)
        context.close()
        for scheme in ['light', 'dark']:
            c, p = boot(browser, color_scheme=scheme, reduced_motion='reduce')
            if scheme == 'dark':
                p.evaluate('document.body.classList.add("dark")')
            step(p, 2)
            for selector in ['.q-status', '.q-equation', '.q-scroll-hint', '.q-steps [aria-current="step"]']:
                check(f'{scheme} text contrast >=4.5: {selector}', contrast(p, selector) >= 4.5)
            check(f'{scheme} reduced-motion has no autoplay', not state(p)['pendingTimer'])
            p.screenshot(path=str(OUT / f'{scheme}-extraction.png'), full_page=True)
            c.close()
        c, p = boot(browser, protocol='file:')
        step(p, 7)
        check('Single-file mode shows explicit original-image fallback',
              p.locator('.q-source-figure img').count() == 0 and '原图未嵌入' in text(p))
        for number in range(7):
            step(p, number)
            check(f'Single-file synthetic stage {number + 1} still works', len(text(p)) > 400)
        c.close()
        c, p = boot(browser, missing_images=True)
        step(p, 7)
        p.locator('.q-source-figure img').evaluate_all('images=>images.forEach(img=>img.loading="eager")')
        p.wait_for_function('Array.from(document.querySelectorAll(".q-source-figure img")).every(img=>img.hidden)')
        check('Missing source images reveal three readable fallbacks',
              p.locator('.q-image-status:visible').count() == 3)
        c.close()
        check('No unhandled page errors', not errors)
        check('No requests beyond local fixture and original figures', not unexpected)
        report = {'status': 'passed', 'checks': checks, 'browser': browser.version,
                  'scope': 'Actual isolated Chromium UI, native Back/Forward, mobile overflow, focus, downloads and original-image checks. Full host offline/notes integration is a separate suite.',
                  'errors': errors, 'unexpected_requests': unexpected}
        (OUT / 'browser-result.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
        print(json.dumps({'passed': len(checks), 'report': str(OUT / 'browser-result.json')}))
    except Exception as error:
        diagnostic = {}
        # Capture while Playwright and the failed page are still alive.
        opened = [p for c in browser.contexts for p in c.pages if not p.is_closed()]
        if opened:
            failed_page = opened[-1]
            try:
                failed_page.screenshot(path=str(OUT / 'last-failure.png'), full_page=True)
                diagnostic = failed_page.evaluate('''()=>({url:location.href,
                  state:window.qController?.getState(),
                  hints:[...document.querySelectorAll('.q-stage .q-scroll-hint')].map(el=>({
                    text:el.textContent, hiddenInDetails:!!el.closest('details:not([open])'),
                    rectangles:el.getClientRects().length, display:getComputedStyle(el).display,
                    visibility:getComputedStyle(el).visibility}))})''')
            except Exception as capture_error:
                diagnostic = {'capture_error':str(capture_error)}
        (OUT / 'browser-result.json').write_text(json.dumps({
            'status': 'failed', 'checks_completed': checks, 'error': str(error),
            'page_errors': errors, 'unexpected_requests': unexpected, 'diagnostic': diagnostic,
            'scope': 'Actual isolated Chromium acceptance; a partial run is not a pass.'
        }, ensure_ascii=False, indent=2))
        raise
    finally:
        browser.close()

#!/usr/bin/env python3
"""Actual Chromium checks for the isolated RDA panel (Playwright 1.55.0).

All HTTP-looking requests are locally intercepted; no server or external website
is used. Only the unchanged repository Fig. 7 can be served. A successful Chromium
launch is required. A blocked launch is NOT a passing browser test.

Run in CI: python tests/rda/browser_test.py
Optional: RDA_QA_DIR, PW_EXECUTABLE_PATH. Do not run where Chromium is known blocked.
"""
import csv
import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(os.environ.get('RDA_QA_DIR', str(ROOT / 'test-results' / 'rda')))
OUT.mkdir(parents=True, exist_ok=True)
CONFIG = json.loads((ROOT / 'resources/rda-walkthrough-v555.json').read_text())
with (ROOT / 'examples/rda_synthetic_villages.csv').open() as stream:
    CONFIG['records'] = [{key: value if key == 'village_id' else float(value)
                          for key, value in row.items()} for row in csv.DictReader(stream)]
FIGURE = ROOT / 'resources' / CONFIG['source']['figurePath']
ORIGIN = 'https://paper-rda.invalid/'
HTML = '''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>RDA isolated UI QA</title>
</head><body><main class="reader" style="max-width:860px;margin:auto;padding:12px">
<p id="original-paragraph" class="prose">Original paragraph sentinel.</p>
<textarea id="private-note" style="max-width:100%">Synthetic private note sentinel</textarea>
<div id="rda-host"></div></main></body></html>'''
checks, errors, unexpected = [], [], []


def check(name, ok):
    assert ok, name
    checks.append(name)
    print('PASS', name)


def boot(browser, *, fixture_url=None, config=None, **options):
    context = browser.new_context(viewport={'width': 1100, 'height': 1000}, **options)
    page = context.new_page()
    page.on('pageerror', lambda error: errors.append(str(error)))

    def serve(route):
        url = route.request.url
        if url == ORIGIN:
            route.fulfill(status=200, content_type='text/html; charset=utf-8', body=HTML)
        elif url == ORIGIN + CONFIG['source']['figurePath']:
            route.fulfill(status=200, content_type='image/png', body=FIGURE.read_bytes())
        elif url.startswith('file:'):
            route.continue_()
        else:
            unexpected.append(url)
            route.abort()

    page.route('**/*', serve)
    page.clock.install()
    page.goto(fixture_url or ORIGIN)
    for name in ['style.css', 'rda-walkthrough.css']:
        page.add_style_tag(content=(ROOT / 'src' / name).read_text())
    page.evaluate('(config)=>{window.PAPER_RDA=config}', config or CONFIG)
    for name in ['rda-model.js', 'rda-walkthrough.js']:
        page.add_script_tag(content=(ROOT / 'src' / name).read_text())
    page.evaluate('window.rdaController=PaperRDA.mount(document.querySelector("#rda-host"))')
    return context, page


def state(page):
    return page.evaluate('rdaController.getState()')


def busy(page):
    return page.evaluate('PaperRDA.isBusy()')


def step(page, n):
    page.locator(f'[data-step="{n}"]').click()


def click(page, action):
    page.locator(f'[data-action="{action}"]').click()


def text(page, selector='.rda-stage'):
    return page.locator(selector).inner_text()


def contrast_check(page):
    return page.evaluate('''()=>{
      const root=document.querySelector('.rda-walkthrough');
      const rgb=value=>value.match(/[\\d.]+/g).slice(0,3).map(Number);
      const luminance=color=>rgb(color).map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4}).reduce((s,v,i)=>s+v*[.2126,.7152,.0722][i],0);
      const surface=luminance(getComputedStyle(root).backgroundColor);
      return ['.rda-stage-head p','.rda-footnote','.rda-equation'].map(selector=>{
        const el=root.querySelector(selector); if(!el)return 21;
        const ink=luminance(getComputedStyle(el).color);
        const bg=luminance(getComputedStyle(el).backgroundColor)==0?surface:luminance(getComputedStyle(el).backgroundColor);
        return (Math.max(ink,bg)+.05)/(Math.min(ink,bg)+.05);
      });
    }''')


with sync_playwright() as pw:
    opts = {'headless': True}
    if os.environ.get('PW_EXECUTABLE_PATH'):
        opts['executable_path'] = os.environ['PW_EXECUTABLE_PATH']
    browser = pw.chromium.launch(**opts)
    try:
        context, page = boot(browser)
        page.clock.fast_forward(60000)
        check('No autoplay or pending timer after one minute', state(page)['step'] == 0 and not state(page)['pendingTimer'] and not busy(page))
        page.evaluate('PaperRDA.mount(document.querySelector("#rda-host"))')
        check('Mount is idempotent', page.locator('.rda-walkthrough').count() == 1)
        check('Legacy paragraph and private sentinel untouched', page.locator('#original-paragraph').text_content() == 'Original paragraph sentinel.' and page.locator('#private-note').input_value() == 'Synthetic private note sentinel' and page.locator('.rda-walkthrough .prose,.rda-walkthrough [data-block]').count() == 0)
        for n in range(6):
            step(page, n)
            check(f'Manual stage {n+1} renders', state(page)['step'] == n and len(text(page)) > 150)
        step(page, 3)
        for value in ['1.388889', '0.611111', '0.833333', '0.555556', '41.667%', '27.778%', '60.000%', '40.000%', '30.556%']:
            check('Default decomposition includes ' + value, value in text(page))
        field = page.locator('[data-field="v4B"]')
        field.fill('4.25')
        check('Edit recomputes two eigenvalues', '0.907322' in text(page) and '0.435815' in text(page))
        check('Number edit preserves focus and guards updates', field.evaluate('(el)=>el===document.activeElement') and busy(page))
        field.press('ArrowUp')
        check('Native number keyboard increments without changing stage', state(page)['v4B'] == 4.5 and state(page)['step'] == 3 and field.evaluate('(el)=>el===document.activeElement'))
        field.fill('4.25')
        for invalid in ['', '-1', '5.25', '3.76']:
            field.fill(invalid)
            check('Invalid input retains last valid model: '+repr(invalid), state(page)['v4B'] == 4.25 and field.get_attribute('aria-invalid') == 'true' and '上次有效结果' in text(page, '.rda-status'))
        field.fill('0')
        check('Zero is accepted only as an explicit valid value', state(page)['v4B'] == 0 and not state(page)['invalid'])
        field.fill('5')
        check('Upper boundary is valid', state(page)['v4B'] == 5)
        click(page, 'reset')
        check('Reset restores all defaults and clears guard', state(page)['step'] == 0 and state(page)['v4B'] == 3.75 and state(page)['village'] == 'V1' and state(page)['view'] == 'variables' and state(page)['denominator'] == 'total' and not busy(page))
        for village in ['V1', 'V2', 'V3', 'V4']:
            page.locator('[data-field="village"]').select_option(village)
            step(page, 1)
            check(village+' numeric substitution', village+' 的 A' in text(page))
            step(page, 2)
            check(village+' original-unit reconstruction', village+'：把原始分数重建回来' in text(page))
        step(page, 4)
        before = page.locator('[data-variable="A"] circle').get_attribute('cx')
        page.locator('[data-field="denominator"]').focus()
        page.locator('[data-field="denominator"]').select_option('constrained')
        check('Denominator focus stays on original control', page.locator('[data-field="denominator"]').evaluate('(el)=>el===document.activeElement'))
        check('Changing denominator updates axis label without moving dot', '60.000%' in text(page, 'svg') and page.locator('[data-variable="A"] circle').get_attribute('cx') == before)
        check('Residual and angle/whole-correlation discrepancy remain visible', all(value in text(page) for value in ['30.556%', '0.272166', '0.894427', '0.816497']))
        page.locator('.rda-walkthrough').screenshot(path=str(OUT / 'desktop-variable-correlations.png'))
        page.locator('[data-field="view"]').focus()
        page.locator('[data-field="view"]').select_option('observations')
        check('View change retains focus and distinguishes village scores', page.locator('[data-field="view"]').evaluate('(el)=>el===document.activeElement') and page.locator('[data-village]').count() == 4 and page.locator('[data-variable]').count() == 0 and '观察标准化分数投影' in text(page) and '不是原文响应指标的圆点' in text(page))
        page.locator('.rda-walkthrough').screenshot(path=str(OUT / 'desktop-village-scores.png'))
        for n, selector in [(0, '.rda-table-scroll'), (4, '.rda-chart-scroll')]:
            step(page, n)
            scroller = page.locator(selector).first
            scroller.focus()
            scroller.press('ArrowRight')
            check('Native scroller keeps arrow keys: '+selector, state(page)['step'] == n)
        page.locator('.rda-walkthrough').focus()
        page.keyboard.press('Home')
        page.keyboard.press('ArrowRight')
        check('Focused panel supports manual arrow navigation', state(page)['step'] == 1)
        step(page, 5)
        image = page.locator('.rda-source-figure img')
        image.scroll_into_view_if_needed()
        page.wait_for_function('document.querySelector(".rda-source-figure img").complete && document.querySelector(".rda-source-figure img").naturalWidth>0')
        check('Actual Fig.7 uses the verified unchanged source bytes', hashlib.sha256(FIGURE.read_bytes()).hexdigest() == CONFIG['source']['figureHash'] and image.get_attribute('src') == CONFIG['source']['figurePath'])
        page.locator('.rda-source-variables summary').click()
        check('All14 original X definitions and dates are rendered', all(v['unit'] in text(page) and v['year'] in text(page) for v in CONFIG['variables']))
        check('Revenue is not called profit and source dots are not villages', '不是利润' in text(page) and '不是35个村庄' in text(page) and '价格 × 产量' in text(page))
        image.dispatch_event('error')
        check('Image failure leaves explicit fallback', page.locator('.rda-image-status').is_visible() and not image.is_visible())
        for n in range(6):
            step(page, n)
            issues = page.evaluate('''()=>{
              const root=document.querySelector('.rda-walkthrough'),issues=[];
              const ids=[...document.querySelectorAll('[id]')].map(el=>el.id);
              if(new Set(ids).size!==ids.length)issues.push('duplicate IDs');
              for(const el of root.querySelectorAll('input,select'))if(!root.querySelector(`label[for="${el.id}"]`))issues.push('unlabelled input');
              for(const el of root.querySelectorAll('button'))if(!el.textContent.trim()&&!el.getAttribute('aria-label'))issues.push('unnamed button');
              for(const el of root.querySelectorAll('svg'))if(!el.querySelector('title')||!el.querySelector('desc'))issues.push('missing SVG alternative');
              for(const el of root.querySelectorAll('table'))if(!el.caption||!el.querySelector('th[scope=col]'))issues.push('missing table semantics');
              return issues;
            }''')
            check(f'Semantic controls, tables and SVG alternatives in stage {n+1}', not issues)
        step(page, 1)
        check('Light text contrast meets4.5:1', min(contrast_check(page)) >= 4.5)
        page.evaluate('document.body.classList.add("dark")')
        check('Dark theme uses correct ink and text contrast', page.locator('.rda-walkthrough').evaluate('(el)=>getComputedStyle(el).color') == 'rgb(229, 235, 227)' and min(contrast_check(page)) >= 4.5)
        page.locator('.rda-walkthrough').screenshot(path=str(OUT / 'desktop-dark-standardization.png'))
        page.evaluate('dispatchEvent(new HashChangeEvent("hashchange"))')
        check('Route change destroys panel and releases busy guard', not state(page)['mounted'] and not busy(page) and page.locator('.rda-walkthrough').count() == 0)
        page.evaluate('window.rdaController=PaperRDA.mount(document.querySelector("#rda-host"))')
        page.evaluate('document.querySelector("#rda-host").remove()')
        page.wait_for_function('!rdaController.getState().mounted')
        check('Detach cleans up controller', not busy(page))
        context.close()

        mobile, mp = boot(browser, is_mobile=True, device_scale_factor=1)
        for width in [360, 320]:
            mp.set_viewport_size({'width': width, 'height': 800})
            for n in range(6):
                step(mp, n)
                check(f'{width}px stage{n+1} has no page overflow', mp.evaluate('document.documentElement.scrollWidth<=innerWidth+1'))
            step(mp, 4)
            mp.locator('[data-field="view"]').select_option('observations')
            check(f'{width}px observation plot also stays inside page', mp.evaluate('document.documentElement.scrollWidth<=innerWidth+1'))
            check(f'{width}px chart provides internal scrolling', mp.locator('.rda-chart-scroll').evaluate('(el)=>el.scrollWidth>el.clientWidth'))
        mp.locator('.rda-walkthrough').screenshot(path=str(OUT / 'mobile-village-scores.png'))
        mobile.close()

        reduced, rp = boot(browser, reduced_motion='reduce')
        rp.clock.fast_forward(60000)
        check('Reduced motion leaves initial stage unchanged', state(rp)['step'] == 0 and not state(rp)['pendingTimer'])
        step(rp, 4)
        check('Reduced motion retains charts and no CSS animation', rp.locator('svg').count() == 1 and rp.locator('[aria-current="step"]').evaluate('(el)=>getComputedStyle(el).animationName') == 'none')
        reduced.close()

        singular = json.loads(json.dumps(CONFIG))
        for row in singular['records']:
            row['perception_a'] = 3.75 if row['village_id'] == 'V4' else row['perception_a']
            row['perception_b'] = row['perception_a']
        zero, zp = boot(browser, config=singular)
        step(zp, 4)
        check('Undefined correlations never get drawn as zero-valued variables', zp.locator('[data-variable]').count() == 0 and '未定义（零方差轴）' in text(zp) and 'NaN' not in text(zp))
        zp.locator('[data-field="view"]').select_option('observations')
        check('Rank-one village view omits undefined2D axis and table coordinates', zp.locator('svg').count() == 0 and zp.locator('[data-village]').count() == 0 and '二维村庄图不绘制' in text(zp) and '未定义（零方差轴）' in text(zp))
        zero.close()

        with TemporaryDirectory(prefix='paper-rda-offline-') as temp:
            fixture = Path(temp) / 'rda-offline.html'
            fixture.write_text(HTML)
            offline, op = boot(browser, fixture_url=fixture.as_uri())
            step(op, 5)
            check('file: mode explicitly states original image is not embedded', op.locator('img').count() == 0 and '原图未嵌入' in text(op))
            step(op, 4)
            check('file: mode retains synthetic SVG and numeric tables', op.locator('svg').count() == 1 and op.locator('table').count() >= 2)
            offline.close()

        check('No page JavaScript errors', not errors)
        check('No unexpected network requests; fixtures only', not unexpected)
        report = {'passed': checks, 'pageErrors': errors, 'unexpectedNetworkRequests': unexpected,
                  'scope': 'Actual Chromium isolated panel; local interception only. Does not assert screen-reader conformance or whole-app integration.'}
        (OUT / 'browser-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
        print(json.dumps({'passed': len(checks), 'report': str(OUT / 'browser-report.json')}))
    except Exception as error:
        report = {'passed': False, 'checks': checks, 'pageErrors': errors, 'error': str(error), 'scope': 'Actual Chromium isolated RDA panel'}
        for index, candidate in enumerate(browser.contexts):
            for j, current in enumerate(candidate.pages):
                try:
                    current.screenshot(path=str(OUT / f'failure-{index}-{j}.png'))
                except Exception:
                    pass
        (OUT / 'browser-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
        raise
    finally:
        browser.close()

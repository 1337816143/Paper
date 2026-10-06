#!/usr/bin/env python3
"""Actual isolated Chromium acceptance. Requires Python Playwright==1.55.0.

Run in parent CI / a supported browser environment, never retry the known-blocked
local Chromium socket. Compilation and DOM simulation are NOT browser passes.
Every fixture request is local/intercepted. Host build/offline-cache/note integration
remains a separate parent acceptance suite; this file states that scope honestly.
"""
import csv
import io
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(os.environ.get('ANNUAL_QA_DIR', str(ROOT / 'test-results' / 'annual-balance')))
OUT.mkdir(parents=True, exist_ok=True)
ORIGIN = 'https://paper-annual.invalid/'
GUIDE = '#/farmdesign-2012-balance-walkthrough/annual-balance'
OTHER_GUIDE = '#/qu-2025-chain-walkthrough/annual-balance'
HTML = '''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><link rel="icon" href="data:,"><title>Annual balance isolated QA</title>
<style>html,body{margin:0}body{font-family:system-ui,sans-serif}main{max-width:1000px;margin:auto;padding:12px;box-sizing:border-box}textarea{max-width:100%;box-sizing:border-box}</style>
</head><body><main><p id="original-paragraph">Unchanged source sentinel.</p>
<textarea id="private-note">Synthetic note sentinel</textarea><div id="annual-host"></div></main></body></html>'''
checks, errors, unexpected = [], [], []


def check(name, condition):
    assert condition, name
    checks.append(name)
    print('PASS', name)


def boot(browser, *, color_scheme='light', width=1100, file_mode=False, theme=None):
    context = browser.new_context(viewport={'width': width, 'height': 900},
                                  color_scheme=color_scheme, reduced_motion='reduce',
                                  accept_downloads=True)
    page = context.new_page()
    page.on('pageerror', lambda error: errors.append(str(error)))

    def serve(route):
        if route.request.url == ORIGIN:
            route.fulfill(status=200, content_type='text/html;charset=utf-8', body=HTML)
        elif route.request.url.startswith('file:'):
            route.continue_()
        else:
            unexpected.append(route.request.url)
            route.abort()

    page.route('**/*', serve)
    page.clock.install()
    if file_mode:
        fixture = OUT / 'annual-single-file-fixture.html'
        fixture.write_text(HTML)
        page.goto(fixture.as_uri())
    else:
        page.goto(ORIGIN)
    base_css = ROOT / 'src/style.css'
    if base_css.exists():
        page.add_style_tag(content=base_css.read_text())
    page.add_style_tag(content=(ROOT / 'src/annual-balance-walkthrough.css').read_text())
    page.evaluate('''({guide,other})=>{
      history.replaceState({},'',guide); window.fixtureHash=location.hash;
      // These synthetic sentinels are the fixture's, never real user notes.
      localStorage.setItem('annual-qa-note','synthetic-preserved');
      sessionStorage.setItem('annual-qa-session','synthetic-preserved');
      window.fixtureStorage=JSON.stringify([Object.entries(localStorage),Object.entries(sessionStorage)]);
      window.hostRender=()=>{
        window.fixtureHash=location.hash;
        const oldHost=document.querySelector('#annual-host');
        const host=document.createElement('div'); host.id='annual-host';
        oldHost.replaceWith(host);
        if(location.hash===guide || location.hash===other)
          window.annualController=PaperAnnualBalance.mount(host);
        else host.innerHTML='<p id="original-destination">Original reader destination sentinel.</p>';
      };
      // As in app.js, host render precedes the panel's lifecycle handlers.
      addEventListener('popstate',hostRender);
      addEventListener('hashchange',()=>{if(fixtureHash!==location.hash)hostRender()});
    }''', {'guide': GUIDE, 'other': OTHER_GUIDE})
    for name in ['annual-balance-model.js', 'annual-balance-walkthrough.js']:
        page.add_script_tag(content=(ROOT / 'src' / name).read_text())
    page.evaluate('window.annualController=PaperAnnualBalance.mount(document.querySelector("#annual-host"))')
    if (theme or color_scheme) == 'dark':
        page.evaluate('document.body.classList.add("dark")')
    return context, page


def state(page):
    return page.evaluate('annualController.getState()')


def step(page, number):
    page.locator(f'[data-annual-stage="{number}"]').click()


def field(page, name, value):
    selector = f'[data-annual-field="{name}"]'
    if name == 'replaceRetained':
        page.locator(selector).set_checked(value)
    else:
        page.locator(selector).fill(str(value))


def metric(page, name):
    return page.locator(f'[data-annual-value="{name}"]').inner_text()


def no_overflow(page):
    return page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')


def figure_text_problems(page):
    return page.locator('.annual-figure svg').evaluate('''svg=>{
      const items=[...svg.querySelectorAll('text')].map(el=>({text:el.textContent,box:el.getBBox()}));
      const problems=[];
      for(let i=0;i<items.length;i++){
        const a=items[i].box;
        if(a.x<0||a.y<0||a.x+a.width>980||a.y+a.height>650)problems.push('outside: '+items[i].text);
        for(let j=i+1;j<items.length;j++){
          const b=items[j].box;
          if(a.x<b.x+b.width-1&&a.x+a.width>b.x+1&&a.y<b.y+b.height-1&&a.y+a.height>b.y+1)
            problems.push(items[i].text+' overlaps '+items[j].text);
        }
      }
      return problems;
    }''')


def contrast(page, selector):
    return page.locator(selector).first.evaluate(r'''el=>{
      const color=s=>(s.match(/[\d.]+/g)||[]).map(Number);
      const luminance=c=>c.slice(0,3).map(v=>v/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4).reduce((sum,v,i)=>sum+v*[.2126,.7152,.0722][i],0);
      let bg=null,node=el;
      while(node&&!bg){const c=color(getComputedStyle(node).backgroundColor);if(c.length>=3&&(c.length<4||c[3]===1))bg=c;node=node.parentElement;}
      const fg=luminance(color(getComputedStyle(el).color)),back=luminance(bg||[255,255,255]);
      return(Math.max(fg,back)+.05)/(Math.min(fg,back)+.05);
    }''')


with sync_playwright() as playwright:
    try:
        browser = playwright.chromium.launch(headless=True,
                    executable_path=os.environ.get('PW_EXECUTABLE_PATH') or None)
    except Exception as error:
        (OUT / 'browser-result.json').write_text(json.dumps({
            'status': 'blocked', 'error': str(error), 'checks': [],
            'scope': 'Chromium launch failed. Actual browser acceptance was NOT run.'}, indent=2))
        raise
    try:
        context, page = boot(browser)
        check('default independent arithmetic', metric(page, 'farmSurplus') == '720.00'
              and metric(page, 'chainLoss') == '168.00' and metric(page, 'soilResidual') == '552.00')
        check('default guard idle after initial mount', not page.evaluate('PaperAnnualBalance.isBusy()'))
        for number in range(6):
            step(page, number)
            check(f'manual stage {number+1} renders a named explanation',
                  state(page)['step'] == number and len(page.locator('.annual-stage').inner_text()) > 160)
        page.locator('[data-annual-action="reset"]').click()
        page.screenshot(path=str(OUT / 'desktop-default.png'), full_page=True)
        check('diagram labels fit and do not overlap', not figure_text_problems(page))
        page.evaluate('window.savedControl=document.querySelector("[data-annual-field=lossFraction]")')
        field(page, 'lossFraction', .1)
        check('editing preserves exact control and focus', page.evaluate('''savedControl===document.querySelector('[data-annual-field=lossFraction]')&&document.activeElement===savedControl'''))
        check('same input updates metrics, SVG, full ledger and explicit inputs',
              metric(page, 'chainLoss') == '84.00' and metric(page, 'soilResidual') == '636.00'
              and page.locator('[data-annual-diagram="soilResidual"]').text_content() == '636.00'
              and '636.00' in page.locator('.annual-all-table').text_content()
              and state(page)['inputs']['lossFraction'] == .1)
        page.locator('[data-annual-field="lossFraction"]').press('ArrowUp')
        check('number input native ArrowUp changes its value, not stage',
              state(page)['inputs']['lossFraction'] == .15 and state(page)['step'] == 0)
        page.locator('[data-annual-field="lossFraction"]').press('ArrowDown')
        field(page, 'replaceRetained', True)
        check('explicit replacement yields independently expected values',
              state(page)['result']['mineralNitrogen'] == 836 and metric(page, 'soilResidual') == '552.00'
              and metric(page, 'farmSurplus') == '636.00')
        page.screenshot(path=str(OUT / 'desktop-replacement.png'), full_page=True)
        old_result = state(page)['result']
        for bad in ['', '.11', '.25', '-.05']:
            field(page, 'lossFraction', bad)
            check(f'invalid draft {bad!r} explicitly keeps last valid result',
                  state(page)['invalid'] and state(page)['result'] == old_result
                  and '上次有效结果' in page.locator('.annual-status').inner_text()
                  and page.locator('[data-annual-download="json"]').is_disabled())
        page.screenshot(path=str(OUT / 'invalid-draft.png'), full_page=True)
        page.locator('[data-annual-action="reset"]').click()
        check('reset clears error, all controls, stage and optional replacement',
              state(page)['inputs'] == {'herd':8,'forageArea':6,'lossFraction':.2,'replaceRetained':False}
              and not state(page)['invalid'] and state(page)['step'] == 0)
        field(page, 'herd', 0)
        field(page, 'forageArea', 10)
        check('zero herd exports entire crop and marks negative soil as deficit',
              state(page)['result']['feedNitrogenExported'] == 1500
              and state(page)['result']['manureExcretedNitrogen'] == 0
              and metric(page,'soilResidual') == '-400.00'
              and '供应赤字 400.00' in page.locator('.annual-constraints').inner_text()
              and not state(page)['result']['feasible'])
        page.screenshot(path=str(OUT / 'supply-deficit.png'), full_page=True)
        field(page, 'herd', 2)
        field(page, 'forageArea', 0)
        check('exact feed cap is accepted', not state(page)['result']['flags']['feedImportExceeded'])
        field(page, 'herd', 3)
        check('over-cap feed is rejected as infeasible without hiding arithmetic',
              state(page)['result']['flags']['feedImportExceeded'] and state(page)['result']['feedImported'] == 15)
        page.locator('[data-annual-action="reset"]').click()
        page.locator('.annual-ledger summary').click()
        check('expanded full ledger blocks automatic updates', page.evaluate('PaperAnnualBalance.isBusy()'))
        page.locator('[data-annual-action="reset"]').click()
        check('reset closes full ledger and releases guard',
              not page.locator('.annual-ledger').evaluate('el=>el.open')
              and not page.evaluate('PaperAnnualBalance.isBusy()'))
        page.locator('[data-annual-field="herd"]').focus()
        check('focused default form blocks automatic updates', page.evaluate('PaperAnnualBalance.isBusy()'))
        page.locator('[data-annual-field="herd"]').press('Tab')
        check('keyboard reaches next persistent input',
              page.evaluate('document.activeElement.getAttribute("data-annual-field")') == 'forageArea')
        step(page, 5)
        page.locator('[data-annual-scenario="retain"]').click()
        check('manual retention button', state(page)['result']['soilResidual'] == 636)
        page.locator('[data-annual-scenario="replace"]').click()
        check('manual replacement button', state(page)['result']['farmSurplus'] == 636)
        page.locator('.annual-ledger summary').click()
        page.evaluate('location.hash="#/original/farmdesign-2012"')
        page.wait_for_selector('#original-destination')
        check('leaving route releases guard', not page.evaluate('PaperAnnualBalance.isBusy()'))
        page.go_back()
        page.wait_for_selector('.annual-walkthrough')
        check('native Back restores inputs, stage and expanded ledger',
              state(page)['mounted'] and state(page)['step'] == 5
              and state(page)['inputs']['replaceRetained']
              and page.locator('.annual-ledger').evaluate('el=>el.open'))
        page.go_forward()
        page.wait_for_selector('#original-destination')
        page.go_back()
        page.wait_for_selector('.annual-walkthrough')
        check('paired popstate/hashchange keeps the fresh remount alive', state(page)['mounted'])
        field(page,'forageArea','')
        page.evaluate('location.hash="#/original/farmdesign-2012"')
        page.wait_for_selector('#original-destination')
        page.go_back()
        page.wait_for_selector('.annual-walkthrough')
        check('Back also preserves invalid draft and visibly retained valid model',
              state(page)['invalid'] and page.locator('[data-annual-field="forageArea"]').input_value() == ''
              and state(page)['result']['mineralNitrogen'] == 836)
        page.evaluate('(hash)=>{location.hash=hash}', OTHER_GUIDE)
        page.wait_for_function('annualController.getState().inputs.lossFraction===.2')
        check('fresh guide entry starts with defaults', state(page)['step'] == 0 and not state(page)['invalid'])
        field(page,'lossFraction',.1)
        field(page,'replaceRetained',True)
        with TemporaryDirectory() as directory:
            downloaded = {}
            for kind in ['inputs','json','csv']:
                with page.expect_download() as event:
                    page.locator(f'[data-annual-download="{kind}"]').click()
                download = event.value
                target = Path(directory)/download.suggested_filename
                download.save_as(target)
                downloaded[kind] = target.read_text(encoding='utf-8-sig')
            check('downloaded input CSV has exactly four reproducible inputs',
                  list(csv.DictReader(io.StringIO(downloaded['inputs']))) ==
                  [{'herd':'8','forageArea':'6','lossFraction':'0.1','replaceRetained':'true'}])
            report = json.loads(downloaded['json'])
            check('downloaded JSON preserves full model and source caveats',
                  report['result']['mineralNitrogen']==836 and report['result']['farmSurplus']==636
                  and report['kind']=='original-synthetic-teaching-model' and len(report['caveats'])==4)
            rows = list(csv.DictReader(io.StringIO(downloaded['csv'])))
            surplus = next(row for row in rows if row['key']=='farmSurplus')
            check('full CSV is a distinct long ledger with units',
                  surplus['value']=='636' and surplus['unit']=='kg N/year'
                  and rows[0]['category']=='input')
        page.clock.run_for(1100)
        check('download URLs released after browser has consumed them', state(page)['pendingDownloads']==0)
        context.set_offline(True)
        field(page,'herd',4)
        check('loaded panel recalculates offline without network dependency',
              state(page)['result']['feedExported']==16 and state(page)['result']['farmSurplus']==258)
        context.set_offline(False)
        check('source prose, synthetic notes and all storage unchanged',
              page.locator('#original-paragraph').inner_text()=='Unchanged source sentinel.'
              and page.locator('#private-note').input_value()=='Synthetic note sentinel'
              and page.evaluate('fixtureStorage===JSON.stringify([Object.entries(localStorage),Object.entries(sessionStorage)])'))
        page.locator('[data-annual-action="reset"]').click()
        page.evaluate('dispatchEvent(new Event("beforeprint"))')
        page.emulate_media(media='print')
        check('print exposes complete ledger and lets figures fit page width',
              page.locator('.annual-all-table').is_visible()
              and page.locator('.annual-figure svg').evaluate('el=>getComputedStyle(el).minWidth')=='0px')
        page.screenshot(path=str(OUT / 'print-ledger.png'),full_page=True)
        page.pdf(path=str(OUT / 'current-ledger.pdf'),format='A4',print_background=True)
        page.emulate_media(media='screen')
        page.evaluate('dispatchEvent(new Event("afterprint"))')
        check('print cleanup restores collapsed ledger',not page.locator('.annual-ledger').evaluate('el=>el.open'))
        page.evaluate('document.querySelector("#annual-host").remove()')
        page.wait_for_function('!annualController.getState().mounted')
        check('detachment cleanup releases active panel guard',not page.evaluate('PaperAnnualBalance.isBusy()'))
        context.close()
        for scheme in ['light','dark']:
            context,page=boot(browser,color_scheme=scheme)
            for selector in ['.annual-status','.annual-boundary','.annual-scroll-hint','.annual-steps [aria-current="step"]','.annual-caveat']:
                check(f'{scheme} readable text contrast: {selector}',contrast(page,selector)>=4.5)
            check(f'{scheme} diagram labels remain separated',not figure_text_problems(page))
            check(f'{scheme} reduced-motion has no autoplay',not state(page)['pendingTimer'])
            page.screenshot(path=str(OUT / f'{scheme}-flow.png'),full_page=True)
            for width in [320,375]:
                page.set_viewport_size({'width':width,'height':900})
                for number in range(6):
                    step(page,number)
                    check(f'{scheme} {width}px stage {number+1} no page overflow',no_overflow(page))
                page.locator('.annual-chart-scroll').evaluate('el=>{el.scrollLeft=0}')
                page.locator('.annual-chart-scroll').focus()
                page.locator('.annual-chart-scroll').press('ArrowRight')
                page.clock.run_for(500)
                check(f'{scheme} {width}px chart keyboard scroll stays local',
                      page.locator('.annual-chart-scroll').evaluate('el=>el.scrollLeft>0')
                      and state(page)['step']==5 and no_overflow(page))
                page.screenshot(path=str(OUT / f'{scheme}-mobile-{width}.png'),full_page=True)
            context.close()
        context,page=boot(browser,color_scheme='dark',theme='light')
        field(page,'herd','')
        for selector in ['.annual-error','.annual-status','.annual-caveat']:
            check(f'OS dark plus host-selected light stays readable: {selector}',contrast(page,selector)>=4.5)
        check('OS preference does not override manually selected light warning background',
              page.locator('.annual-caveat').evaluate('el=>getComputedStyle(el).backgroundColor')
              in ['rgb(251, 240, 221)','rgb(255, 243, 219)'])
        page.screenshot(path=str(OUT/'os-dark-manual-light.png'),full_page=True)
        context.close()
        context,page=boot(browser,file_mode=True)
        context.set_offline(True)
        field(page,'lossFraction',.1)
        check('file protocol and offline arithmetic work without fetch',metric(page,'soilResidual')=='636.00')
        context.close()
        check('no unhandled page errors',not errors)
        check('no external or unrecognized fixture requests',not unexpected)
        (OUT / 'browser-result.json').write_text(json.dumps({
            'status':'passed','browser':browser.version,'checks':checks,'errors':errors,
            'unexpected_requests':unexpected,
            'scope':'Actual isolated Chromium UI: arithmetic propagation, native history, focus, invalid drafts, local downloads, loaded/file offline operation, print, mobile, light/dark. Parent host service-worker/private-note integration is separate.'},ensure_ascii=False,indent=2))
        print(json.dumps({'status':'passed','checks':len(checks),'report':str(OUT/'browser-result.json')}))
    except Exception as error:
        diagnostic={}
        pages=[page for context in browser.contexts for page in context.pages if not page.is_closed()]
        if pages:
            page=pages[-1]
            try:
                page.screenshot(path=str(OUT/'last-failure.png'),full_page=True)
                diagnostic=page.evaluate('({url:location.href,state:window.annualController?.getState(),width:innerWidth,scrollWidth:document.documentElement.scrollWidth})')
            except Exception as capture_error:
                diagnostic={'capture_error':str(capture_error)}
        (OUT / 'browser-result.json').write_text(json.dumps({
            'status':'failed','checks_completed':checks,'error':str(error),'page_errors':errors,
            'unexpected_requests':unexpected,'diagnostic':diagnostic,
            'scope':'Actual isolated browser acceptance; a partial run is not a pass.'},ensure_ascii=False,indent=2))
        raise
    finally:
        browser.close()

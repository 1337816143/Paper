"""Headless browser acceptance tests against the actual generated site."""
from pathlib import Path
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from functools import partial
import threading,json
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'dist/site';RES=ROOT/'test-results';RES.mkdir(exist_ok=True)
server=ThreadingHTTPServer(('127.0.0.1',8765),partial(SimpleHTTPRequestHandler,directory=str(OUT)))
threading.Thread(target=server.serve_forever,daemon=True).start()
checks=[]
with sync_playwright() as p:
    browser=p.chromium.launch()
    ctx=browser.new_context(viewport={'width':1280,'height':900},accept_downloads=True)
    page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto('http://127.0.0.1:8765/#/home');page.wait_for_selector('.hero')
    page.screenshot(path=str(RES/'desktop.png'),full_page=True)
    page.locator('a.btn[href="#/research-framework"]').click();page.wait_for_selector('.journey-map');page.goto('http://127.0.0.1:8765/#/liang-2022');page.wait_for_selector('#note')
    page.evaluate('window.scrollTo(0,850)');page.wait_for_timeout(350);before=page.evaluate('scrollY')
    # Navigate without scrolling the link into view; use a real link click event.
    page.evaluate("document.querySelector('a[href=\"#/ideal-distance\"]').click()")
    
    if page.locator('#study-term-popover').count():page.evaluate("document.querySelector('#study-term-popover a[href=\"#/ideal-distance\"]').click()")
    page.wait_for_function("location.hash==='#/ideal-distance'");page.wait_for_timeout(150);page.locator('#back').click();page.wait_for_timeout(400)
    assert abs(page.evaluate('scrollY')-before)<8,(before,page.evaluate('scrollY'))
    checks.append('cross-link back restores exact reading position')
    page.locator('#note').fill('TEST NOTE: preserved across navigation and reload')
    page.locator('#done').check();page.reload();page.wait_for_selector('#note')
    assert page.locator('#note').input_value().startswith('TEST NOTE')
    assert page.locator('#done').is_checked();checks.append('notes and completion survive reload')
    page.locator('#search').fill('MIDIP');page.locator('#search-form').evaluate('(f)=>f.requestSubmit()');page.wait_for_timeout(200)
    assert page.locator('.card').count()>1;checks.append('offline-capable full content search')
    page.evaluate("document.querySelector('a[href=\"#/lab\"]').click()")
    page.wait_for_selector('#pareto-result');assert 'A' in page.locator('#pareto-result').inner_text()
    for i,score in enumerate([1]*2+[2]*4+[3]*8+[4]*4+[5]*2):page.locator('.q-select').nth(i).select_option(str(score))
    assert '符合' in page.locator('#q-result').inner_text();checks.append('interactive Pareto and Q-sort')
    page.evaluate("document.querySelector('a[href=\"#/offline\"]').click()")
    page.wait_for_selector('#check-cache');page.evaluate('navigator.serviceWorker.ready.then(()=>true)')
    page.locator('#cache-site').click();page.wait_for_function("document.querySelector('#cache-status').textContent.includes('已完整缓存')",timeout=300000)
    checks.append('all declared offline assets present in versioned cache')
    with page.expect_download() as info:page.locator('[data-file="pareto_lab.py"]').click()
    assert info.value.suggested_filename=='pareto_lab.py';checks.append('embedded exercise download')
    ctx.set_offline(True);page.goto('http://127.0.0.1:8765/#/cheng-2025');page.wait_for_selector('#note')
    assert 'Q方法' in page.locator('.articlehead h1').inner_text();checks.append('fresh route and reload work with network disabled')
    page.reload();page.wait_for_selector('#note');assert page.locator('.reader section').count()>3
    ctx.set_offline(False)
    phone=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,device_scale_factor=2,has_touch=True)
    m=phone.new_page();m.goto('http://127.0.0.1:8765/#/liang-2022');m.wait_for_selector('.reader')
    assert m.evaluate('document.documentElement.scrollWidth <= innerWidth+1')
    m.screenshot(path=str(RES/'mobile-reading.png'),full_page=True)
    m.goto('http://127.0.0.1:8765/#/home');m.wait_for_selector('.hero');m.screenshot(path=str(RES/'mobile-home.png'),full_page=True)
    m.locator('#menu').click();assert m.locator('#sidebar').evaluate("e=>e.classList.contains('open')")
    checks.append('390px mobile layout and drawer')
    local=browser.new_page();local.goto((OUT/'downloads/Paper-Lab-offline.html').as_uri()+'#/liang-2023');local.wait_for_selector('.reader')
    assert '轮作' in local.locator('h1').inner_text();checks.append('single HTML runs from file protocol')
    assert not errors,errors
    (RES/'report.json').write_text(json.dumps({'passed':checks,'browserErrors':errors},ensure_ascii=False,indent=2),encoding='utf-8')
    browser.close()
server.shutdown();print(json.dumps({'passed':checks},ensure_ascii=False))

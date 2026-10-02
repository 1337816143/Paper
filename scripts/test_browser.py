"""Headless browser acceptance tests against the actual generated site."""
from pathlib import Path
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from functools import partial
import threading,json,math
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
    assert '支配' in page.locator('#result-1').inner_text()
    assert 'E' in page.locator('#result-0').inner_text()
    numeric=page.locator('[data-farm="0"][data-col="1"]')
    numeric.fill('')
    assert '暂不可计算' in page.locator('#pareto-result').inner_text()
    assert page.locator('#pareto-plot circle').count()==0
    assert page.locator('#result-1').inner_text()=='待计算'
    assert numeric.get_attribute('aria-invalid')=='true'
    numeric.fill('100')
    assert page.locator('#pareto-plot circle').count()==6
    for objective in page.locator('.objective').all():objective.uncheck()
    assert page.locator('#pareto-plot circle').count()==0
    page.locator('.objective[value="1"]').check()
    assert '非支配方案：C' in page.locator('#pareto-result').inner_text()
    page.locator('.objective[value="2"]').check();page.locator('.objective[value="3"]').check()
    checks.append('Pareto witnesses, invalid-input reset and objective-only maximization')
    ordinary=[[100,30,80],[80,40,100],[120,50,90],[90,20,70],[100,30,80],[110,35,120]]
    projection_cases=[
        [[1e308,1e308,80],[-1e308,-1e308,100],[1e308,-1e308,90],[-1e308,1e308,70],[0,0,80],[5e307,-5e307,120]],
        [[1.7976931348623157e308,1.7976931348623157e308,80],[-1.7976931348623157e308,-1.7976931348623157e308,100],[0,0,90],[1e308,-1e308,70],[-1e308,1e308,80],[1.7976931348623155e308,-1.7976931348623155e308,120]],
        [[5e-324,5e-324,80],[-5e-324,-5e-324,100],[1e-323,-1e-323,90],[-1e-323,1e-323,70],[0,0,80],[5e-324,0,120]],
        [[1e308,-1e308,row[2]] for row in ordinary],
    ]
    for rows in projection_cases:
        for i,row in enumerate(rows):
            for j,value in enumerate(row,1):page.locator(f'[data-farm="{i}"][data-col="{j}"]').fill(str(value))
        points=page.locator('#pareto-plot circle').evaluate_all('(els)=>els.map(e=>[Number(e.getAttribute("cx")),Number(e.getAttribute("cy"))])')
        assert len(points)==6 and all(math.isfinite(x) and math.isfinite(y) and 55<=x<=575 and 50<=y<=245 for x,y in points),points
        expected=[not any(j!=i and all(s[k]>=r[k] if k==0 else s[k]<=r[k] for k in range(3)) and any(s[k]>r[k] if k==0 else s[k]<r[k] for k in range(3)) for j,s in enumerate(rows)) for i,r in enumerate(rows)]
        assert [page.locator(f'#result-{i}').inner_text().startswith('非支配') for i in range(6)]==expected
        assert [[float(page.locator(f'[data-farm="{i}"][data-col="{j}"]').input_value()) for j in range(1,4)] for i in range(6)]==rows
    page.screenshot(path=str(RES/'pareto-finite-extremes.png'),full_page=False)
    for i,row in enumerate(ordinary):
        for j,value in enumerate(row,1):page.locator(f'[data-farm="{i}"][data-col="{j}"]').fill(str(value))
    checks.append('Finite extreme, near-maximum, subnormal and constant projections stay bounded without altering inputs or dominance')
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

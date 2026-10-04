#!/usr/bin/env python3
"""Integrated Paper route, update safety, note preservation and offline walkthrough."""
from pathlib import Path
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
import json,threading
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'dist/site';RES=ROOT/'test-results';RES.mkdir(exist_ok=True)
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*a):pass
srv=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(OUT)));threading.Thread(target=srv.serve_forever,daemon=True).start();BASE=f'http://127.0.0.1:{srv.server_port}/'
checks=[];errors=[];report={}
def check(name,ok):
 assert ok,name
 checks.append(name)
try:
 with sync_playwright() as pw:
  b=pw.chromium.launch();ctx=b.new_context(viewport={'width':1440,'height':1000});p=ctx.new_page();p.on('pageerror',lambda e:errors.append(str(e)));p.clock.install()
  p.goto(BASE+'#/liang-2022/research-walkthrough');p.wait_for_selector('#research-walkthrough .paper-walkthrough');panel=p.locator('.paper-walkthrough')
  check('Paper article offers direct walkthrough entry',p.locator('.articletools a[href="#/liang-2022/research-walkthrough"]').count()==1)
  check('Visual panel does not insert lesson paragraphs or glossary spans',panel.locator('.prose,[data-block],[data-study-term]').count()==0)
  old=p.locator('#s0 > .prose').text_content();ids=p.locator('#s0 [data-block]').evaluate_all('(xs)=>xs.map(x=>x.id)')
  check('Default walkthrough does not autoplay or block updates',not p.evaluate('PaperWalkthrough.isBusy()'))
  panel.locator('[data-field="costAW"]').fill('1100');panel.locator('[data-step="2"]').click()
  check('Changing the raw cost changes downstream calculated result','1,800' in panel.locator('.rw-stage').inner_text())
  p.clock.fast_forward(13000);safe=p.evaluate('PaperRelease.safeToReload()');check('Paused edited example defers automatic updates',not safe['ready'] and '研究演示' in safe['reason'])
  panel.locator('[data-action="reset"]').click();check('Reset clears walkthrough update guard',not p.evaluate('PaperWalkthrough.isBusy()'))
  panel.locator('[data-step="4"]').click();p.clock.fast_forward(13000);safe=p.evaluate('PaperRelease.safeToReload()');check('Reading an advanced unedited step also defers updates',not safe['ready'] and '研究演示' in safe['reason'])
  check('Default feasible front is visibly A and C','F1={A, C}' in panel.inner_text() or 'F1={A,C}' in panel.inner_text())
  check('The main chart retains semantic SVG text and numerical table',panel.locator('.rw-plot svg[role="img"]').count()==1 and panel.locator('.rw-plot svg title').count()==1 and panel.locator('.rw-stage table').count()>0)
  panel.locator('.rw-plot').screenshot(path=str(RES/'walkthrough-integrated-chart.png'))
  check('Tool use retains original paragraph text and IDs',p.locator('#s0 > .prose').text_content()==old and p.locator('#s0 [data-block]').evaluate_all('(xs)=>xs.map(x=>x.id)')==ids)
  p.locator('#note').fill('SYNTHETIC original research note remains unchanged');p.locator('#note').evaluate('(e)=>e.blur()');p.clock.fast_forward(1000)
  for width in [390,320]:
   p.set_viewport_size({'width':width,'height':844});panel.locator('[data-step="5"]').click();check(f'{width}px integrated walkthrough has no page overflow',p.evaluate('document.documentElement.scrollWidth<=innerWidth+2'))
   panel.locator('.rw-stage').screenshot(path=str(RES/f'walkthrough-integrated-{width}.png'))
  p.goto(BASE+'#/liang-2023');p.wait_for_selector('[data-context-note="liang23-eleven"]');check('Navigating away cleans up walkthrough busy state',not p.evaluate('PaperWalkthrough.isBusy()'))
  p.goto(BASE+'#/liang-2022/research-walkthrough');p.wait_for_selector('.paper-walkthrough');check('Existing note survives tool navigation',p.locator('#note').input_value()=='SYNTHETIC original research note remains unchanged')
  p.evaluate('navigator.serviceWorker.ready.then(()=>true)');p.wait_for_function('!!navigator.serviceWorker.controller',timeout=60000);ctx.set_offline(True);p.reload();p.wait_for_selector('.paper-walkthrough');p.locator('.paper-walkthrough [data-step="4"]').click();check('Interactive calculation and chart work offline',p.locator('.rw-plot svg').count()==1);ctx.set_offline(False)
  single=b.new_page();single.goto((OUT/'downloads/Paper-Lab-offline.html').as_uri()+'#/liang-2022/research-walkthrough');single.wait_for_selector('.paper-walkthrough');single.locator('.paper-walkthrough [data-step="5"]').click();check('Standalone HTML embeds the working visual module',single.locator('.rw-plot svg').count()==1)
  check('No uncaught integrated application errors',not errors);b.close()
 report={'passed':True,'checks':checks,'errors':errors,'scope':'Synthetic local inputs and note; no real account or private-note restoration claim'}
except Exception as e:
 report={'passed':False,'checks':checks,'errors':errors,'error':str(e)}
 raise
finally:
 (RES/'walkthrough-integration-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));srv.shutdown()
print(json.dumps({'passed':True,'checks':len(checks)}))

#!/usr/bin/env python3
"""Actual built-site acceptance; synthetic notes only, never private-user restoration."""
from pathlib import Path
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
import re
import threading
from playwright.sync_api import sync_playwright
from browser_idle import observe_activity, after_reading_idle, release_snapshot

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'dist/site';RES=ROOT/'test-results';RES.mkdir(exist_ok=True)
BASELINE=json.loads((ROOT/'tests/annual-balance/source-baseline.json').read_text())
spec=importlib.util.spec_from_file_location('annual_balance',ROOT/'examples/annual_balance.py')
MODEL=importlib.util.module_from_spec(spec);spec.loader.exec_module(MODEL)
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
srv=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(OUT)))
threading.Thread(target=srv.serve_forever,daemon=True).start();BASE=f'http://127.0.0.1:{srv.server_port}/'
checks=[];errors=[];report={};pw=None;browser=None;page=None
def check(name,ok):
 assert ok,name
 checks.append(name)
def go(id):
 page.goto(BASE+'#/'+id);page.wait_for_selector('#note');page.clock.run_for(250)
def expected_blocks(id):
 old=next(x for x in json.loads((ROOT/BASELINE['documents'][id]['file']).read_text()) if x['id']==id)
 rules=json.loads((ROOT/'resources/research-presentation.json').read_text());parts=[]
 for section in old['sections']:
  text=section[2]
  if section[1]=='教学代码':parts.append(text);continue
  for before,after in sorted(rules.items(),key=lambda x:-len(x[0])):text=text.replace(before,after)
  parts.extend(re.sub(r'\[\[[a-z0-9-]+\|([^\]]+)\]\]',r'\1',text).split('\n\n'))
 return {'lesson-block-'+str(i):text for i,text in enumerate(parts)}
def blocks():
 return page.locator('.prose [data-block]').evaluate_all('(xs)=>Object.fromEntries(xs.map(x=>[x.id,x.textContent]))')
try:
 pw=sync_playwright().start();browser=pw.chromium.launch()
 context=browser.new_context(viewport={'width':1440,'height':1000},accept_downloads=True)
 page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)));page.clock.install();observe_activity(page)
 for id in ['farmdesign-2012','qu-2025','whole-farm','nutrients','ledger-farmdesign-2012','ledger-qu-2025']:
  go(id);check(id+' retains old paragraphs and block IDs',blocks()==expected_blocks(id))
  check(id+' links to the new annual tool outside prose',page.locator('.articletools a[href="#/farmdesign-2012-balance-walkthrough/annual-balance"]').count()==1)
 go('farmdesign-2012');note='SYNTHETIC pre-5.5.7 annual-reading note; no real user data'
 page.locator('#note').fill(note);page.locator('#note').evaluate('(e)=>e.blur()');page.clock.run_for(250)
 quote=expected_blocks('farmdesign-2012')['lesson-block-0'][:32]
 annotation={'id':'synthetic-pre557-annual','docId':'lesson:farmdesign-2012','type':'highlight','title':'SYNTHETIC old source quote','comment':'Compatibility fixture','tags':[],'links':[],'color':'yellow','quote':quote,'segments':[{'block':'lesson-block-0','start':0,'end':len(quote),'quote':quote,'prefix':'','suffix':''}]}
 page.evaluate('(v)=>PaperReader.put("annotations",v)',annotation);page.reload();page.wait_for_selector('mark[data-annotation="synthetic-pre557-annual"]')
 check('Existing original lesson highlight resolves exactly',''.join(page.locator('mark[data-annotation="synthetic-pre557-annual"]').all_text_contents())==quote)
 page.locator('.articletools a[href="#/farmdesign-2012-balance-walkthrough/annual-balance"]').click();page.wait_for_selector('.annual-walkthrough')
 panel=page.locator('.annual-walkthrough')
 check('One isolated annual panel mounts in canonical FarmDESIGN guide',panel.count()==1 and page.locator('.articlehead a[href="#/original/farmdesign-2012"]').count()==1 and panel.locator('.prose,[data-block],.term-word').count()==0)
 check('Default farm surplus is720 and starts without a busy guard',panel.locator('[data-annual-value="farmSurplus"]').inner_text()=='720.00' and not page.evaluate('PaperAnnualBalance.isBusy()'))
 panel.locator('[data-annual-field="lossFraction"]').fill('0.1')
 check('Changing retention recalculates diagram and residual',panel.locator('[data-annual-value="chainLoss"]').inner_text()=='84.00' and panel.locator('[data-annual-diagram="soilResidual"]').text_content()=='636.00')
 panel.locator('[data-annual-field="replaceRetained"]').check()
 check('Explicit replacement changes external inputs and surplus',panel.locator('[data-annual-value="farmSurplus"]').inner_text()=='636.00' and panel.locator('[data-annual-diagram="mineralNitrogen"]').text_content()=='836.00')
 panel.locator('[data-annual-stage="4"]').click();safe=after_reading_idle(page)
 check('Advanced reading blocks release for the annual-tool reason',not safe['ready'] and '年度收支演示' in safe['reason'])
 panel.locator('[data-annual-field="herd"]').fill('')
 check('Blank input is visible error and keeps last-valid result',panel.locator('.annual-error').is_visible() and '上次有效' in panel.locator('.annual-status').inner_text() and panel.locator('[data-annual-value="farmSurplus"]').inner_text()=='636.00' and panel.locator('[data-annual-download="inputs"]').is_disabled())
 panel.locator('[data-annual-action="reset"]').click();check('Reset clears errors and update guard',not panel.locator('.annual-error').is_visible() and not page.evaluate('PaperAnnualBalance.isBusy()'))
 panel.locator('[data-annual-field="herd"]').fill('4');panel.locator('.annual-ledger summary').click()
 with page.expect_download() as info:panel.locator('[data-annual-download="inputs"]').click()
 current_input=MODEL.read_input(info.value.path());check('Actual downloaded input CSV runs through Python unchanged',current_input=={**MODEL.DEFAULTS,'herd':4} and MODEL.calculate(current_input)['farmSurplus']==300)
 with page.expect_download() as info:panel.locator('[data-annual-download="json"]').click()
 downloaded=json.loads(Path(info.value.path()).read_text());computed=MODEL.calculate(downloaded['inputs'])
 check('Downloaded full result equals independent Python raw values',all(abs(downloaded['result'][key]-value)<1e-9 if type(value) in (int,float) else downloaded['result'][key]==value for key,value in computed.items()))
 for width in [390,320]:
  page.set_viewport_size({'width':width,'height':844});check(str(width)+'px no whole-page overflow',page.evaluate('document.documentElement.scrollWidth<=innerWidth+2'))
  check(str(width)+'px has a labelled internal plot scroller',panel.locator('.annual-chart-scroll').evaluate('(e)=>e.scrollWidth>e.clientWidth') and '左右滚动' in panel.locator('.annual-scroll-hint').inner_text())
  panel.screenshot(path=str(RES/f'annual-integrated-{width}.png'))
 page.set_viewport_size({'width':1440,'height':1000});go('qu-2025-chain-walkthrough/annual-balance');page.wait_for_selector('.annual-walkthrough')
 panel.locator('[data-annual-field="herd"]').fill('4');panel.locator('[data-annual-stage="4"]').click();panel.locator('.annual-ledger summary').click()
 original=page.locator('.articlehead a[href="#/original/qu-2025"]');original.scroll_into_view_if_needed();page.clock.run_for(300);position=page.evaluate('scrollY');original.click();page.wait_for_selector('#original-text');page.clock.run_for(300)
 check('Original source entry leaves clean tool lifecycle',not page.evaluate('PaperAnnualBalance.isBusy()'))
 page.go_back();page.wait_for_selector('.annual-walkthrough');page.clock.run_for(300)
 check('Back from original preserves inputs stage ledger and scroll',panel.locator('[data-annual-field="herd"]').input_value()=='4' and panel.locator('[data-annual-stage="4"]').get_attribute('aria-current')=='step' and panel.locator('.annual-ledger').evaluate('(e)=>e.open') and abs(page.evaluate('scrollY')-position)<=3)
 page.screenshot(path=str(RES/'annual-original-return.png'))
 page.go_forward();page.wait_for_selector('#original-text');page.go_back();page.wait_for_selector('.annual-walkthrough');page.clock.run_for(300)
 panel.locator('[data-annual-field="herd"]').fill('0');check('Repeated history still recomputes negative supply deficit',panel.locator('[data-annual-value="soilResidual"]').inner_text()=='-120.00' and '供应赤字' in panel.locator('.annual-constraints').inner_text())
 go('farmdesign-2012');page.wait_for_selector('mark[data-annotation="synthetic-pre557-annual"]')
 check('Old note and quotation survive the complete new flow',page.locator('#note').input_value()==note and blocks()==expected_blocks('farmdesign-2012') and ''.join(page.locator('mark[data-annotation="synthetic-pre557-annual"]').all_text_contents())==quote)
 go('farmdesign-2012-balance-walkthrough');page.wait_for_selector('.annual-walkthrough')
 page.reload();page.wait_for_selector('.annual-walkthrough')
 panel.locator('[data-annual-field="herd"]').fill('12')
 panel.locator('.annual-footnote a[href="#/qu-2025-chain-walkthrough"]').click();page.wait_for_selector('.annual-walkthrough')
 panel.locator('.annual-footnote a[href="#/farmdesign-2012-balance-walkthrough"]').click();page.wait_for_selector('.annual-walkthrough')
 panel.locator('[data-annual-field="herd"]').fill('4');page.reload();page.wait_for_selector('.annual-walkthrough')
 check('Reload explicitly starts with default configuration',panel.locator('[data-annual-field="herd"]').input_value()=='8')
 panel.locator('[data-annual-field="herd"]').fill('4')
 page.go_back();page.wait_for_url('**/#/qu-2025-chain-walkthrough');page.wait_for_selector('.annual-walkthrough')
 page.go_back();page.wait_for_url('**/#/farmdesign-2012-balance-walkthrough');page.wait_for_selector('.annual-walkthrough')
 check('Old same-route history entry cannot adopt a different post-reload configuration',panel.locator('[data-annual-field="herd"]').input_value()=='8')
 go('farmdesign-2012-balance-walkthrough/annual-balance');page.wait_for_selector('.annual-walkthrough')
 page.evaluate('navigator.serviceWorker.ready.then(()=>true)');page.wait_for_function('!!navigator.serviceWorker.controller',timeout=60000);context.set_offline(True);page.reload();page.wait_for_selector('.annual-walkthrough')
 panel.locator('[data-annual-field="lossFraction"]').fill('0.1');check('Installed offline core recomputes the same annual ledger',panel.locator('[data-annual-value="soilResidual"]').inner_text()=='636.00');context.set_offline(False)
 single=browser.new_page();single.goto((OUT/'downloads/Paper-Lab-offline.html').as_uri()+'#/qu-2025-chain-walkthrough/annual-balance');single.wait_for_selector('.annual-walkthrough')
 single.locator('[data-annual-stage="5"]').click();single.locator('[data-annual-scenario="replace"]').click()
 check('Standalone HTML embeds and recalculates the complete model',single.locator('[data-annual-value="farmSurplus"]').inner_text()=='636.00' and single.locator('.annual-chart-scroll svg').count()==1)
 check('No uncaught application errors',not errors)
 report={'passed':True,'checks':checks,'errors':errors,'scope':'Actual built-site integration and synthetic old-note fixtures; no real-user private records inspected'}
except Exception as error:
 report={'passed':False,'checks':checks,'errors':errors,'error':str(error)}
 if page:
  try:page.screenshot(path=str(RES/'annual-integration-failure.png'));report['releaseState']=release_snapshot(page);report['url']=page.url
  except Exception as diagnostic:report['diagnosticError']=str(diagnostic)
 raise
finally:
 (RES/'annual-integration-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
 if browser and browser.is_connected():browser.close()
 if pw:pw.stop()
 srv.shutdown()
print(json.dumps({'passed':True,'checks':len(checks)}))

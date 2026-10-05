#!/usr/bin/env python3
"""Actual host integration, source anchors, synthetic notes, downloads and offline Q tool."""
from pathlib import Path
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
import hashlib,json,re,threading
from playwright.sync_api import sync_playwright
from browser_idle import observe_activity,after_reading_idle,release_snapshot
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'dist/site';RES=ROOT/'test-results';RES.mkdir(exist_ok=True)
CONFIG=json.loads((ROOT/'resources/q-walkthrough-v556.json').read_text())
RESULTS={x['id']:x['result'] for x in json.loads((ROOT/'resources/q-results-v556.json').read_text())['scenarios']}
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
srv=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(OUT)));threading.Thread(target=srv.serve_forever,daemon=True).start();BASE=f'http://127.0.0.1:{srv.server_port}/'
checks=[];errors=[];report={};pw=None;b=None;p=None
def check(name,ok):
 assert ok,name
 checks.append(name)
def go(id):
 p.goto(BASE+'#/'+id);p.wait_for_selector('#note');p.wait_for_timeout(180)
def expected_blocks(id):
 old=json.loads((ROOT/'tests/q/source-baseline.json').read_text())[id];rules=json.loads((ROOT/'resources/research-presentation.json').read_text());result={};i=0
 for sec in old['sections']:
  value=sec[2]
  if sec[1]=='教学代码':parts=[value]
  else:
   for a,z in sorted(rules.items(),key=lambda x:-len(x[0])):value=value.replace(a,z)
   parts=re.sub(r'\[\[[a-z0-9-]+\|([^\]]+)\]\]',r'\1',value).split('\n\n')
  for value in parts:result['lesson-block-'+str(i)]=value;i+=1
 return result
def blocks():return p.locator('.prose [data-block]').evaluate_all('(xs)=>Object.fromEntries(xs.map(x=>[x.id,x.textContent]))')
try:
 pw=sync_playwright().start();b=pw.chromium.launch();ctx=b.new_context(viewport={'width':1440,'height':1000},accept_downloads=True);p=ctx.new_page();p.on('pageerror',lambda e:errors.append(str(e)));p.clock.install();observe_activity(p)
 for id in ['q-method','cheng-2025','ledger-cheng-2025']:
  go(id);check(id+' retains exact old paragraphs and annotation IDs',blocks()==expected_blocks(id))
  check(id+' links to the new tool outside old prose',p.locator('.articletools a[href="#/cheng-2025-q-walkthrough/q-walkthrough"]').count()==1)
  check(id+' has the dated scope clarification outside preserved paragraphs',p.locator('.q-coverage-update').count()==1 and p.locator('.prose .q-coverage-update').count()==0)
 go('q-method');synthetic='SYNTHETIC pre-5.5.6 Q reading note, no real user data'
 p.locator('#note').fill(synthetic);p.locator('#note').evaluate('(e)=>e.blur()');p.clock.run_for(250)
 quote=expected_blocks('q-method')['lesson-block-0'][:32]
 annotation={'id':'synthetic-pre556-q','docId':'lesson:q-method','type':'highlight','title':'SYNTHETIC existing Q quotation','comment':'Synthetic compatibility fixture','tags':[],'links':[],'color':'yellow','quote':quote,'segments':[{'block':'lesson-block-0','start':0,'end':len(quote),'quote':quote,'prefix':'','suffix':''}]}
 p.evaluate('(v)=>PaperReader.put("annotations",v)',annotation);p.reload();p.wait_for_selector('mark[data-annotation="synthetic-pre556-q"]')
 check('Existing Q highlight restores its exact quotation',''.join(p.locator('mark[data-annotation="synthetic-pre556-q"]').all_text_contents())==quote)
 p.locator('.articletools a[href="#/cheng-2025-q-walkthrough/q-walkthrough"]').click();p.wait_for_selector('#q-walkthrough .q-walkthrough');panel=p.locator('.q-walkthrough')
 check('New guide points to Cheng source and mounts one isolated panel',panel.count()==1 and p.locator('.articlehead a[href="#/original/cheng-2025"]').count()==1 and panel.locator('.prose,[data-block],.term-word').count()==0)
 check('Default Q view starts without autoplay or a release guard',not p.evaluate('PaperQWalkthrough.isBusy()'))
 panel.locator('[data-step="4"]').click();panel.locator('[data-field="person"]').select_option('P01');panel.locator('[data-field="statement"]').select_option('S01')
 first=panel.locator('.q-equation').first.inner_text();expected=RESULTS['baseline']['weights'][0][0]*RESULTS['baseline']['data'][0][0]
 check('Selected P01 contribution is computed from current source fixture','P01' in first and f'{expected:.6f}' in first and 'P01' in panel.locator('.q-selected-row').inner_text())
 panel.locator('[data-field="person"]').select_option('P07');second=panel.locator('.q-equation').first.inner_text()
 check('The previously inactive participant control now changes formula and highlighted row',first!=second and 'P07' in second and 'P07' in panel.locator('.q-selected-row').inner_text())
 panel.locator('[data-field="scenario"]').select_option('reverse-p03');panel.locator('[data-field="person"]').select_option('P03')
 check('Coherent reverse scenario uses negative defining weight',f"{RESULTS['reverse-p03']['weights'][2][0]:.6f}" in panel.locator('.q-equation').first.inner_text() and '负定义权重' in panel.inner_text())
 panel.locator('[data-step="2"]').click();safe=after_reading_idle(p)
 check('Advanced Q reading defers automatic updates after true idle',not safe['ready'] and 'Q方法演示' in safe['reason'])
 panel.locator('[data-field="loadingView"]').select_option('geometry');panel.locator('[data-field="angle"]').fill('45')
 check('Geometry preview keeps input focus and explicitly does not refit',panel.locator('[data-field="angle"]').evaluate('(e)=>e===document.activeElement') and 'GEOMETRY PREVIEW' in panel.locator('.q-stage').inner_text() and '下游标记' in panel.inner_text())
 panel.locator('[data-action="reset"]').click();check('Reset restores default scene and clears the update guard',not p.evaluate('PaperQWalkthrough.isBusy()') and panel.locator('[data-field="scenario"]').input_value()=='baseline')
 panel.locator('[data-step="6"]').click();panel.locator('[data-field="statement"]').select_option('S12')
 diff=RESULTS['baseline']['statement_comparisons'][11]
 check('S12 continuous difference and both thresholds are visible',all(f'{diff[k]:.6f}' in panel.locator('.q-stage').inner_text() for k in ['difference','threshold_p05','threshold_p01']))
 for width in [390,320]:
  p.set_viewport_size({'width':width,'height':844});check(f'{width}px Q difference view has no page overflow',p.evaluate('document.documentElement.scrollWidth<=innerWidth+2'))
  check(f'{width}px chart has labelled internal scrolling',panel.locator('.q-chart-scroll').evaluate('(e)=>e.scrollWidth>e.clientWidth') and '左右滚动' in panel.locator('.q-scroll-hint').first.inner_text())
  panel.screenshot(path=str(RES/f'q-integrated-{width}.png'))
 p.set_viewport_size({'width':1440,'height':1000});panel.locator('[data-step="7"]').click()
 for index in range(3):
  img=panel.locator(f'[data-source-image="{index}"]');img.scroll_into_view_if_needed();p.wait_for_function('(i)=>document.querySelector(`[data-source-image="${i}"]`)?.naturalWidth>0',arg=index)
 check('All three unchanged source figures and category meanings are rendered',panel.locator('.q-source-item').count()==3 and 'Farmer_1' in panel.inner_text() and '2.857143' in panel.inner_text() and 'Ungrouped' in panel.inner_text())
 panel.locator('.q-stage details').first.locator('summary').click()
 source_link=panel.locator(f'a[href="{CONFIG["source"]["figures"][0]["anchor"]}"]');source_link.scroll_into_view_if_needed();p.clock.run_for(300);before_source_y=p.evaluate('scrollY')
 source_link.click();p.wait_for_selector('#original-text');p.clock.run_for(300)
 check('Original figure link leaves a clean Q lifecycle',not p.evaluate('PaperQWalkthrough.isBusy()') and '#/original/cheng-2025/' in p.url)
 p.go_back();p.wait_for_selector('.q-walkthrough');p.clock.run_for(300)
 check('Returning from the original preserves stage, selected statement, expanded context and position',panel.locator('[data-step="7"]').get_attribute('aria-current')=='step' and panel.locator('[data-field="statement"]').input_value()=='S12' and panel.locator('.q-stage details').first.evaluate('(e)=>e.open') and abs(p.evaluate('scrollY')-before_source_y)<=3)
 p.screenshot(path=str(RES/'q-original-return.png'))
 panel.locator('.q-downloads summary').click()
 for name in CONFIG['downloads']:
  with p.expect_download() as info:panel.locator(f'[data-q-download="{name}"]').click()
  actual=Path(info.value.path()).read_bytes();check(name+' actual download retains every UTF-8 source byte',actual==(ROOT/'examples'/name).read_bytes())
 p.clock.run_for(1200)
 go('q-method');check('Leaving Q clears its guard and retains the old note',not p.evaluate('PaperQWalkthrough.isBusy()') and p.locator('#note').input_value()==synthetic)
 p.wait_for_selector('mark[data-annotation="synthetic-pre556-q"]');check('Existing Q quotation and paragraph IDs survive tool use',blocks()==expected_blocks('q-method') and ''.join(p.locator('mark[data-annotation="synthetic-pre556-q"]').all_text_contents())==quote)
 go('cheng-2025-q-walkthrough/q-walkthrough');p.wait_for_selector('.q-walkthrough');check('Native fragment entry retains one current-route Q controller',p.locator('.q-walkthrough').count()==1)
 p.go_back();p.wait_for_url('**/#/q-method');p.wait_for_selector('#note');check('Native Back retains original note',p.locator('#note').input_value()==synthetic)
 p.go_forward();p.wait_for_url('**/#/cheng-2025-q-walkthrough/q-walkthrough');p.wait_for_selector('.q-walkthrough');p.clock.run_for(250)
 check('Native Forward survives paired history events',p.locator('.q-walkthrough').count()==1)
 p.locator('.q-walkthrough [data-step="3"]').click();check('Returned panel still changes stage and protects reading',p.evaluate('PaperQWalkthrough.isBusy()') and '定义排序' in p.locator('.q-stage').inner_text())
 p.evaluate('navigator.serviceWorker.ready.then(()=>true)');p.wait_for_function('!!navigator.serviceWorker.controller',timeout=60000);ctx.set_offline(True);p.reload();p.wait_for_selector('.q-walkthrough');p.locator('.q-walkthrough [data-step="1"]').click()
 check('Installed offline core retains the same Q matrix and visual chain',p.locator('.q-chart-scroll svg').count()==1 and 'Pearson' in p.locator('.q-stage').inner_text());ctx.set_offline(False)
 single=b.new_page();single.goto((OUT/'downloads/Paper-Lab-offline.html').as_uri()+'#/cheng-2025-q-walkthrough/q-walkthrough');single.wait_for_selector('.q-walkthrough');single.locator('.q-walkthrough [data-step="4"]').click()
 check('Standalone HTML embeds the same contribution tool',single.locator('.q-chart-scroll svg').count()==1)
 single.locator('.q-walkthrough [data-step="7"]').click();check('Standalone discloses originals absent without losing explanations',single.locator('.q-source-item img').count()==0 and '原图未嵌入' in single.locator('.q-stage').inner_text())
 single.locator('.q-downloads summary').click()
 with single.expect_download() as info:single.locator('[data-q-download="q_synthetic.csv"]').click()
 check('Standalone CSV download preserves the pinned R input hash',hashlib.sha256(Path(info.value.path()).read_bytes()).hexdigest()==json.loads((ROOT/'tests/q/reference-manifest.json').read_text())['input']['sha256'])
 check('No uncaught application errors',not errors)
 report={'passed':True,'checks':checks,'errors':errors,'scope':'Q host integration and frozen public paragraph baseline with synthetic notes only; not actual user-vault restoration'}
except Exception as e:
 report={'passed':False,'checks':checks,'errors':errors,'error':str(e)}
 if p:
  try:p.screenshot(path=str(RES/'q-integration-last-state.png'));report['url']=p.url;report['releaseState']=release_snapshot(p)
  except Exception as diagnostic_error:report['diagnosticError']=str(diagnostic_error)
 raise
finally:
 (RES/'q-integration-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
 if b and b.is_connected():b.close()
 if pw:pw.stop()
 srv.shutdown()
print(json.dumps({'passed':True,'checks':len(checks)}))

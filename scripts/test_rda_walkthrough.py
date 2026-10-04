#!/usr/bin/env python3
"""Actual integrated RDA route, old paragraph IDs, synthetic notes and offline checks."""
from pathlib import Path
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json, re, threading
from playwright.sync_api import sync_playwright
from browser_idle import observe_activity,after_reading_idle,release_snapshot
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'dist/site'; RES=ROOT/'test-results'; RES.mkdir(exist_ok=True)
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
srv=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(OUT)))
threading.Thread(target=srv.serve_forever,daemon=True).start(); BASE=f'http://127.0.0.1:{srv.server_port}/'
checks=[];errors=[];report={};pw=None;b=None;p=None
def check(name,ok):
 assert ok,name
 checks.append(name)
def go(id):
 p.goto(BASE+'#/'+id);p.wait_for_selector('#note');p.wait_for_timeout(200)
def expected_blocks(id):
 old=json.loads((ROOT/'tests/rda/source-baseline.json').read_text())[id]
 rules=json.loads((ROOT/'resources/research-presentation.json').read_text())
 result={};i=0
 for sec in old['sections']:
  value=sec[2]
  if sec[1]=='教学代码':parts=[value]
  else:
   for a,z in sorted(rules.items(),key=lambda item:-len(item[0])):value=value.replace(a,z)
   value=re.sub(r'\[\[[a-z0-9-]+\|([^\]]+)\]\]',r'\1',value);parts=value.split('\n\n')
  for value in parts:result['lesson-block-'+str(i)]=value;i+=1
 return result
def legacy_blocks():
 return p.locator('.prose [data-block]').evaluate_all('(xs)=>Object.fromEntries(xs.map(x=>[x.id,x.textContent]))')
try:
 pw=sync_playwright().start();b=pw.chromium.launch();ctx=b.new_context(viewport={'width':1440,'height':1000});p=ctx.new_page();p.on('pageerror',lambda e:errors.append(str(e)));p.clock.install();observe_activity(p)
 for id in ['rda','cheng-2023']:
  go(id);check(id+' retains every original paragraph text and block ID',legacy_blocks()==expected_blocks(id))
  check(id+' offers the new guide outside annotated prose',p.locator('.articletools a[href="#/cheng-2023-rda-walkthrough/rda-walkthrough"]').count()==1 and p.locator('.prose .rda-walkthrough').count()==0)
 go('rda');synthetic='SYNTHETIC pre-5.5.5 RDA note: units, missing values, original figure'
 p.locator('#note').fill(synthetic);p.locator('#note').evaluate('(e)=>e.blur()');p.clock.fast_forward(1000)
 quote=expected_blocks('rda')['lesson-block-0'][:35]
 annotation={'id':'synthetic-pre555-rda','docId':'lesson:rda','type':'highlight','title':'SYNTHETIC existing RDA quotation','comment':'No real reader data','tags':[],'links':[],'color':'yellow','quote':quote,'segments':[{'block':'lesson-block-0','start':0,'end':len(quote),'quote':quote,'prefix':'','suffix':''}]}
 p.evaluate('(v)=>PaperReader.put("annotations",v)',annotation);p.reload();p.wait_for_selector('mark[data-annotation="synthetic-pre555-rda"]')
 check('Existing synthetic RDA annotation restores its exact quotation',''.join(p.locator('mark[data-annotation="synthetic-pre555-rda"]').all_text_contents())==quote)
 p.locator('.articletools a[href="#/cheng-2023-rda-walkthrough/rda-walkthrough"]').click();p.wait_for_selector('#rda-walkthrough .rda-walkthrough');panel=p.locator('.rda-walkthrough')
 check('New guide opens at the tool and retains canonical original link',p.url.endswith('/rda-walkthrough') and p.locator('.articlehead a[href="#/original/cheng-2023"]').count()==1)
 check('Tool creates no old annotation blocks or glossary terms',panel.locator('.prose,[data-block],.term-word').count()==0)
 check('Default tool has no autoplay or busy state',not p.evaluate('PaperRDA.isBusy()'))
 panel.locator('[data-step="3"]').click();idle=after_reading_idle(p)
 check('Reading later RDA stage defers automatic update',not idle['ready'] and 'RDA' in idle['reason'])
 panel.locator('[data-field="v4B"]').fill('4.25')
 check('Input change rotates actual fitted decomposition','0.907322' in panel.inner_text() and '0.435815' in panel.inner_text() and panel.locator('[data-field="v4B"]').evaluate('(e)=>e===document.activeElement'))
 panel.locator('[data-step="4"]').click();before=panel.locator('[data-variable="A"] circle').get_attribute('cx')
 panel.locator('[data-field="denominator"]').select_option('constrained')
 check('Denominator change keeps coordinates and residual accounting',panel.locator('[data-variable="A"] circle').get_attribute('cx')==before and '残差部分仍在' in panel.inner_text())
 panel.locator('[data-field="v4B"]').fill('');after_reading_idle(p)
 check('Invalid in-progress input retains last valid result and defers update','上次有效结果' in panel.locator('.rda-status').inner_text() and not p.evaluate('PaperRelease.safeToReload().ready'))
 panel.locator('[data-action="reset"]').click();check('Reset restores default state and removes update guard',not p.evaluate('PaperRDA.isBusy()') and panel.locator('[data-field="v4B"]').input_value()=='3.75')
 panel.locator('[data-step="5"]').click();panel.locator('img').scroll_into_view_if_needed();p.wait_for_function('document.querySelector(".rda-source-figure img")?.naturalWidth>0')
 check('Original figure and field-specific source boundaries are present',panel.locator('img').get_attribute('src').endswith('/p9-figure1.png') and 'Revenue' in panel.inner_text() and '21%' in panel.inner_text())
 panel.locator('.rda-source-variables summary').click();check('Fourteen predictor definitions retain mixed years',panel.locator('.rda-source-variables tbody tr').count()==14 and all(t in panel.inner_text() for t in ['2018','2020','2017','TFI','Stevia']))
 for width in [390,320]:
  p.set_viewport_size({'width':width,'height':844});check(f'{width}px original-source stage does not overflow page',p.evaluate('document.documentElement.scrollWidth<=innerWidth+2'))
  panel.locator('[data-step="4"]').click();check(f'{width}px variable chart is internally scrollable',panel.locator('.rda-chart-scroll').evaluate('(e)=>e.scrollWidth>e.clientWidth') and p.evaluate('document.documentElement.scrollWidth<=innerWidth+2'))
  panel.screenshot(path=str(RES/f'rda-integrated-{width}.png'));panel.locator('[data-step="5"]').click()
 go('rda');check('Navigation cleans up the previous tool and retains old note',not p.evaluate('PaperRDA.isBusy()') and p.locator('#note').input_value()==synthetic)
 p.wait_for_selector('mark[data-annotation="synthetic-pre555-rda"]');check('Old block text and quotation survive tool navigation',legacy_blocks()==expected_blocks('rda') and ''.join(p.locator('mark[data-annotation="synthetic-pre555-rda"]').all_text_contents())==quote)
 go('cheng-2023-rda-walkthrough/rda-walkthrough');p.wait_for_selector('.rda-walkthrough')
 check('Native fragment navigation retains exactly one newly mounted panel',p.locator('.rda-walkthrough').count()==1)
 p.go_back();p.wait_for_url('**/#/rda');p.wait_for_selector('#note');check('Native Back retains the old note and clears the departed controller',p.locator('#note').input_value()==synthetic and not p.evaluate('PaperRDA.isBusy()'))
 p.go_forward();p.wait_for_url('**/#/cheng-2023-rda-walkthrough/rda-walkthrough');p.wait_for_selector('.rda-walkthrough');p.clock.run_for(250)
 check('Native Forward survives the paired history and fragment events',p.locator('.rda-walkthrough').count()==1)
 p.locator('.rda-walkthrough [data-field="v4B"]').fill('4.25');check('Returned panel still computes and protects edited state',p.evaluate('PaperRDA.isBusy()') and '4.25' in p.locator('.rda-status').inner_text());p.locator('.rda-walkthrough [data-action="reset"]').click()
 p.evaluate('navigator.serviceWorker.ready.then(()=>true)');p.wait_for_function('!!navigator.serviceWorker.controller',timeout=60000)
 ctx.set_offline(True);p.reload();p.wait_for_selector('.rda-walkthrough');p.locator('[data-step="4"]').click();check('RDA calculation and SVG work from installed offline core',p.locator('.rda-chart-scroll svg').count()==1 and '0.272166' in p.locator('.rda-stage').inner_text());ctx.set_offline(False)
 single=b.new_page();single.goto((OUT/'downloads/Paper-Lab-offline.html').as_uri()+'#/cheng-2023-rda-walkthrough/rda-walkthrough');single.wait_for_selector('.rda-walkthrough');single.locator('[data-step="4"]').click();check('Standalone HTML embeds the live RDA model',single.locator('.rda-chart-scroll svg').count()==1)
 single.locator('[data-step="5"]').click();check('Standalone accurately discloses absent original image','原图未嵌入' in single.locator('.rda-stage').inner_text() and single.locator('.rda-stage img').count()==0)
 check('No uncaught integrated application error',not errors)
 report={'passed':True,'checks':checks,'errors':errors,'scope':'RDA integration, frozen public paragraph baseline and synthetic note only; no real private-note restoration'}
except Exception as e:
 report={'passed':False,'checks':checks,'errors':errors,'error':str(e)}
 if p:
  try:p.screenshot(path=str(RES/'rda-integration-last-state.png'));report['url']=p.url;report['releaseState']=release_snapshot(p)
  except Exception:pass
 raise
finally:
 (RES/'rda-integration-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
 if b and b.is_connected():b.close()
 if pw:pw.stop()
 srv.shutdown()
print(json.dumps({'passed':True,'checks':len(checks)}))

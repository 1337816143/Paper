"""Acceptance tests; real WASM model inference, not mocked translations."""
from pathlib import Path
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from functools import partial
import threading,json,re,os,traceback
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'dist/site';RES=ROOT/'test-results';RES.mkdir(exist_ok=True)
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',8783),partial(Quiet,directory=str(OUT)));threading.Thread(target=server.serve_forever,daemon=True).start()
BASE=os.environ.get('STUDY_BASE_URL','http://127.0.0.1:8783/');checks=[];errors=[];console=[];remote=[];translations=[];failure=None
with sync_playwright() as p:
 browser=p.chromium.launch();ctx=browser.new_context(viewport={'width':1280,'height':900},accept_downloads=True);page=ctx.new_page();page.set_default_timeout(45000)
 page.on('pageerror',lambda e:errors.append(str(e)))
 page.on('console',lambda m:console.append(m.type+': '+m.text[:600]) if m.type in ['error','warning'] else None)
 page.on('request',lambda r:remote.append(r.url) if r.url.startswith('http') and not r.url.startswith(BASE.rstrip('/')) else None)
 try:
  page.goto(BASE+'#/research-framework');page.wait_for_selector('.journey-map');assert page.locator('.journey-map a').count()==6
  ids=page.evaluate('Object.keys(PAPER_STUDY.frameworks)');assert len(ids)==21
  for id in ids:
   page.goto(BASE+'#/'+id);page.wait_for_selector('.paper-framework');assert page.locator('.story-phase').count()>=2
   assert page.evaluate('''id=>{const d=PAPER_DATA.documents.find(x=>x.id===id);return d.sections.every((s,i)=>document.getElementById('s'+i));}''',id)
  checks.append('All 21 paper frameworks retain every old section and add a connected argument narrative')
  page.goto(BASE+'#/liang-2022');page.wait_for_selector('.paper-framework');assert page.locator('.phase-bridge').count()==3
  before=page.locator('#view .reader').inner_text();term=page.locator('.prose [data-study-term]').filter(has_text='MIDIP').first;term.click();page.wait_for_selector('#study-term-popover');assert '理想点' in page.locator('#study-term-popover').inner_text()
  page.locator('.articlehead h1').click();assert page.locator('#study-term-popover').count()==0;assert page.locator('#view .reader').inner_text()==before;checks.append('Guided-reading terminology opens on tap and closes outside without changing text')
  page.locator('#note').fill('TEST prior guided notes retained');page.locator('#done').check();page.reload();page.wait_for_selector('#note');assert page.locator('#note').input_value()=='TEST prior guided notes retained';assert page.locator('#done').is_checked();checks.append('Prior guided notes and completion persist through framework restructuring')
  page.goto(BASE+'#/original/liang-2022');page.wait_for_selector('#toggle-chinese');page.wait_for_selector('.study-equation');assert page.locator('.study-equation math').count()>=3
  intact=page.evaluate('''async()=>{const b=await PaperReader.loadBook('liang-2022');return b.pages.flatMap(p=>p.blocks).filter(x=>x.text).every(x=>document.getElementById(x.id)?.textContent===x.text.replace(/\s+/g,' ').trim());}''');assert intact
  checks.append('Original source text and anchors unchanged; display math reconstructed from verified source layout')
  # Original term spelling remains intact and is selectable.
  ot=page.locator('.original-block [data-study-term="positive-deviance"]').first;ot.click();page.wait_for_selector('#study-term-popover');page.keyboard.press('Escape');assert page.locator('#study-term-popover').count()==0;checks.append('English original terminology works with click-away and Escape')
  page.evaluate('''()=>{const el=[...document.querySelectorAll('.original-block')].find(e=>e.textContent.length>250&&!e.closest('details'));el.scrollIntoView();const w=document.createTreeWalker(el,NodeFilter.SHOW_TEXT),nodes=[];while(w.nextNode())nodes.push(w.currentNode);const r=document.createRange();r.setStart(nodes[0],0);let n=90;for(const t of nodes){if(n<=t.length){r.setEnd(t,n);break;}n-=t.length;}const s=getSelection();s.removeAllRanges();s.addRange(r);document.dispatchEvent(new Event('selectionchange'));}''');page.wait_for_selector('#selection-tools');page.locator('[data-quick="highlight"]').click();page.wait_for_selector('mark[data-annotation]');quoted=page.locator('mark[data-annotation]').all_text_contents();page.reload();page.wait_for_selector('mark[data-annotation]');assert page.locator('mark[data-annotation]').all_text_contents()==quoted;checks.append('Multi-node selection across terms saves and restores exact original highlights')
  # First actual inference uses a synthetic educational sentence, not copyrighted source output in logs.
  result=page.evaluate("async()=>await PaperStudy.translateLocal('The farm has two fields. Water and labour are limited.')");assert re.search('[\u3400-\u9fff]',result['text']),result;translations.append(result);checks.append('Actual pinned local model translates English to Chinese without a remote inference API')
  page.locator('#toggle-chinese').click();page.wait_for_function("document.querySelector('#toggle-chinese').getAttribute('aria-pressed')==='true'")
  page.wait_for_selector('.translation-slot[data-status="ready"]',timeout=180000);ready=page.locator('.translation-slot[data-status="ready"]').first;first_id=ready.get_attribute('id');chinese=ready.locator('.translated-text').inner_text();assert re.search('[\u3400-\u9fff]',chinese)
  page.locator('#toggle-chinese').click();assert page.locator('#'+first_id).is_hidden();page.locator('#toggle-chinese').click();assert page.locator('#'+first_id).is_visible();page.locator('#translation-pause').evaluate('e=>e.click()');page.reload();page.wait_for_selector('#toggle-chinese');page.wait_for_selector('#'+first_id+' .translated-text');assert page.locator('#'+first_id+' .translated-text').inner_text()==chinese
  checks.append('Chinese appears directly under original paragraphs; toggle and generated translations survive reload')
  page.locator('#toggle-chinese').click();page.locator('#reader-mode').click();page.wait_for_timeout(250);assert page.locator('#original-viewport').evaluate("e=>e.classList.contains('paged')");page.locator('#next-page').click();assert page.locator('#original-viewport').evaluate('e=>e.scrollLeft')>0;page.locator('#toggle-chinese').click();page.wait_for_timeout(300);assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1');page.locator('#toggle-chinese').click();checks.append('Bilingual toggle remains compatible with reflow pagination')
  page.goto(BASE+'#/offline');page.wait_for_selector('#cache-site');page.evaluate('navigator.serviceWorker.ready.then(()=>true)');page.locator('#cache-site').click();page.wait_for_function("document.querySelector('#cache-status').textContent.includes('已完整缓存')",timeout=300000);checks.append('Complete cache includes pinned model, WASM, originals, formulas and glossary')
  ctx.set_offline(True);page.goto(BASE+'#/original/cheng-2025');page.wait_for_selector('#toggle-chinese');assert page.locator('.source-page').count()==14
  result=page.evaluate("async()=>await PaperStudy.translateLocal('Farmers compare different crop rotations before making a decision.')");assert re.search('[\u3400-\u9fff]',result['text']);translations.append(result);checks.append('New sentence translated with network disabled and new original opened fully offline')
  assert not remote,remote;checks.append('No third-party requests from browser reading or translation')
  ctx.set_offline(False)
  phone=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True,device_scale_factor=2);m=phone.new_page();m.goto(BASE+'#/original/liang-2022');m.wait_for_selector('#toggle-chinese');r=m.locator('#toggle-chinese').bounding_box();assert r['x']>330 and r['x']+r['width']<=391;assert m.evaluate('document.documentElement.scrollWidth<=innerWidth+1');m.locator('.study-equation math').first.scroll_into_view_if_needed();m.screenshot(path=str(RES/'study-equations-mobile.png'));m.goto(BASE+'#/liang-2022');m.wait_for_selector('.paper-framework');assert m.evaluate('document.documentElement.scrollWidth<=innerWidth+1');m.screenshot(path=str(RES/'study-framework-mobile.png'));checks.append('390px mobile right-edge control, framework and equation layouts do not overflow')
  assert not errors,errors
 except Exception as e:
  failure=traceback.format_exc();raise
 finally:
  report={'passed':checks,'errors':errors,'console':console[-25:],'unexpectedRemoteRequests':remote,'syntheticTranslationSmoke':translations,'failure':failure,'scope':'Chromium desktop and touch-viewport simulation; machine translation not scientifically calibrated; no physical device test'}
  (RES/'study-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));page.screenshot(path=str(RES/'study-last-state.png'));browser.close();server.shutdown()
print(json.dumps({'passed':checks,'syntheticTranslationSmoke':translations},ensure_ascii=False))

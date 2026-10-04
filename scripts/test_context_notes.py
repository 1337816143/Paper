#!/usr/bin/env python3
"""Actual desktop/mobile/keyboard/offline contextual-note acceptance, synthetic notes only."""
from pathlib import Path
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
import json,threading
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'dist/site';RES=ROOT/'test-results';RES.mkdir(exist_ok=True)
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*a):pass
srv=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(OUT)));threading.Thread(target=srv.serve_forever,daemon=True).start();BASE=f'http://127.0.0.1:{srv.server_port}/'
checks=[];errors=[];report={};pw=None;b=None;p=None
def check(name,ok):
 assert ok,name
 checks.append(name)
def go(p,id):
 p.goto(BASE+'#/'+id);p.wait_for_function('!!window.PaperContext');p.wait_for_timeout(150)
def trigger(p,id):return p.locator('[data-context-note="'+id+'"]').first
try:
 pw=sync_playwright().start()
 b=pw.chromium.launch();ctx=b.new_context(viewport={'width':1440,'height':1000});p=ctx.new_page();p.on('pageerror',lambda e:errors.append(str(e)))
 go(p,'liang-2023/s2');check('Explicit eleven-indicator phrase is contextual',p.locator('[data-context-note="liang23-eleven"]').count()==1)
 expected=next(d for d in json.loads((ROOT/'content/papers.json').read_text()) if d['id']=='liang-2023')['sections'][2][2]
 visible=p.locator('#s2 > .prose').text_content();check('Annotation buttons retain the exact paragraph text',''.join(visible.split())==''.join(expected.split()))
 check('Inline explanation does not inherit large toolbar button height',trigger(p,'liang23-gmv').evaluate('(e)=>getComputedStyle(e).minHeight')=='0px')
 before_ids=p.locator('#s2 [data-block]').evaluate_all('(xs)=>xs.map(x=>x.id)')
 trig=trigger(p,'liang23-eleven');trig.evaluate("(e)=>e.focus()");trig.press('Enter');p.wait_for_selector('#paper-context-note[open]')
 box=p.locator('#paper-context-note');check('Eleven metrics expand with scope, units and sources',box.locator('details').count()==11 and all(x in box.inner_text() for x in ['3项','5项','kg AI/ha/yr','Table2','没有报告用Delphi']))
 check('Exact original-page and deep-guide links are usable',box.locator('a[href="#/original/liang-2023/page-7"]').count()==1 and box.locator('a[href="#/liang-2023-indicator-details"]').count()==1)
 check('Dialog has accessible title and focused close control',box.get_attribute('aria-labelledby')=='context-note-title' and p.locator('.context-note-close').evaluate('(e)=>e===document.activeElement'))
 box.locator('details').nth(8).locator('summary').click();check('Source contradictions remain explicit',all(x in box.inner_text() for x in ['QSOC','标题写kg','Table2和组分定义写Mg']))
 box.locator('.context-note-close').focus();p.keyboard.press('Shift+Tab');check('Reverse Tab wraps to the final dialog link',p.locator('#paper-context-note a').last.evaluate('(e)=>e===document.activeElement'));p.keyboard.press('Tab');check('Forward Tab wraps to close control',box.locator('.context-note-close').evaluate('(e)=>e===document.activeElement'))
 for _ in range(12):p.keyboard.press('Tab');check('Keyboard focus remains in native dialog',p.evaluate('!!document.activeElement.closest("#paper-context-note")'))
 p.keyboard.press('Escape');check('Escape closes and returns focus without changing route',box.count()==0 and trig.evaluate('(e)=>e===document.activeElement') and p.url.endswith('#/liang-2023/s2'))
 for _ in range(3):
  trig.press('Space');p.wait_for_selector('#paper-context-note[open]');check('Repeated open has one dialog',p.locator('#paper-context-note').count()==1);p.locator('.context-note-close').click()
 trig.click();p.wait_for_selector('#paper-context-note[open]');p.mouse.click(2,2);check('Backdrop click closes the contextual dialog',p.locator('#paper-context-note').count()==0)
 guarded=p.evaluate('''()=>{const b=document.querySelector('[data-context-note="liang23-eleven"]'),r=document.createRange();r.selectNodeContents(b);const s=getSelection();s.removeAllRanges();s.addRange(r);b.dispatchEvent(new MouseEvent('click',{bubbles:true}));const closed=!document.querySelector('#paper-context-note');s.removeAllRanges();return closed;}''');check('Selecting text does not open a contextual dialog',guarded)
 check('Open and close preserve existing lesson block IDs',p.locator('#s2 [data-block]').evaluate_all('(xs)=>xs.map(x=>x.id)')==before_ids)
 # A synthetic pre-existing note must not receive contextual buttons or rewritten text.
 synthetic='SYNTHETIC 11个指标 / 毛利变异 / 自测笔记来自测量'
 p.locator('#note').fill(synthetic);p.locator('#note').evaluate('(e)=>e.blur()');p.wait_for_timeout(400);p.reload();p.wait_for_selector('[data-context-note="liang23-eleven"]')
 check('Private note value is untouched by contextual layer',p.locator('#note').input_value()==synthetic and p.locator('#note [data-context-note]').count()==0)
 # Select a range crossing an inline button and surrounding text, using the existing annotation UI.
 selected=p.evaluate("""()=>{const b=document.querySelector('[data-context-note="liang23-gmv"]'),el=b.closest('[data-block]'),t=el.textContent,i=t.indexOf(b.textContent),lo=Math.max(0,i-3),hi=Math.min(t.length,i+b.textContent.length+3),w=document.createTreeWalker(el,NodeFilter.SHOW_TEXT),r=document.createRange();let at=0,start=false;while(w.nextNode()){const n=w.currentNode,end=at+n.length;if(!start&&lo<end){r.setStart(n,lo-at);start=true;}if(start&&hi<=end){r.setEnd(n,hi-at);break;}at=end;}const s=getSelection();s.removeAllRanges();s.addRange(r);document.dispatchEvent(new Event('selectionchange'));return {quote:t.slice(lo,hi),block:el.id,text:t};}""")
 p.wait_for_selector('#selection-tools');p.locator('[data-quick="highlight"]').click();p.wait_for_selector('mark[data-annotation]')
 check('Selection across a contextual button retains the exact quotation',p.evaluate('(v)=>document.getElementById(v.block).textContent===v.text',selected))
 saved=p.evaluate("PaperReader.all('annotations')");check('Native annotation records preserve quotation across inline markup',any(n.get('quote')==selected['quote'] for n in saved))
 p.reload();p.wait_for_selector('[data-context-note="liang23-gmv"] mark[data-annotation]')
 check('Cross-button highlight survives reload without changing paragraph text',p.evaluate('(v)=>document.getElementById(v.block).textContent===v.text',selected))
 trigger(p,'liang23-gmv').focus();trigger(p,'liang23-gmv').press('Enter');p.wait_for_selector('#paper-context-note[open]');p.keyboard.press('Escape')
 check('Context buttons coexist with separate glossary terms',p.locator('.term-word').count()>0 and p.locator('[data-context-note] .term-word').count()==0)
 # Native touch-like and narrow layouts use a bounded scrolling dialog.
 for width,height in [(390,844),(320,568)]:
  p.set_viewport_size({'width':width,'height':height});trigger(p,'liang23-eleven').click();p.wait_for_selector('#paper-context-note[open]')
  rect=p.locator('#paper-context-note').bounding_box();check(f'{width}px dialog stays in viewport',rect['x']>=0 and rect['y']>=0 and rect['x']+rect['width']<=width+1 and rect['y']+rect['height']<=height+1)
  check(f'{width}px detailed content can scroll',p.locator('.context-note-body').evaluate('(e)=>e.scrollHeight>e.clientHeight'))
  check(f'{width}px page does not overflow',p.evaluate('document.documentElement.scrollWidth<=innerWidth+2'))
  p.screenshot(path=str(RES/f'context-notes-{width}.png'));p.locator('.context-note-close').click()
 p.set_viewport_size({'width':1440,'height':1000});p.locator('#theme').click();trigger(p,'liang23-eleven').click();p.wait_for_selector('#paper-context-note[open]');check('Dark dialog uses existing theme background',p.locator('#paper-context-note').evaluate('(e)=>getComputedStyle(e).backgroundColor!=="rgb(255, 255, 255)"'))
 p.screenshot(path=str(RES/'context-notes-desktop-dark.png'));p.locator('.context-note-close').click();p.locator('#theme').click()
 # In-dialog navigation closes cleanly; Back retains the original lesson and note.
 trigger(p,'liang23-eleven').click();p.locator('#paper-context-note a[href="#/liang-2023-indicator-details"]').click();p.wait_for_url('**/#/liang-2023-indicator-details');check('Deep guide original link resolves to the real paper',p.locator('.articlehead a[href="#/original/liang-2023"]').count()==1);check('Deep guide opens with no stale popup',p.locator('#paper-context-note').count()==0 and '11项指标' in p.locator('.articlehead h1').inner_text());p.go_back();p.wait_for_selector('[data-context-note="liang23-eleven"]');check('Back restores the previous lesson note',p.locator('#note').input_value()==synthetic)
 for page,id in [('liang-2022','liang22-seven'),('liang-2022','liang22-midip-hdip'),('cheng-2025','cheng25-grid'),('farmsteps-2026','farmsteps-vertical-horizontal')]:
  go(p,page);trigger(p,id).click();p.wait_for_selector('#paper-context-note[open]');check(id+' has its own context',p.locator('#paper-context-note').inner_text().strip()!='');p.keyboard.press('Escape')
 # Synthetic fixture uses the pre-5.5.3 public paragraph ID from commit f140045.
 legacy={'id': 'synthetic-pre553-relocation', 'docId': 'lesson:liang-indicator-audit', 'type': 'highlight', 'title': 'SYNTHETIC legacy relocation', 'comment': 'Synthetic annotation only', 'tags': [], 'links': [], 'color': 'yellow', 'quote': '因此这不是每个案例连续监测地下水位下降，也不是简单用水量本身；‘消耗’', 'segments': [{'block': 'lesson-block-15', 'start': 0, 'end': 35, 'quote': '因此这不是每个案例连续监测地下水位下降，也不是简单用水量本身；‘消耗’', 'prefix': '', 'suffix': '包含了模型估计补给。把mm换成立方米要有相应面积：1 mm作用于1 ha相当于1'}]}
 go(p,'liang-indicator-audit');p.evaluate('(v)=>PaperReader.put("annotations",v)',legacy);p.reload();p.wait_for_selector('mark[data-annotation="synthetic-pre553-relocation"]')
 check('A shifted pre-5.5.3 annotation relocates by its unique quote',''.join(p.locator('mark[data-annotation="synthetic-pre553-relocation"]').all_text_contents())==legacy['quote'] and p.locator('#s5 mark[data-annotation="synthetic-pre553-relocation"]').count()>=1)
 go(p,'original/liang-2023/page-7');p.wait_for_selector('#original-text');check('Original PDF text has no contextual rewrite',p.locator('#original-text [data-context-note]').count()==0)
 go(p,'liang-2023');p.evaluate('navigator.serviceWorker.ready.then(()=>true)');p.wait_for_function('!!navigator.serviceWorker.controller',timeout=60000);ctx.set_offline(True);p.reload();p.wait_for_selector('[data-context-note="liang23-eleven"]');trigger(p,'liang23-eleven').click();p.wait_for_selector('#paper-context-note[open]');check('Complete contextual explanation works offline','Table2' in p.locator('#paper-context-note').inner_text());ctx.set_offline(False)
 single=b.new_page();single.goto((OUT/'downloads/Paper-Lab-offline.html').as_uri()+'#/liang-2023');single.wait_for_selector('[data-context-note="liang23-eleven"]');trigger(single,'liang23-eleven').click();single.wait_for_selector('#paper-context-note[open]');check('Standalone file contains the complete inline explanation',single.locator('#paper-context-note details').count()==11)
 check('No uncaught application errors',not errors);b.close()
 report={'passed':True,'checks':checks,'errors':errors,'scope':'Controlled contextual lesson annotations; synthetic note only; no real private account restoration claim'}
except Exception as e:
 report={'passed':False,'checks':checks,'errors':errors,'error':str(e)}
 try:
  p.screenshot(path=str(RES/'context-notes-last-state.png'));report['activeElement']=p.evaluate('({tag:document.activeElement?.tagName,id:document.activeElement?.id,className:document.activeElement?.className})')
 except Exception:pass
 raise
finally:
 (RES/'context-notes-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
 if b and b.is_connected():b.close()
 if pw:pw.stop()
 srv.shutdown()
print(json.dumps({'passed':True,'checks':len(checks)}))

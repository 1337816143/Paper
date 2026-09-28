from pathlib import Path
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from functools import partial
import threading,json
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'dist/site';RES=ROOT/'test-results';RES.mkdir(exist_ok=True)
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',8771),partial(Quiet,directory=str(OUT)));threading.Thread(target=server.serve_forever,daemon=True).start();checks=[]
with sync_playwright() as p:
 browser=p.chromium.launch();c=browser.new_context(viewport={'width':1280,'height':900},accept_downloads=True);page=c.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 try:
  page.goto('http://127.0.0.1:8771/#/liang-2022');page.wait_for_selector('#note')
  page.locator('.articlehead a[href="#/original/liang-2022"]').click();page.wait_for_selector('#original-text');assert page.locator('#original-text [data-block]').count()>100;assert page.locator('.source-page').count()==15;assert page.locator('iframe,embed,object').count()==0;checks.append('Complete source text and 15 pages, not PDF viewer')
  page.screenshot(path=str(RES/'reader-desktop.png'),full_page=False)
  page.evaluate('''()=>{const el=[...document.querySelectorAll('[data-block]')].find(e=>e.textContent.length>200&&e.getBoundingClientRect().height>0);el.scrollIntoView();const w=document.createTreeWalker(el,NodeFilter.SHOW_TEXT);let t;while(w.nextNode()){if(w.currentNode.length>20){t=w.currentNode;break;}}if(!t)throw Error('No selectable text');const r=document.createRange();r.setStart(t,0);r.setEnd(t,Math.min(80,t.length));const s=getSelection();s.removeAllRanges();s.addRange(r);document.dispatchEvent(new Event('selectionchange'));}''');page.wait_for_selector('#selection-tools');page.locator('[data-quick="highlight"]').click();page.wait_for_selector('mark[data-annotation]');page.reload();page.wait_for_selector('mark[data-annotation]');checks.append('Native selection highlight survives reload')
  page.locator('mark[data-annotation]').first.click();page.wait_for_selector('#note-editor');page.locator('[name="title"]').fill('TEST source note');page.locator('[name="comment"]').fill('TEST original evidence note');page.locator('#note-form button[type="submit"]').click();page.wait_for_timeout(200)
  page.evaluate("document.querySelector('a[href=\"#/annotations\"]').click()");page.wait_for_selector('.annotation-card');assert 'TEST original evidence note' in page.locator('.annotation-card').inner_text()
  with page.expect_download() as dl:page.locator('#export-annotations').click()
  assert dl.value.suggested_filename.endswith('.json');checks.append('Central notes search and JSON export')
  page.locator('#new-note').click();page.locator('[name="title"]').fill('TEST linked note');page.locator('[name="comment"]').fill('TEST backlink body');first=page.locator('[name="links"] option').first.get_attribute('value');page.locator('[name="links"]').select_option(first);page.locator('#note-form button[type="submit"]').click();page.wait_for_timeout(250);assert '被引用' in page.locator('#annotation-list').inner_text();checks.append('Linked notes and reciprocal backlinks')
  page.locator('.annotation-card a').filter(has_text='跳回原文位置').first.click();page.wait_for_selector('#original-text');page.wait_for_selector('.jump-focus');checks.append('Note returns to exact source paragraph')
  page.locator('#reader-mode').click();page.wait_for_timeout(500);assert page.locator('#original-viewport').evaluate('e=>e.classList.contains("paged")');page.locator('#next-page').click();page.wait_for_timeout(100);assert page.locator('#original-viewport').evaluate('e=>e.scrollLeft')>0;checks.append('Reflow paginated mode and navigation');page.screenshot(path=str(RES/'reader-paged.png'),full_page=False)
  page.locator('#reader-mode').click();page.locator('#original-query').fill('References');page.locator('#original-search').evaluate('e=>e.requestSubmit()');assert '/' in page.locator('#original-match').inner_text();checks.append('Full original search includes references')
  with page.expect_download() as dl:page.locator('#original-download').click()
  assert dl.value.suggested_filename.endswith('.pdf');checks.append('Exact source PDF available to external readers')
  page.goto('http://127.0.0.1:8771/#/offline');page.wait_for_selector('#cache-site');page.evaluate('navigator.serviceWorker.ready.then(()=>true)');page.locator('#cache-site').click();page.wait_for_function("document.querySelector('#cache-status').textContent.includes('已完整缓存')",timeout=300000);checks.append('Complete cache covers originals, graphics and parser')
  c.set_offline(True);page.goto('http://127.0.0.1:8771/#/original/liang-2023');page.wait_for_selector('#original-text');assert page.locator('.source-page').count()==13;image=page.locator('.source-figure img').first;image.scroll_into_view_if_needed();page.wait_for_function("document.querySelector('.source-figure img').naturalWidth>0")
  with page.expect_download() as dl:page.locator('#original-download').click()
  assert dl.value.suggested_filename.endswith('.pdf');checks.append('Never-opened original, figure and PDF work after network disabled');c.set_offline(False)
  # Native local PDF import uses vendored parser offline, not a server upload.
  page.goto('http://127.0.0.1:8771/#/resources');page.wait_for_selector('#import-original');page.on('dialog',lambda d:d.accept())
  with page.expect_file_chooser() as fc:page.locator('#import-original').click()
  source=next((ROOT/'resources/library/liang-2022').glob('*/source.pdf'));fc.value.set_files(str(source));page.wait_for_selector('#original-text',timeout=120000);assert page.locator('.source-page').count()==15;checks.append('Personal PDF import, complete text and per-page fidelity images')
  phone=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True,device_scale_factor=2);m=phone.new_page();m.goto('http://127.0.0.1:8771/#/original/liang-2022');m.wait_for_selector('#original-text');assert m.evaluate('document.documentElement.scrollWidth<=innerWidth+1');m.evaluate("document.querySelectorAll('[data-block]')[6].scrollIntoView()");m.screenshot(path=str(RES/'reader-mobile.png'),full_page=False);m.locator('#reader-mode').click();m.wait_for_timeout(300);assert m.evaluate('document.documentElement.scrollWidth<=innerWidth+1');checks.append('390px touch viewport no horizontal page overflow')
  assert not errors,errors
 finally:
  (RES/'reader-report.json').write_text(json.dumps({'passed':checks,'errors':errors,'scope':'Chromium desktop and mobile simulation, not physical devices'},ensure_ascii=False,indent=2));page.screenshot(path=str(RES/'reader-last-state.png'),full_page=False);browser.close();server.shutdown()
print(json.dumps(checks,ensure_ascii=False))

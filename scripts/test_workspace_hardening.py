from pathlib import Path
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from functools import partial
import threading,json,traceback
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'dist/site';RES=ROOT/'test-results';RES.mkdir(exist_ok=True)
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',8785),partial(Quiet,directory=str(OUT)));threading.Thread(target=server.serve_forever,daemon=True).start();BASE='http://127.0.0.1:8785/';checks=[];errors=[];failure=None
with sync_playwright() as p:
 b=p.chromium.launch();c=b.new_context();page=c.new_page();page.set_default_timeout(30000);page.on('pageerror',lambda e:errors.append(str(e)))
 try:
  page.goto(BASE+'#/discover');page.wait_for_selector('#literature-query')
  id=page.evaluate("async()=>(await PaperWorkspace.ingest(new File(['Methods\\n\\nSoil water balance (SWB) describes a synthetic water accounting example.\\n\\nWe compare SWB under two teaching scenarios.'],'source-acronym.txt'))).book.id")
  page.goto(BASE+'#/original/'+id);page.wait_for_selector('[data-study-term^="sourceabbr-"]');term=page.locator('[data-study-term^="sourceabbr-"]').filter(has_text='SWB').first;term.click();page.wait_for_selector('#study-term-popover');assert 'Soil water balance' in page.locator('#study-term-popover').inner_text();assert '核对原文定义位置' in page.locator('#study-term-popover').inner_text();page.keyboard.press('Escape')
  checks.append('Author-defined acronym has source-specific expansion and original-block evidence link')
  other=page.evaluate("async()=>(await PaperWorkspace.ingest(new File(['SWB has no expansion in this separate document.'],'different-context.txt'))).book.id")
  page.goto(BASE+'#/original/'+other);page.wait_for_selector('#original-text');assert page.locator('[data-study-term^="sourceabbr-"]').count()==0;assert not page.evaluate("PaperStudy.matchTerms('SWB').some(t=>t.id.startsWith('sourceabbr-'))")
  checks.append('Derived acronym meaning is cleared when leaving its source document')
  page.evaluate('async id=>await PaperWorkspace.put("workbooks",{id,values:{question:"Original local interpretation"}})',id)
  page.goto(BASE+'#/discover');page.wait_for_selector('#workspace-backup');payload=json.dumps({'schema':'paper.workspace.backup.v4','references':[],'workbooks':[{'id':id,'values':{'question':'Different imported interpretation','method':'Imported method note'}}],'terms':[]})
  with page.expect_file_chooser() as fc:page.locator('#workspace-backup').click()
  fc.value.set_files({'name':'synthetic-backup.json','mimeType':'application/json','buffer':payload.encode()});page.wait_for_selector('#my-reference-list');saved=page.evaluate('async id=>await PaperWorkspace.get("workbooks",id)',id);assert 'Original local interpretation' in saved['values']['question'] and 'Different imported interpretation' in saved['values']['question'];assert saved['values']['method']=='Imported method note'
  page.goto(BASE+'#/workbook/'+id);page.wait_for_selector('[data-workbook="question"]');assert 'Different imported interpretation' in page.locator('[data-workbook="question"]').input_value();checks.append('Conflicting workbook fields stay attached to the paper and retain both versions')
  page.goto(BASE+'#/original/liang-2022');page.wait_for_selector('#view-page-images');page.locator('#view-page-images').click();assert page.locator('#toggle-chinese').is_disabled();page.locator('#view-page-images').click();assert not page.locator('#toggle-chinese').is_disabled();checks.append('Original-image verification mode clearly disables text-only translation and pagination controls')
  page.goto(BASE+'#/liang-2022');page.wait_for_selector('.connected-walkthrough [data-study-term="midip"]')
  source_text=page.evaluate("PAPER_STUDY.frameworks['liang-2022'].walkthrough.paragraphs")
  visible_text=page.locator('.connected-walkthrough > p').all_text_contents();assert visible_text==source_text
  page.locator('.connected-walkthrough [data-study-term="midip"]').first.click();page.wait_for_selector('.term-example');assert '0.5' in page.locator('.term-example').inner_text();page.keyboard.press('Escape')
  checks.append('New connected walkthroughs expose the same beginner glossary without changing their source text')
  page.goto(BASE+'#/workbook');page.wait_for_selector('#my-reference-list');checks.append('Generic workbook entry leads to the paper selector rather than an empty document')
  assert not errors,errors
 except Exception:failure=traceback.format_exc();raise
 finally:
  (RES/'workspace-hardening-report.json').write_text(json.dumps({'passed':checks,'browserErrors':errors,'failure':failure},ensure_ascii=False,indent=2));b.close();server.shutdown()
print(json.dumps(checks,ensure_ascii=False))

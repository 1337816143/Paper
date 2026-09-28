"""Workspace acceptance: real public API queries plus separate simulated failure tests."""
from pathlib import Path
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from functools import partial
import threading,json,traceback,base64
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'dist/site';RES=ROOT/'test-results';RES.mkdir(exist_ok=True)
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',8784),partial(Quiet,directory=str(OUT)));threading.Thread(target=server.serve_forever,daemon=True).start();BASE='http://127.0.0.1:8784/'
checks=[];api_results={};errors=[];failure=None
with sync_playwright() as p:
 browser=p.chromium.launch();ctx=browser.new_context(viewport={'width':1280,'height':900},accept_downloads=True);page=ctx.new_page();page.set_default_timeout(45000);page.on('pageerror',lambda e:errors.append(str(e)))
 try:
  page.goto(BASE+'#/discover');page.wait_for_selector('#literature-query');assert page.locator('#paper-drop').count()==1
  assert page.evaluate("PaperWorkspace.doi('https://doi.org/10.1016/J.AGSY.2022.103471')")=='10.1016/j.agsy.2022.103471'
  assert page.evaluate("PaperWorkspace.doi('DOI: 10.1000/foo(bar)')")=='10.1000/foo(bar)'
  assert page.evaluate("['http://test.org/a','https://user:pass@example.com/a','https://127.0.0.1/a','https://192.168.1.1/a','javascript:alert(1)'].every(x=>!PaperWorkspace.safeURL(x))")
  checks.append('DOI normalization and unsafe network URL rejection')
  page.locator('#literature-query').fill('10.1016/j.agsy.2022.103471');page.locator('#literature-search').evaluate('e=>e.requestSubmit()');page.wait_for_selector('[data-save-ref]')
  assert 'Identifying exemplary' in page.locator('#literature-results').inner_text()
  api_results['crossrefDOI']={'passed':True,'returnedDOI':'10.1016/j.agsy.2022.103471'}
  page.locator('[data-save-ref]').first.click();page.wait_for_function("document.querySelector('[data-save-ref]').textContent.includes('已在')")
  rows=page.evaluate("async()=>await PaperWorkspace.lookup('Identifying exemplary sustainable cropping systems using a positive deviance approach')")
  assert any(r['doi']=='10.1016/j.agsy.2022.103471' for r in rows)
  api_results['crossrefTitle']={'passed':True,'returnedCount':len(rows)};checks.append('Live Crossref DOI and title lookup, metadata selection and local save')
  # Optional provider: report real result separately from the mandatory working provider.
  try:
   oa=page.evaluate("async()=>await PaperWorkspace.lookup('10.1016/j.agsy.2022.103471','openalex')")
   api_results['openalex']={'passed':bool(oa),'candidates':len(oa[0].get('candidates',[])) if oa else 0}
  except Exception as e:api_results['openalex']={'passed':False,'error':str(e)[:700]}
  page.goto(BASE+'#/my-library');page.wait_for_selector('[data-attach]');assert '本站有完整原文' in page.locator('#my-reference-list').inner_text()
  page.locator('[data-ref-state]').first.select_option('reading');page.locator('[data-ref-tags]').first.fill('TEST farming');page.locator('[data-ref-tags]').first.dispatch_event('change');page.reload();page.wait_for_selector('[data-ref-state]');assert page.locator('[data-ref-state]').first.input_value()=='reading';assert page.locator('[data-ref-tags]').first.input_value()=='TEST farming'
  checks.append('Reading state and tags persist after reload without conflating metadata and full text')
  page.goto(BASE+'#/discover');page.wait_for_selector('#literature-query')
  ris='TY  - JOUR\nTI  - TEST local citation\nAU  - Reader, One\nPY  - 2026\nDO  - 10.9999/test-citation\nER  -\n'
  bib='@article{example, title={A {nested} title}, author={One, A and Two, B}, year={2026}, doi={10.9999/example}}'
  assert page.evaluate('s=>PaperWorkspace.parseCitations(s)',ris)[0]['doi']=='10.9999/test-citation'
  assert page.evaluate('s=>PaperWorkspace.parseCitations(s)',bib)[0]['title']=='A nested title'
  checks.append('RIS and nested-brace BibTeX common-field parsing')
  # Invalid PDFs and cancelled imports never create complete books.
  before=page.evaluate("async()=>(await PaperReader.all('books')).length")
  bad=page.evaluate("async()=>{try{await PaperWorkspace.ingest(new File(['not pdf'],'invalid.pdf'));return false;}catch(e){return e.message;}}")
  assert 'PDF' in bad;assert page.evaluate("async()=>(await PaperReader.all('books')).length")==before
  # Import archived source through the same browser-local parser used for user files.
  result=page.evaluate("""async()=>{const rec=PAPER_SOURCES.records.find(r=>r.id==='liang-2022'),blob=await(await fetch(rec.originalPath)).blob();return await PaperWorkspace.ingest(new File([blob],'liang-2022.pdf',{type:'application/pdf'}));}""")
  book=result['book'];assert len(book['pages'])==15 and book['local'];bid=book['id']
  assert sum(len(p['blocks']) for p in book['pages'])>50
  duplicate=page.evaluate("""async()=>{const rec=PAPER_SOURCES.records.find(r=>r.id==='liang-2022'),blob=await(await fetch(rec.originalPath)).blob();return (await PaperWorkspace.ingest(new File([blob],'renamed.pdf',{type:'application/pdf'}))).duplicate;}""")
  assert duplicate;checks.append('Actual local PDF parsing preserves all 15 page images; identical files deduplicate by SHA256')
  page.goto(BASE+'#/original/'+bid);page.wait_for_selector('#view-page-images');assert page.locator('.source-page').count()==15
  page.locator('#view-page-images').click();assert page.locator('#original-text').evaluate("e=>e.classList.contains('source-image-mode')")
  assert page.locator('#reader-mode').is_disabled();page.locator('.page-proof img').first.scroll_into_view_if_needed();page.wait_for_function("document.querySelector('.page-proof img').naturalWidth>0")
  page.locator('.page-proof img').first.click();page.wait_for_selector('.image-dialog[open]');page.locator('.image-dialog button').click();page.locator('#view-page-images').click();assert not page.locator('#reader-mode').is_disabled()
  checks.append('Original-page image mode, zoom and safe return to selectable text')
  page.goto(BASE+'#/workbook/'+bid);page.wait_for_selector('[data-workbook="question"]');page.locator('[data-workbook="question"]').fill('TEST: study question grounded in source');page.wait_for_function("document.querySelector('#workbook-status').textContent.includes('已保存')")
  page.reload();page.wait_for_selector('[data-workbook="question"]');assert page.locator('[data-workbook="question"]').input_value().startswith('TEST:')
  with page.expect_download() as dl:page.locator('#export-reading-prompt').click()
  assert dl.value.suggested_filename.endswith('.md');checks.append('Source-linked six-stage reading workbook and private AI evidence export persist')
  page.goto(BASE+'#/glossary');page.wait_for_selector('#term-filter');page.locator('#term-filter').fill('MIDIP');assert '0.5' in page.locator('#term-list').text_content();assert page.evaluate('PAPER_STUDY.terms.length')>=90
  matches=page.evaluate("PaperStudy.matchTerms('multi‐objective optimization; 主成分分析; cluster centroid; positive de\\u00adviance; P-MODE')")
  assert len(matches)>=5,matches
  page.goto(BASE+'#/liang-2022');page.wait_for_selector('.reading-sequence');assert page.locator('.stage-io').count()==3
  term=page.locator('.prose [data-study-term="midip"]').first;term.click();page.wait_for_selector('.term-example');assert '0.5' in page.locator('.term-example').inner_text();page.locator('.term-popover').evaluate("e=>e.dispatchEvent(new WheelEvent('wheel',{bubbles:true,deltaY:40}))");assert page.locator('.term-popover').count()==1;page.keyboard.press('Escape');assert page.locator('.term-popover').count()==0
  checks.append('Expanded aliases, beginner examples, connected phase inputs/outputs and readable scrollable popovers')
  page.goto(BASE+'#/original/farmsteps-2026');page.wait_for_selector('#source-access-v4');assert page.locator('a[href="https://edepot.wur.nl/713946"]').count()>0;assert 'Taverne' in page.locator('#source-access-v4').inner_text()
  checks.append('Unarchived article provides official repository access instead of a dead-end unavailable message')
  # Simulated failure branches are explicitly separate from real public API acceptance.
  page.goto(BASE+'#/discover');page.wait_for_selector('#literature-query');page.route('https://api.crossref.org/**',lambda route:route.fulfill(status=429,body='rate limit',headers={'Access-Control-Allow-Origin':'*'}));page.locator('#literature-query').fill('10.9999/failure');page.locator('#literature-search').evaluate('e=>e.requestSubmit()');page.wait_for_function("document.querySelector('#literature-status').textContent.includes('限流')");page.unroute('https://api.crossref.org/**')
  checks.append('Simulated 429 provider error surfaces a useful retry status rather than a false empty result')
  # Full backup round-trip in isolated small library; no public article output or personal data logged.
  small=browser.new_context(accept_downloads=True);a=small.new_page();a.goto(BASE+'#/discover');a.wait_for_selector('#literature-query');a.on('dialog',lambda d:d.accept())
  tiny=a.evaluate("async()=>{const x=await PaperWorkspace.ingest(new File(['Introduction\\n\\nA farm has two fields.\\n\\nConclusion\\n\\nA synthetic example.'],'teaching.txt'));await PaperReader.put('annotations',{id:'test-note',docId:x.book.id,title:'TEST note',comment:'TEST private comment',type:'note',segments:[],links:[]});await PaperWorkspace.put('workbooks',{id:x.book.id,values:{question:'TEST workbook'}});return x.book.id;}")
  with a.expect_download() as dl:a.evaluate('PaperWorkspace.exportFull()')
  backup_path=RES/'synthetic-roundtrip.paperbackup';dl.value.save_as(backup_path)
  restored=browser.new_context(accept_downloads=True);r=restored.new_page();r.goto(BASE+'#/discover');r.wait_for_selector('#workspace-package');r.on('dialog',lambda d:d.accept())
  with r.expect_file_chooser() as fc:r.locator('#workspace-package').click()
  fc.value.set_files(str(backup_path));r.wait_for_selector('#my-reference-list');assert r.evaluate("async()=>(await PaperReader.all('books')).length")==1;assert r.evaluate("async()=>(await PaperReader.all('annotations'))[0].comment")=='TEST private comment';assert r.evaluate('async id=>(await PaperWorkspace.get("workbooks",id)).values.question',tiny)=='TEST workbook'
  checks.append('Full compressed personal backup restores local original, annotations, references and workbook in another browser context')
  # Mobile layouts and original fidelity images.
  for width in [360,390,430]:
   c=browser.new_context(viewport={'width':width,'height':844},is_mobile=True,has_touch=True);m=c.new_page();m.goto(BASE+'#/discover');m.wait_for_selector('#literature-query');assert m.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
   m.goto(BASE+'#/glossary');m.wait_for_selector('#term-filter');assert m.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
   m.goto(BASE+'#/original/liang-2022');m.wait_for_selector('#view-page-images');m.locator('#view-page-images').click();assert m.evaluate('document.documentElement.scrollWidth<=innerWidth+1');m.screenshot(path=str(RES/f'workspace-mobile-{width}.png'));c.close()
  checks.append('360/390/430px touch layouts: discovery, glossary and original-page images do not overflow')
  manifest=json.loads((OUT/'offline-manifest.json').read_text());assert './workspace.js' in manifest['core'] and './workspace.css' in manifest['core']
  assert '<script src="workspace.js">' not in (OUT/'downloads/Paper-Lab-offline.html').read_text()
  checks.append('New scripts/styles included in offline core and embedded standalone HTML')
  assert not errors,errors
 except Exception:
  failure=traceback.format_exc();raise
 finally:
  report={'passed':checks,'api':api_results,'browserErrors':errors,'failure':failure,'scope':'Chromium desktop and 360/390/430px touch simulations; actual Crossref DOI/title API; mock only explicitly named error tests; no physical device or institutional login test'}
  (RES/'workspace-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));page.screenshot(path=str(RES/'workspace-last-state.png'));browser.close();server.shutdown()
print(json.dumps({'passed':checks,'api':api_results},ensure_ascii=False))

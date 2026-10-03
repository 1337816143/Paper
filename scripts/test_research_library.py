#!/usr/bin/env python3
"""Research navigation and legacy-note compatibility against the built application."""
from pathlib import Path
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json, threading
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'dist/site';RES=ROOT/'test-results';RES.mkdir(exist_ok=True)
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(OUT)))
threading.Thread(target=server.serve_forever,daemon=True).start();BASE=f'http://127.0.0.1:{server.server_port}/'
checks=[];errors=[]
def check(name,ok):
 assert ok,name
 checks.append(name)
def goto(page,id):
 page.goto(BASE+'#/'+id);page.wait_for_function('!!window.PaperLibrary');page.wait_for_timeout(150)
try:
 with sync_playwright() as pw:
  b=pw.chromium.launch();ctx=b.new_context(viewport={'width':1440,'height':1000},accept_downloads=True);page=ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
  goto(page,'home');check('Six primary research entrances',page.locator('nav[aria-label="主导航"] a').all_text_contents()==['研究总览','论文工作区','概念与方法','模型与软件','综合与创新','我的工作'])
  check('Home has no assessment entry or reader score',not any(x in page.locator('#view').inner_text() for x in ['自测','成绩','能力验收','先猜']))
  page.screenshot(path=str(RES/'research-library-desktop.png'),full_page=True)
  # Every official coverage row is conservative about source availability and reproduction.
  goto(page,'coverage');check('All 22 sources have coverage rows',page.locator('.coverage-card').count()==22)
  check('Archive availability is independent from close reading', '全文各节和案例尚未完整核读' in page.locator('#verdouw-2021').inner_text() and '许可原文已归档' in page.locator('#verdouw-2021').inner_text())
  check('Unpublished private sources stay distinct', '公开站未归档全文' in page.locator('#dong-2026').inner_text() and '13页出版PDF全文已核读' in page.locator('#dong-2026').inner_text())
  goto(page,'library');page.locator('[data-filter="程嘉莉"]').click();check('Author filtering still works',page.locator('#catalog .card').count()>=3 and page.locator('#catalog .coverage-inline').count()>=3)
  # Seed an old synthetic v1 backup, including optional method-contract keys.
  legacy={'notes':{'liang-2022':'SYNTHETIC legacy paper note: 机制练习是我的原话','research::liang-2022::s1':'SYNTHETIC stable section','research::liang-2022::method-contract-explain':'SYNTHETIC existing research explanation'},'done':{'liang-2022':True},'positions':{'liang-2022':{'route':'#/liang-2022/s1','y':640,'at':1}},'last':'liang-2022'}
  page.evaluate('(s)=>localStorage.setItem("paper-lab-learning-v1",JSON.stringify(s))',legacy);page.reload();goto(page,'liang-2022');page.wait_for_selector('.research-reading-layers')
  check('Question explanations are open with no checkbox or score',page.locator('#self-test details').count()>0 and page.locator('#self-test details:not([open])').count()==0 and page.locator('#done').count()==0)
  check('Old note and section anchor survive refocus',page.locator('#note').input_value()==legacy['notes']['liang-2022'] and page.locator('#s1').count()==1)
  check('Method-contract explanation retains its exact old key',page.locator('[data-note-key="research::liang-2022::method-contract-explain"] textarea').input_value()==legacy['notes']['research::liang-2022::method-contract-explain'])
  check('Legacy done data is not removed or reinterpreted',page.evaluate('JSON.parse(localStorage.getItem("paper-lab-learning-v1")).done["liang-2022"]') is True)
  page.locator('nav[aria-label="三层研究阅读"] a').nth(2).click();check('Evidence depth has a real anchor',page.locator('#research-evidence').count()==1)
  goto(page,'whole-farm');check('Full numeric explanation retained', '1200 h/年' in page.locator('#s6').inner_text() and '请先自己算' not in page.locator('#s6').inner_text())
  goto(page,'lab');check('Mechanisms show computed Pareto and complete Q example immediately','非支配' in page.locator('#pareto-result').inner_text() and all(page.locator('.q-select').nth(i).input_value() for i in range(20)))
  for width in [390,320]:
   page.set_viewport_size({'width':width,'height':844})
   for id in ['home','library','methods','model-software','research-synthesis','my-work','coverage','liang-2022']:
    goto(page,id)
    if page.evaluate('document.documentElement.scrollWidth>innerWidth+2'):
     page.screenshot(path=str(RES/f'research-overflow-{width}-{id}.png'),full_page=True)
     (RES/f'research-overflow-{width}-{id}.json').write_text(json.dumps(page.evaluate('Array.from(document.querySelectorAll("#view *")).filter(e=>e.getBoundingClientRect().right>innerWidth+2).map(e=>({tag:e.tagName,cls:e.className,text:e.textContent.slice(0,100),right:e.getBoundingClientRect().right}))'),ensure_ascii=False,indent=2))
    check(f'{width}px {id} has no horizontal overflow',page.evaluate('document.documentElement.scrollWidth<=innerWidth+2'))
   goto(page,'home');page.locator('#menu').click();check(f'{width}px all six mobile navigation entries accessible',page.locator('nav[aria-label="主导航"] a').count()==6 and page.locator('#sidebar').evaluate('e=>e.classList.contains("open")'))
   page.locator('nav[aria-label="主导航"] a[href="#/my-work"]').click();check(f'{width}px mobile navigation closes after use',not page.locator('#sidebar').evaluate('e=>e.classList.contains("open")'))
  page.set_viewport_size({'width':390,'height':844});goto(page,'home');page.screenshot(path=str(RES/'research-library-mobile.png'),full_page=True)
  goto(page,'liang-2022');page.evaluate('navigator.serviceWorker.ready.then(()=>true)');page.wait_for_function('!!navigator.serviceWorker.controller',timeout=60000);ctx.set_offline(True);page.reload();page.wait_for_selector('.research-reading-layers');check('Offline article keeps new navigation and legacy note',page.locator('#note').input_value()==legacy['notes']['liang-2022']);ctx.set_offline(False)
  goto(page,'notes')
  with page.expect_download() as download:page.locator('[data-action="export"]').click()
  backup_path=Path(download.value.path());backup=json.loads(backup_path.read_text());check('Export preserves legacy flags and all research-note keys',backup['data']['done']['liang-2022'] and all(backup['data']['notes'][k]==v for k,v in legacy['notes'].items()))
  check('Private note wording is not changed by the explanation presentation layer','机制练习是我的原话' in page.locator('#view').inner_text())
  restore_ctx=b.new_context();restore=restore_ctx.new_page();goto(restore,'notes');restore.locator('#import-file').set_input_files({'name':'legacy-backup.json','mimeType':'application/json','buffer':backup_path.read_bytes()});restore.wait_for_timeout(250)
  restored=restore.evaluate('JSON.parse(localStorage.getItem("paper-lab-learning-v1"))');check('Import restores all legacy and optional research notes',all(restored['notes'][k]==v for k,v in legacy['notes'].items()) and restored['done']['liang-2022'])
  single=b.new_page();single.goto((OUT/'downloads/Paper-Lab-offline.html').as_uri()+'#/coverage');single.wait_for_selector('.coverage-card');check('Standalone file embeds research coverage and presentation assets',single.locator('.coverage-card').count()==22)
  check('No uncaught application errors',not errors);b.close()
 report={'passed':True,'checks':checks,'errors':errors,'scope':'Synthetic local data and Chromium; no real private credentials or claims about cross-device login'}
except Exception as e:
 report={'passed':False,'checks':checks,'errors':errors,'error':str(e)}
 raise
finally:
 (RES/'research-library-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));server.shutdown()
print(json.dumps({'passed':True,'checks':len(checks)}))

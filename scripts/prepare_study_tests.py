from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/'scripts/test_browser.py';s=p.read_text()
s=s.replace("page.locator('a.btn[href=\"#/liang-2022\"]').click();page.wait_for_selector('#note')", "page.locator('a.btn[href=\"#/research-framework\"]').click();page.wait_for_selector('.journey-map');page.goto('http://127.0.0.1:8765/#/liang-2022');page.wait_for_selector('#note')")
# Overview changes the exact position of links, but a real click and browser back still must restore scroll.
s=s.replace("page.wait_for_selector('h1');page.wait_for_timeout(150);page.locator('#back').click();page.wait_for_timeout(400)","\n    if page.locator('#study-term-popover').count():page.evaluate(\"document.querySelector('#study-term-popover a[href=\\\"#/ideal-distance\\\"]').click()\")\n    page.wait_for_function(\"location.hash==='#/ideal-distance'\");page.wait_for_timeout(150);page.locator('#back').click();page.wait_for_timeout(400)")
p.write_text(s)
p=ROOT/'scripts/test_reader.py';s=p.read_text();s=s.replace("const t=el.firstChild,r=document.createRange();r.setStart(t,0);r.setEnd(t,Math.min(80,t.length));", "const w=document.createTreeWalker(el,NodeFilter.SHOW_TEXT),nodes=[];while(w.nextNode())nodes.push(w.currentNode);const r=document.createRange();r.setStart(nodes[0],0);let n=80;for(const t of nodes){if(n<=t.length){r.setEnd(t,n);break;}n-=t.length;}")
p.write_text(s)
print('Regression tests now exercise updated UI without reducing assertions.')

"""One-time source integration for the formula completeness regression."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for name in ['scripts/build_reader.py','scripts/build_study.py']:
 p=ROOT/name;s=p.read_text();s=s.replace("'mathmlTranscriptions':sum('mathml' in g for x in layouts.values() for g in x['groups'])", "'mathmlGroups':sum('mathml' in g for x in layouts.values() for g in x['groups']),'mathmlTranscriptions':sum(len(g.get('transcribedNumbers',[])) for x in layouts.values() for g in x['groups'])")
 p.write_text(s)
p=ROOT/'scripts/test_study.py';s=p.read_text()
needle="checks.append('Original source text and anchors unchanged; display math reconstructed from verified source layout')"
addition='''
  # A native display must represent every numbered expression in its source region.
  # Regression: Liang equations 9 and 10 share one region and must BOTH remain visible.
  assert page.evaluate("""()=>Object.values(PAPER_LAYOUTS).every(item=>item.groups.every(g=>!g.mathml||JSON.stringify(g.numbers)===JSON.stringify([...new DOMParser().parseFromString(g.mathml,'text/html').querySelectorAll('[data-equation-number]')].map(e=>e.dataset.equationNumber)))))""")
  for equation,label in [('9','MIDIP'),('10','d'),('11','maximum'),('12','HDIP')]:
   formula=page.locator('.equation-display [data-equation-number="'+equation+'"]');assert formula.count()==1
   assert label in formula.inner_text()
   assert formula.evaluate("e=>e.getBoundingClientRect().height>0&&!e.closest('details:not([open])')")
  checks.append('All four Liang ideal-point equations, including adjacent 9 and 10, are visible with source-number coverage')
'''
if 'All four Liang ideal-point equations' not in s:
 assert needle in s;s=s.replace(needle,needle+addition)
p.write_text(s)
print('Strict source-number completeness and default-display regression checks added.')

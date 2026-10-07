"""Exact inverse of the independently reviewed Liang append-only text delta.

Existing frozen hashes are retained. Only the two specified final sentence
additions and their manifest hashes may be removed for old-baseline comparison.
"""
from pathlib import Path
import copy,hashlib,html
ADDITION='同一篇原文存在未解决的降幅差异：§3.3（PDF第6页）报告劳动、地下水耗减、氮损失、净温室气体和农药使用分别下降17%、31%、34%、69%、46%；Fig.7（PDF第12页）则依次标为20%、35%、33%、51%、46%。这些是两个位置各自发表的数字，不合并成一套已复算值；逐案例原始数据和补充Table S9尚未取得，不能据此判定哪套正确。'
HASHES={
 'full':('92cfc99d8491739f8e7235c364b60faa65bdf901d83bb1f613fd09c8fa38516b','0224d898f4fb0925ecedb5e645dea00724c7c05a347d95b7cb8d4c5765ad99b6'),
 'brief':('c1ca5cbbf490b9b85af0092b6c9409539212de808616d0b89061e4955e252e30','b197c754c970725d47ff3188df0b191140e75f996090a3dcc64e32113cea1d14')}
sha=lambda b:hashlib.sha256(b).hexdigest()
def original_source_bytes(root,path):
 raw=(Path(root)/path).read_bytes()
 if path=='resources/research-leads/accepted.json':
  for before,after in HASHES.values():
   assert raw.count(after.encode())==1
   raw=raw.replace(after.encode(),before.encode(),1)
 elif path in {f'resources/research-leads/liang-2022/{v}.txt' for v in HASHES}:
  version=Path(path).stem;before,after=HASHES[version]
  assert sha(raw)==after,(path,'Unexpected candidate text')
  assert raw.count(ADDITION.encode())==1
  raw=raw.replace(ADDITION.encode(),b'',1)
  assert sha(raw)==before,(path,'Existing text changed')
 return raw

def original_leads(leads):
 result=copy.deepcopy(leads);row=result['liang-2022']
 assert row['paragraphs']=={'full':11,'brief':5}
 assert row['html'].count(html.escape(ADDITION))==2
 row['html']=row['html'].replace(html.escape(ADDITION),'')
 for version,(before,after) in HASHES.items():
  assert row['hashes'][version]==after
  attribute='data-lead-sha256="'+after+'"'
  assert row['html'].count(attribute)==1
  row['html']=row['html'].replace(attribute,'data-lead-sha256="'+before+'"',1)
  row['hashes'][version]=before
 return result

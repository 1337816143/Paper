#!/usr/bin/env python3
"""Adversarial evidence and legacy-anchor checks for thesis-related additions."""
import hashlib,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads((ROOT/p).read_text())
P={d['id']:d for d in read('content/papers.json')}
G=read('content/thesis-evidence-v552.json')[0]
L=G['sourceLedger'];TEXT=json.dumps(G,ensure_ascii=False)
LEGACY={'liang-thesis': {'count': 3, 'digest': 'f1b1a91c7377f49850c768b79685149d89ef97b86b9118f81d226fc2e244b980', 'quiz': [['为什么不能把文章发表年份直接当作毕业年份？', '论文可能毕业前投稿、毕业后才发表，且最终版本可能继续扩展。']]}, 'cheng-thesis': {'count': 4, 'digest': '0e725b9b55df5b5356c507f7fb8e885e8cc8e2450b151a3ef8f28451d7f83d2e', 'quiz': [['能根据Q方法论文直接断言最终优化用了哪一套权重吗？', '不能。需查实际优化章的接口定义。']]}}
class ThesisEvidence(unittest.TestCase):
 def test_old_section_content_order_and_quizzes_untouched(self):
  for id,e in LEGACY.items():
   old=P[id]['sections'][:e['count']]
   self.assertEqual(hashlib.sha256(json.dumps(old,ensure_ascii=False,sort_keys=True).encode()).hexdigest(),e['digest'])
   self.assertEqual(P[id].get('quiz',[]),e['quiz'])
 def test_conference_and_thesis_are_distinct(self):
  self.assertEqual(L['kind'],'conference-paper')
  self.assertEqual(L['pages'],'442–444');self.assertEqual(L['pdfPages'],[2,3,4]);self.assertEqual(L['pdfContainerPages'],6)
  self.assertFalse(L['fullThesisAcquired']);self.assertFalse(L['originalModelRun'])
  self.assertEqual(L['sha256'],'11c5173da6f9f38cdd2084dc5e74e7029f345a8d7e5ddeed5f538cd8b5dfa0b4')
  self.assertEqual(G['quiz'],[])
  self.assertEqual(len(read('resources/research-coverage-v55.json')['papers']),22)
  self.assertEqual(len(read('resources/method-contracts-v54.json')['contracts'])+1,22)
  self.assertEqual(G['type'],'guide')
  self.assertNotIn(G['id'],read('resources/research-coverage-v55.json')['papers'])
  self.assertNotIn(G['id'],read('resources/method-contracts-v54.json')['contracts'])
 def test_notice_dates_are_sourced_not_download_error_inferences(self):
  r={x['id']:x for x in read('resources/catalog.json')['records']}
  for id,date in [('liang-thesis','2026-12-31'),('cheng-thesis','2027-01-09')]:
   self.assertEqual(r[id]['embargoNoticeDate'],date)
   self.assertEqual(r[id]['accessStatus'],'official-embargo')
   a=r[id]['accessAttempts'][-1];self.assertEqual(a['noticeUntil'],date);self.assertEqual(a['method'],'cloud-browser-visible-page');self.assertFalse(a['fullTextAcquired'])
   self.assertIn(date,P[id]['evidence']);self.assertNotIn('bookPath',r[id])
   self.assertIn('即使日期已过，也不能自动改为已取得全文',r[id]['accessRecheckPolicy'])
 def test_no_unjustified_methods_upgrade(self):
  for t in ['five steps','Step 1–4','8项都被直接优化','全局最优','潜力','未能让利益相关者','2026摘要反写2025','一年','公式表','WaterUse','SoilCarbon','N Leaching']:
   self.assertIn(t,TEXT)
  self.assertIn('N Leaching：kg ha⁻¹ year⁻¹',TEXT)
  self.assertIn('不能直接叫家庭食物安全',TEXT)
 def test_falsifiability_and_information_fairness(self):
  for t in ['反证','独立接受判断','未来真实天气','转换成本','尚未证明原创','PhD1','O2/O3','原始数据']:
   self.assertIn(t,TEXT if t!='原始数据' else json.dumps(read('content/session-log.json')[-1],ensure_ascii=False))
 def test_license_and_public_data_boundaries(self):
  self.assertEqual(L['license'],'CC BY-NC-ND 4.0')
  for t in ['不再分发PDF','逐段译文','软件许可']:self.assertIn(t,TEXT)
  for p in [ROOT/'content/thesis-evidence-v552.json']:
   text=p.read_text()
   for private in ['assistant-review.json','private/paper-sync','github_pat_','ghp_','BEGIN PRIVATE KEY']:
    self.assertNotIn(private,text)
 def test_build_contains_sources_and_stable_anchors(self):
  out=ROOT/'dist/site'
  if not (out/'data.json').exists():self.skipTest('Build first')
  h=(out/'read/cheng-landscape-evidence-2025.html').read_text()
  for s in ['Differential Evolution','2026摘要反写2025','701440','442','O2/O3']:self.assertIn(s,h)
  for id,e in LEGACY.items():
   html=(out/f'read/{id}.html').read_text()
   for n in range(e['count']):self.assertIn(f'id="s{n}"',html)
  self.assertFalse(any(out.rglob('cheng-fsd2025.pdf')))
if __name__=='__main__':unittest.main(verbosity=2)

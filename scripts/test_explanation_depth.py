#!/usr/bin/env python3
"""Worked-example, source-boundary, and stable-note checks; no learner tests."""
import hashlib,importlib.util,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads((ROOT/p).read_text())
LEGACY={'liang-indicator-audit': {'file': 'content/indicator-audit-v53.json', 'quiz': [['本文为什么不是一套完整的专家赋权指标筛选？', '原文明确按当地挑战选三域七指标，并未报告Delphi/AHP或穷举候选后筛选的程序，不能替作者补上。'], ['哪几项明显依赖共同/经验参数而非逐户全过程实测？', '例如多数单位作业工时、抽水电量换算、深层补给、N损失和温室气体/土壤碳项。应逐项查看正文与补充材料，而非把整个矩阵当全部实测。'], ['地下水补给α=0.2可以直接用于海南吗？', '不可以默认。它是原文案例区域采用的系数，海南水源、地形、土壤和降水条件需另核对或校准。']], 'sectionHashes': ['7a9c5970328ce28c6a6cddc394881f8826ead93f6f7c9cdef194b06efa49fdac', '84d8ed9185a5685ce1c764a1c843fda1265dfa59bfd9b7d18d979e5950ca18b1', '38275834823c6a73fa89b327d617c42a1217eaa4aca8cdf391113d711622d87c', '06dd8a4446283cbcd0781163734ceef2714b2198db97e66f4c2f653e2ac49ddb', '3105127d570f64cd1da37ed1b48ac86c5093a37931b1c3046f36f575ade5914c', '064d13254e22e57aa48e777bca2511f02fa4925af6e2ac7534a35179a393a705', 'e00ad578f02269cd8b10bddbe974f87310bdde70715b7f9163f8f7ae01cd4ca6', 'ed36f565bb538d82456b568d1594f00e537f7f63e9cd9c36bedb1042c0d8aea1', '8dedd52c24309778d1bad0217725fc6ef18541d376e15a253e1fc85d513378f7', '3cac3feee072f1e4969475873629c07d6d841e2e6b772e311f8025ff13f83323', '97b401c5f40959f53e41691a5e6189dfd8ff2aa3d2bf28e028f76a8cc3e34f4f', 'b2ca64ed6449a0809afeca9c3b2c5f70f0369803b8b4a235df29c0353f6ca51a']}, 'pareto': {'file': 'content/methods.json', 'quiz': [['A和B所有指标完全相同时，A支配B吗？', '严格Pareto支配要求至少一项更好，因此不支配。应说明重复点的保留策略。'], ['某方案支配全部已观测农场，能证明现实全局最优吗？', '不能，只能说明相对这些观测、指标和边界的表现。']], 'sectionHashes': ['0c0eab95a58f2f7717ada649f17a86b361c1e81025e738aec263386b9d5f2b6a', 'feb0f93593dd32c1719eb8b3ad0bf67621d974eb167b9c0eb8b1cb6be4499157', '84c9eda76b3ba3048f3ad90bf3252a254b2a866aa5a130b53821494a6c53c551', 'b4a80212437ea190107058114bbfb45641a8b24cf7d72df3f10937987017e0eb']}, 'ideal-distance': {'file': 'content/methods.json', 'quiz': [['MIDIP是距离的平均值吗？', '梁2022这里是标准化距离的欧氏范数，即平方求和开根号。'], ['HDIP=0是否代表理想方案？', '不是，仅说明各指标离理想点的距离相同。']], 'sectionHashes': ['55e256ef3f7d0478313659078ef5ced62d71e0971b95851bd6a20d46f42b6bb2', 'af7fb0d24df3c56845f6caf1a65cb106d1a29c9f6cf3039f2c088edfd3ab9dba', '4b8c907f1350385bd0c9d92b85407faa382efb38ff27f9ff018c28c7144245d8', '635249dec4716ec4b93a05858ba785029ecfc78ed561d2e269cbd176a7429ddb']}, 'data-schema': {'file': 'content/methods.json', 'quiz': [['为什么应同时存数值和单位？', '跨来源可能使用亩、公顷、吨、公斤、干鲜重和不同时间尺度，单位丢失后无法可靠核算。']], 'sectionHashes': ['cf48933b549743079434f5302511503fcaf094a79410a9c96226dd25719229da', 'd38bc7aecf714b1e8b34c979b89d1214568610844c546f8ad3108333acbcaaa0', '1bc486212c3d017fb288b4ab410cba01d1edec01994a802326246e3eda63662f', '44b9cbf23455b4ad55800d488bfb208a92c4ad6fb36790e30deb54bbfe33debc']}}
class ExplanationDepth(unittest.TestCase):
 def test_source_methods_are_explicit_and_missing_parameters_not_invented(self):
  g=read('content/indicator-audit-v53.json')[0];meta=g['workedCalculations']
  self.assertEqual(meta['originalEquations'],list('12345678'))
  self.assertTrue(meta['allExamplesSynthetic']);self.assertFalse(meta['jointlyCalibratedFarm']);self.assertFalse(meta['authorResultReproduced'])
  self.assertEqual(len(meta['originalMissingParameters']),6)
  for i in range(2,9):
   s=g['sections'][i][2]
   for label in ['原文公式 → 代入 → 解释','作者怎样算','完整合成代入','怎样读结果与常见错误']:self.assertIn(label,s)
  for value in ['1900','45.82','74 h/ha/year','260 mm/year','83.5','2.5','6 doses/year']:
   self.assertIn(value,json.dumps(g,ensure_ascii=False))
 def test_old_indicator_paragraphs_are_preserved_as_prefixes(self):
  # Complete original strings remain at every old sN position; compare the
  # untouched prefix preceding the visibly marked addition, not its new text.
  for id,e in LEGACY.items():
   g=next(x for x in read(e['file']) if x['id']==id)
   self.assertEqual(g.get('quiz',[]),e['quiz'])
   for i,sha in enumerate(e['sectionHashes']):
    s=list(g['sections'][i])
    if id=='liang-indicator-audit':
     s[2]=s[2].split('\n\n【从零开始：原文公式 → 代入 → 解释】')[0].split('\n\n【本轮阅读标记】')[0]
     if i==0:s[3]=s[3].removesuffix('；2026-10-04增量补七项公式/代入')
    self.assertEqual(hashlib.sha256(json.dumps(s,ensure_ascii=False).encode()).hexdigest(),sha,(id,i))
 def test_roadmap_preserves_honest_page_level_scope(self):
  g=read('content/explanation-roadmap-v553.json')[0];a=g['auditSnapshot']
  self.assertEqual(len(a['pageCoverage']),112);self.assertEqual(len({x['pageId'] for x in a['pageCoverage']}),112)
  self.assertEqual(a['scope']['coverageCounts'],{'targeted_lesson_reading':57,'inventory_only':37,'separately_updated_not_reassessed':5,'historical_update_inventory_only':13})
  self.assertEqual(len(a['findings']),25)
  self.assertEqual(g['quiz'],[]);self.assertIn('不是全站全部细节',g['evidence'])
  docs={d['id']:d for f in (ROOT/'content').glob('*.json') for d in json.loads(f.read_text())}
  for f in a['findings']:
   self.assertIn(f['pageId'],docs);self.assertEqual(f['sectionId'],'s'+str(f['sectionIndex']))
   self.assertIn(f['passage'],docs[f['pageId']]['sections'][f['sectionIndex']][2])
   for id in f['relatedPages']:self.assertIn(id,docs)
  self.assertTrue(all(x['pageId'] in docs for x in a['pageCoverage']))
  self.assertIn('不与原文SC1–SC4一一对应',json.dumps(read('resources/method-contracts-v54.json')['contracts']['xu-thesis'],ensure_ascii=False))
  self.assertIn('劳动上限为9',json.dumps(read('content/research-library-v55.json'),ensure_ascii=False))
 def test_all_three_explanation_scripts_are_published_whole(self):
  out=ROOT/'dist/site'
  for name in ['seven_indicators_worked','research_pipeline_walkthrough','exemplar_transfer']:
   p=ROOT/'examples'/f'{name}.py';spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
   self.assertTrue(m.test()['passed'])
   self.assertEqual((out/'examples'/p.name).read_bytes(),p.read_bytes())
  data=json.loads((out/'data.json').read_text());docs={d['id']:d for d in data['documents']}
  for id in LEGACY:
   page=(out/f'read/{id}.html').read_text()
   for i in range(len(LEGACY[id]['sectionHashes'])):self.assertIn(f'id="s{i}"',page)
  self.assertFalse(any('先答' in s[2] for s in docs['liang-indicator-audit']['sections'][2:9]))
if __name__=='__main__':unittest.main(verbosity=2)

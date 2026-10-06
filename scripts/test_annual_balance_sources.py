#!/usr/bin/env python3
"""Source, original-anchor and packaging contracts for the annual balance lesson."""
from pathlib import Path
import hashlib
import json
import re
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads((ROOT / path).read_text())


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


class Sources(unittest.TestCase):
    def test_published_prose_and_source_catalog_unchanged(self):
        baseline = read('tests/annual-balance/source-baseline.json')
        self.assertEqual(baseline['sourceCommit'], '1345e9c27f1b0a6d92efb8730be94e055547ee05')
        self.assertEqual(len(baseline['documents']), 120)
        for identity, old in baseline['documents'].items():
            document = next(d for d in read(old['file']) if d['id'] == identity)
            sections = document['sections']
            if identity == 'cheng-2025-q-walkthrough':
                contract = read('tests/q/append-only-contract.json')
                self.assertEqual(old['sectionCount'], 20)
                self.assertEqual(contract['preservedSectionCount'], old['sectionCount'])
                self.assertEqual(contract['preservedSectionsSha256'], old['sectionsSha256'])
                self.assertEqual(len(sections), old['sectionCount'] + 3, identity)
                self.assertEqual([s[0] for s in sections[20:]], contract['appendedTitles'])
                sections = sections[:old['sectionCount']]
            if identity in {'dong-2026','dong-2026-ledger'}:
                contract = read('tests/dong/append-only-contract.json')['documents'][identity]
                self.assertEqual(contract['originalSectionCount'], old['sectionCount'])
                self.assertEqual(contract['originalSectionsSha256'], old['sectionsSha256'])
                self.assertEqual(len(sections), old['sectionCount'] + 1)
                self.assertEqual([s[0] for s in sections[old['sectionCount']:]], contract['appendedTitles'])
                sections = sections[:old['sectionCount']]
            self.assertEqual(len(sections), old['sectionCount'], identity)
            self.assertEqual(digest(sections), old['sectionsSha256'], identity)
            self.assertEqual(digest(document.get('quiz', [])), old['quizSha256'], identity)
        catalog = read('resources/catalog.json')
        contract = read('tests/dong/append-only-contract.json')
        dong = next(row for row in catalog['records'] if row['id'] == 'dong-2026')
        self.assertEqual(dong['pages'], 13)
        self.assertEqual(dong['sha256'], 'cf0b6c31874d95e945d7e3926ba7c64806d719d2aede3b2c13fdb6658aed2b86')
        self.assertIn(contract['catalogOriginalReason'], dong['reason'])
        self.assertEqual(dong['sourceStatusUpdatedAt'], '2026-10-06')
        self.assertTrue(dong['sourceIdentityMapping']['canonicalCatalogIdentityPreserved'])
        dong['reason'] = contract['catalogOriginalReason']
        del dong['sourceStatusUpdatedAt']; del dong['sourceIdentityMapping']
        original_bytes = (json.dumps(catalog, ensure_ascii=False, indent=2) + '\n').encode()
        self.assertEqual(hashlib.sha256(original_bytes).hexdigest(), baseline['catalogSha256'])
        self.assertEqual(contract['catalogOriginalSHA256'], baseline['catalogSha256'])

    def test_new_guides_separate_sources_and_teaching(self):
        docs = read('content/wholefarm-balance-v557.json')
        self.assertEqual([x['sourceId'] for x in docs], ['farmdesign-2012', 'qu-2025'])
        self.assertEqual(sum(len(x['sections']) for x in docs), 34)
        for d in docs:
            self.assertEqual(d['quiz'], [])
            for s in d['sections']:
                self.assertEqual(len(s), 4)
                self.assertTrue(s[3])
        text = json.dumps(docs, ensure_ascii=False)
        for fact in ['9–9.5ha','9–45ha','62头','56.2 LU','M1和M4','15–28kg','3000h','4000h','Table 3','0.25','160欧元','8页参数附录']:
            self.assertTrue(fact in text, "Missing source boundary: " + fact)
        self.assertNotIn('本轮没有取得', docs[0]['sections'][2][2])
        self.assertNotIn('全场全场', text)
        self.assertTrue(all('合成' in json.dumps(d,ensure_ascii=False) for d in docs))

    def test_input_csv_and_python_are_self_contained(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location('annual_balance',ROOT/'examples/annual_balance.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        value=module.read_input(str(ROOT/'examples/annual_balance_synthetic.csv'))
        self.assertEqual(value,module.DEFAULTS)
        self.assertEqual(module.calculate(value)['farmSurplus'],720)
        self.assertNotRegex((ROOT/'examples/annual_balance.py').read_text(),r'\b(?:numpy|pandas|requests)\b')
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'malformed.csv'
            for row in ['8,6,0.2,false,99','8,6','8,6,0.2']:
                path.write_text('herd,forageArea,lossFraction,replaceRetained\n'+row+'\n')
                with self.assertRaisesRegex(ValueError,'exactly four columns'):
                    module.read_input(str(path))

    def test_built_assets_examples_and_standalone(self):
        out=ROOT/'dist/site'
        for name in ['annual-balance-model.js','annual-balance-walkthrough.js','annual-balance-walkthrough.css']:
            self.assertEqual((out/name).read_bytes(),(ROOT/'src'/name).read_bytes())
        for name in ['annual_balance.py','annual_balance_synthetic.csv','annual_balance_readme.md','annual_balance_sources.json']:
            self.assertEqual((out/'examples'/name).read_bytes(),(ROOT/'examples'/name).read_bytes())
        release=json.loads((out/'release.json').read_text())
        self.assertEqual(release['appVersion'],read('resources/application-release.json')['version'])
        self.assertEqual(release['annualBalance']['inputConfigurations'],4410)
        self.assertFalse(release['annualBalance']['agronomicResponseValidated'])
        self.assertFalse(release['annualBalance']['sourceDataReproduced'])
        self.assertEqual(release['paperEntries'],22)
        single=(out/'downloads/Paper-Lab-offline.html').read_text()
        self.assertIn('PaperAnnualBalanceModel',single)
        self.assertIn('PaperAnnualBalance',single)
        self.assertNotIn('<script src="annual-balance',single)
        self.assertNotIn('<link rel="stylesheet" href="annual-balance',single)
        for id in ['farmdesign-2012','qu-2025','whole-farm','nutrients']:
            self.assertIn('annual-balance-link',(out/'read'/f'{id}.html').read_text())


if __name__=='__main__':
    unittest.main()

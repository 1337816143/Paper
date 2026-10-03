#!/usr/bin/env python3
"""Content/source invariants for the 2026-10-03 teaching expansion (no browser)."""
from pathlib import Path
import hashlib
import importlib.util
import json
import unittest

ROOT = Path(__file__).resolve().parents[1]
METHODS = {d['id']: d for d in json.loads((ROOT/'content/methods.json').read_text())}
RESEARCH = json.loads((ROOT/'resources/research-v53.json').read_text())
CATALOG = {d['id']: d for d in json.loads((ROOT/'resources/catalog.json').read_text())['records']}
spec = importlib.util.spec_from_file_location('model_reasoning_lab', ROOT/'examples/model_reasoning_lab.py')
lab = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lab)

# The old section/quiz prefixes from c6658cd4. Appending retains every existing
# section's sN note anchor and the user's stored reading context.
PREFIXES = {
    'whole-farm': (4, 1, '915ec825a4ffc5163f77b892a6a14a2cfb1087995162a6790bedeb2515c3b30f'),
    'nutrients': (4, 1, '47971f3351bde3fd2a3d44e2b3106124e414348faae777ffec477a5e239ed93e'),
    'uncertainty': (5, 1, '5fe6a7277e2dd44bb16ab9cf35d2d362c51caaa0c87dc182950f7e7f515237d5'),
}
SOURCES = {
    'qu-2025': ('7e69eb40dc235c56e72cddc615d123cb8b8679999727d499127a08b0cb2b2769',
                ['p4-b17-3c2633d', 'p3-b9-50c5481', 'p4-b10-752da54']),
    'breure-2024': ('766abe34a78ec2fc630ba474fb035879c398600884bd5676bca435b05aed9bc4',
                    ['p8-b2-7105be4']),
}


class ContentTests(unittest.TestCase):
    def test_existing_sections_and_note_anchor_order_are_preserved(self):
        for id, (n, q, fingerprint) in PREFIXES.items():
            d = METHODS[id]
            old = {'sections': d['sections'][:n], 'quiz': d['quiz'][:q]}
            actual = hashlib.sha256(json.dumps(old, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
            self.assertEqual(actual, fingerprint, id)
            self.assertGreater(len(d['sections']), n)
            self.assertGreater(len(d['quiz']), q)

    def test_new_sections_have_provenance_and_internal_routes(self):
        for id, (n, _, _) in PREFIXES.items():
            for section in METHODS[id]['sections'][n:]:
                self.assertEqual(len(section), 4, (id, section[0]))
                self.assertTrue(section[3].strip())
                self.assertNotIn('[[', section[3], 'Provenance is plain text in the existing renderer')
        self.assertIn('[[topic6-requirements|', json.dumps(METHODS['whole-farm'], ensure_ascii=False))
        self.assertIn('[[whole-farm|', json.dumps(METHODS['uncertainty'], ensure_ascii=False))
        self.assertIn('[[qu-2025|', json.dumps(METHODS['nutrients'], ensure_ascii=False))

    def test_exact_original_pdf_and_all_new_evidence_anchors(self):
        for id, (fingerprint, anchors) in SOURCES.items():
            record = CATALOG[id]
            self.assertEqual(record['sha256'], fingerprint)
            self.assertEqual(hashlib.sha256((ROOT/'resources'/record['originalPath']).read_bytes()).hexdigest(), fingerprint)
            book = json.loads((ROOT/'resources'/record['bookPath']).read_text())
            self.assertEqual(book['sourceHash'], fingerprint)
            blocks = {b['id']: (p['number'], b['text']) for p in book['pages'] for b in p['blocks'] if b.get('text')}
            advertised = {b for e in RESEARCH['papers'][id]['evidence'] for b in e.get('blocks', [])}
            self.assertTrue(set(anchors) <= advertised)
            for anchor in anchors:
                self.assertIn(anchor, blocks)
                self.assertTrue(blocks[anchor][1].strip())
            if id == 'qu-2025':
                self.assertEqual(blocks[anchors[0]][0], 4)
                self.assertIn('exported animal manure', blocks[anchors[0]][1])
            else:
                self.assertEqual(blocks[anchors[0]][0], 8)
                self.assertIn('Robustness of TOA results', blocks[anchors[0]][1])

    def test_lesson_answers_match_executable_examples(self):
        n = json.dumps(METHODS['nutrients'], ensure_ascii=False)
        r = lab.boundary_case()
        for value in r['gate_output_input_efficiency_percent'] + [r['combined_efficiency_percent'], r['b_animal_product_only_percent']]:
            self.assertIn(f'{value:.2f}%', n)
        for value in [r['combined_external_inputs'], r['combined_external_outputs'], r['combined_stock_change'], r['combined_residual']]:
            self.assertIn(str(value), n)
        w = json.dumps(METHODS['whole-farm'], ensure_ascii=False)
        self.assertIn('kg DM/(ha·年)', w)
        self.assertIn('kg DM/(头·年)', w)
        self.assertIn('1200', w)
        self.assertFalse(lab.units_case()['extra_animal_with_feed_import']['feasible_under_toy_constraints'])
        u = json.dumps(METHODS['uncertainty'], ensure_ascii=False)
        self.assertIn('先假定A、B在两情景都可行', u)
        self.assertIn('独立的约束演示', u)
        self.assertIn('不能当作已经找到可执行的固定方案', u)

    def test_build_contains_lessons_sources_and_offline_exercise(self):
        out = ROOT/'dist/site'
        self.assertTrue((out/'release.json').exists(), 'Run scripts/build.py first')
        built = json.loads((out/'data.json').read_text())
        docs = {d['id']: d for d in built['documents']}
        for id in PREFIXES:
            self.assertEqual(docs[id]['sections'], METHODS[id]['sections'])
            html = (out/'read'/f'{id}.html').read_text()
            self.assertIn(METHODS[id]['sections'][-1][0], html)
        source = (ROOT/'examples/model_reasoning_lab.py').read_bytes()
        self.assertEqual((out/'examples/model_reasoning_lab.py').read_bytes(), source)
        self.assertEqual(built['files']['model_reasoning_lab.py'], source.decode())
        self.assertIn('model_reasoning_lab.py', (out/'downloads/Paper-Lab-offline.html').read_text())
        self.assertIn('study-2026-10-03-model-reasoning', docs)


if __name__ == '__main__':
    unittest.main(verbosity=2)

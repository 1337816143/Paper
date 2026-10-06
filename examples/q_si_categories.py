#!/usr/bin/env python3
"""Recalculate published Cheng Table 5 -> SI Table S3, not 327 raw Q-sorts.

No dependencies. Run: python q_si_categories.py --json
Keep q_published_tables.json beside this file. Values are transcribed published
numerical facts, not synthetic participant data and not author analysis code.
"""
import argparse
from fractions import Fraction
import json
from pathlib import Path

SLOTS = [1] * 2 + [2] * 4 + [3] * 8 + [4] * 4 + [5] * 2
COUNTS = [2, 7, 4, 7]
CATEGORIES = ['provisioning', 'regulating', 'supporting', 'cultural']


def category(scores):
    """Exact bounds for n category members assigned to this fixed 20-slot grid."""
    n = len(scores)
    if n not in (2, 4, 7) or any(type(x) is not int or x not in range(1, 6) for x in scores):
        raise ValueError('Expected 2, 4 or 7 integer factor scores in 1..5')
    lo, hi = sum(SLOTS[:n]), sum(SLOTS[-n:])
    total = sum(scores)
    if not lo <= total <= hi:
        raise ValueError('Category total is not attainable in the fixed grid')
    scaled = 100 * Fraction(total - lo, hi - lo)
    return {'n': n, 'sum': total, 'meanExact': str(Fraction(total, n)),
            'minimumSum': lo, 'maximumSum': hi,
            'minimumMeanExact': str(Fraction(lo, n)), 'maximumMeanExact': str(Fraction(hi, n)),
            'scaledExact': str(scaled), 'scaled': float(scaled),
            'printed2dp': f'{float(scaled):.2f}', 'priority': scaled > 50}


def analyze(data):
    if data['categoryCounts'] != COUNTS or data['categoryOrder'] != CATEGORIES:
        raise ValueError('Category order/count differs from published Table 5')
    rows, seen, priority = [], set(), [0] * 4
    for row in data['rows']:
        if row['perspective'] in seen or sorted(row['factorScores']) != SLOTS:
            raise ValueError('Duplicate perspective or invalid complete factor array')
        seen.add(row['perspective'])
        pos, categories = 0, []
        for k, n in enumerate(COUNTS):
            value = category(row['factorScores'][pos:pos+n]);pos += n
            value.update(category=CATEGORIES[k], reported=row['reportedCategoryScores'][k])
            value['matchesPrinted'] = value['printed2dp'] == f'{value["reported"]:.2f}'
            priority[k] += value['priority'];categories.append(value)
        rows.append({'perspective': row['perspective'], 'categories': categories})
    return {'evidence': 'Published Table 5 to SI Table S3 arithmetic only; not raw-data reproduction',
            'authorRawDataReproduced': False, 'source': data['source'], 'rows': rows,
            'matchedCells': sum(c['matchesPrinted'] for r in rows for c in r['categories']),
            'totalCells': len(rows) * 4, 'strictPriorityCounts': priority}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--test', action='store_true')
    args = parser.parse_args()
    data = json.loads(Path(__file__).with_name('q_published_tables.json').read_text())
    result = analyze(data)
    if args.test:
        assert len(result['rows']) == 18 and result['matchedCells'] == result['totalCells'] == 72
        assert result['strictPriorityCounts'] == [11, 9, 4, 7]
        assert category([3, 3, 3, 3])['priority'] is False
        assert category([1, 1, 2, 2])['scaled'] == 0
        assert category([5, 5, 4, 4])['scaled'] == 100
        print('PASS 72 published cells, exact bounds, strict 50, 0 and 100; no raw-data reproduction')
    elif args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(result['evidence'])
        for row in result['rows']:
            print(row['perspective'], ' | '.join(c['printed2dp'] + (' >50' if c['priority'] else ' <=50') for c in row['categories']))
        print('Matched:', result['matchedCells'], '/', result['totalCells'], '; strict counts:', result['strictPriorityCounts'])


if __name__ == '__main__':
    main()

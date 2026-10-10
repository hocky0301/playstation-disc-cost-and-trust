import copy
import csv
import json
import math
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import unittest
from model import Segment, Response, evaluate, simple_delta, exit_break_even, information_value, from_config

class ModelTests(unittest.TestCase):
    def setUp(self):
        self.config=json.loads(Path(__file__).with_name('scenarios.json').read_text())
        self.s=[Segment('a',100,1000,2,100,.9)]
    def test_simple_threshold_zero(self):
        d=exit_break_even(1e6,40000,3000,3e8,1e8)
        self.assertAlmostEqual(simple_delta(1e6,40000,3000,3e8,1e8,d),0,places=4)
    def test_spending_threshold_zero(self):
        d=exit_break_even(1e6,40000,3000,3e8,1e8,.01)
        self.assertAlmostEqual(simple_delta(1e6,40000,3000,3e8,1e8,d,.01),0,places=4)
    def test_simple_baseline(self):
        self.assertEqual(simple_delta(10,100,0,0,0,0),0)
    def test_different_cost_only_threshold(self):
        self.assertAlmostEqual(exit_break_even(1e6,40000,600,3e8,1e8),.019704433497536922)
    def test_full_exit(self):
        self.assertEqual(simple_delta(10,100,20,40,5,1),-965)
    def test_no_denominator(self):
        self.assertIsNone(exit_break_even(10,100,20,40,5,1))
    def test_negative_threshold_not_clipped(self):
        self.assertLess(exit_break_even(10,100,1,0,100),0)
    def test_invalid_simple(self):
        for x in [float('nan'),float('inf'),-1,True]:
            with self.subTest(x=x),self.assertRaises(ValueError): simple_delta(x,100,10,0,0,0)
    def test_invalid_probability(self):
        with self.assertRaises(ValueError): simple_delta(10,100,10,0,0,1.01)
    def test_identical_policy(self):
        r=evaluate(self.s,{'a':Response(conversion_fraction=0)},years=5)
        self.assertEqual(r['npv'],0)
    def test_decomposition(self):
        for name,r in from_config(self.config).items():
            c=r['components_pv']; total=c['retained_uplift']+c['avoided_fixed']-c['exit_loss']-c['spend_loss']-c['assurance_cost']-c['transition_cost']
            self.assertAlmostEqual(total,r['npv'],places=4,msg=name)
    def test_single_year_manual(self):
        r=evaluate(self.s,{'a':Response(initial_exit=.1,spend_haircut=.1,annual_assurance_cost_per_member=10)},years=1,discount=0,avoided_fixed_annual=100,transition_cost=10)
        self.assertAlmostEqual(r['npv'],90*(.9*1200-10)-100*1000+100-10)
    def test_extra_hazard_starts_second_year(self):
        r=evaluate(self.s,{'a':Response(annual_extra_exit=.2,conversion_fraction=0)},years=2,discount=0)
        self.assertEqual(r['yearly'][0]['policy_members'],100)
        self.assertAlmostEqual(r['yearly'][1]['policy_members'],72)
    def test_natural_migration_comparator(self):
        r=evaluate(self.s,{'a':Response()},years=2,discount=0,natural_digital_migration=1)
        self.assertEqual(r['yearly'][1]['retained_uplift'],0)
        self.assertEqual(r['yearly'][1]['baseline_contribution'],90*1200)
    def test_no_policy_conversion(self):
        r=evaluate(self.s,{'a':Response(conversion_fraction=0)},years=2)
        self.assertEqual(r['components_pv']['retained_uplift'],0)
    def test_spend_scales_uplift(self):
        r=evaluate(self.s,{'a':Response(spend_haircut=1)},years=1,discount=0)
        self.assertEqual(r['yearly'][0]['policy_before_fixed'],0)
    def test_new_users_are_not_added(self):
        r=evaluate(self.s,{'a':Response()},years=5)
        self.assertEqual(r['yearly'][0]['policy_members'],100)
        self.assertLess(r['yearly'][-1]['policy_members'],100)
    def test_scale_all_counts_costs(self):
        a=evaluate(self.s,{'a':Response(initial_exit=.03)},avoided_fixed_annual=100,transition_cost=20)
        b=evaluate([Segment('a',200,1000,2,100,.9)],{'a':Response(initial_exit=.03)},avoided_fixed_annual=200,transition_cost=40)
        self.assertAlmostEqual(b['npv'],2*a['npv'])
    def test_monotonic_exit(self):
        a=evaluate(self.s,{'a':Response(initial_exit=.02)})
        b=evaluate(self.s,{'a':Response(initial_exit=.03)})
        self.assertGreater(a['npv'],b['npv'])
    def test_zero_baseline_retention(self):
        r=evaluate([Segment('a',100,1000,2,100,0)],{'a':Response()},years=2)
        self.assertEqual(r['yearly'][1]['baseline_members'],0)
    def test_duplicate_segments(self):
        with self.assertRaises(ValueError): evaluate(self.s*2,{'a':Response()})
    def test_missing_response(self):
        with self.assertRaises(ValueError): evaluate(self.s,{})
    def test_invalid_years(self):
        for y in [0,True,1.5]:
            with self.subTest(y=y),self.assertRaises(ValueError): evaluate(self.s,{'a':Response()},years=y)
    def test_invalid_response(self):
        with self.assertRaises(ValueError): evaluate(self.s,{'a':Response(annual_extra_exit=1.1)})
    def test_evpi_nonnegative(self):
        for good,bad in [(4,-3),(-1,-2),(1,2),(0,0)]:
            for p in [0,.25,.55,1]:
                self.assertGreaterEqual(information_value(good,bad,p)['evpi'],-1e-12)
    def test_no_information_value_when_same_decision(self):
        self.assertAlmostEqual(information_value(4,3,.55)['evpi'],0)
    def test_evpi_numerical_example(self):
        r=information_value(4e9,-3e9,.55,2e8)
        self.assertAlmostEqual(r['evpi']/1e9,1.35)
    def test_reproducible(self):
        self.assertEqual(from_config(self.config),from_config(self.config))

def _rounded(value, scale, places):
    """Divide by scale, then round once (half up) to the given decimal places."""
    return Decimal(repr(value / scale)).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)


class ArticleNumberTests(unittest.TestCase):
    """The model-derived numbers printed in the Zenn article, against the saved results.

    Each saved value is rounded once, directly to the digits shown in the article.
    (Natural migration 30% is 8.86; the article's first printing said 8.87, from rounding twice.)
    Money is in units of 100 million yen (oku-en); break-even rates are in percent.
    """
    OKU = 1e8
    PERCENT = 0.01

    @classmethod
    def setUpClass(cls):
        results = Path(__file__).parents[1] / 'results'
        cls.main = json.loads((results / 'results.json').read_text(encoding='utf-8'))
        cls.sens = json.loads((results / 'sensitivity.json').read_text(encoding='utf-8'))
        with (results / 'natural_migration.csv').open(encoding='utf-8', newline='') as f:
            cls.migration = {(float(r['natural_migration']), r['policy']): float(r['npv']) for r in csv.DictReader(f)}
        with (results / 'simple_frontier.csv').open(encoding='utf-8', newline='') as f:
            cls.frontier = {(float(r['uplift_pv_per_member']), float(r['incremental_exit'])): float(r['delta_pv']) for r in csv.DictReader(f)}

    def table(self):
        m, s = self.main, self.sens
        stress = m['policies']['full_stress']['components_pv']
        info = m['information_example']
        return [
            # (label, saved value, scale, decimal places, number the article should print)
            # When the article's numbers change, update this table with them.
            ('simple: nobody leaves (oku-en)', self.frontier[(3000.0, 0.0)], self.OKU, 1, '32.0'),
            ('simple: 5% leave (oku-en)', m['simple']['exit_5pct_delta'], self.OKU, 1, '10.5'),
            ('simple: 8% leave (oku-en)', m['simple']['exit_8pct_delta'], self.OKU, 1, '-2.4'),
            ('simple: break-even exit (%)', m['simple']['break_even_exit'], self.PERCENT, 2, '7.44'),
            ('simple: break-even when 1% of the rest spend less (%)', m['simple']['break_even_with_1pct_spending_loss'], self.PERCENT, 2, '6.51'),
            ('simple: break-even when uplift is 600 yen (%)', m['simple']['cost_only_break_even'], self.PERCENT, 2, '1.97'),
            ('five years: full removal, calm', m['policies']['full_calm']['npv'], self.OKU, 2, '12.49'),
            ('five years: full removal, strong reaction', m['policies']['full_stress']['npv'], self.OKU, 2, '-10.15'),
            ('five years: invest in continued use', m['policies']['full_assurance']['npv'], self.OKU, 2, '3.86'),
            ('five years: keep a small physical line', m['policies']['selective_physical']['npv'], self.OKU, 2, '2.13'),
            ('five years: investment changes no behaviour', s['assurance_without_behavior_change']['npv'], self.OKU, 2, '-17.58'),
            ('strong reaction: retained uplift', stress['retained_uplift'], self.OKU, 2, '15.56'),
            ('strong reaction: avoided fixed cost', stress['avoided_fixed'], self.OKU, 2, '4.79'),
            ('strong reaction: profit of members who left', stress['exit_loss'], self.OKU, 2, '21.87'),
            ('strong reaction: profit of reduced spending', stress['spend_loss'], self.OKU, 2, '7.13'),
            ('strong reaction: transition cost', stress['transition_cost'], self.OKU, 1, '1.5'),
            ('natural migration 0%', self.migration[(0.0, 'full_calm')], self.OKU, 2, '17.35'),
            ('natural migration 15%', self.migration[(0.15, 'full_calm')], self.OKU, 2, '12.49'),
            ('natural migration 30%', self.migration[(0.3, 'full_calm')], self.OKU, 2, '8.86'),
            ('information: adopt without information', info['adopt_without_information'], self.OKU, 1, '8.5'),
            ('information: with perfect information', info['perfect_information_value_before_cost'], self.OKU, 0, '22'),
            ('information: value of perfect information', info['evpi'], self.OKU, 1, '13.5'),
            ('information: upper bound after research cost', info['net_upper_bound_of_research'], self.OKU, 1, '11.5'),
        ]

    def test_article_numbers_match_saved_results(self):
        rows = self.table()
        self.assertEqual(len(rows), 23)
        for label, value, scale, places, printed in rows:
            with self.subTest(label):
                self.assertEqual(_rounded(value, scale, places), Decimal(printed))


if __name__=='__main__': unittest.main()

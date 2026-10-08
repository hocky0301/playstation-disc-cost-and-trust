"""Counterfactual contribution model; every scenario input is hypothetical.

Currency: JPY. Time: years after the proposed transition begins, not calendar FY.
No Sony user-level data, BOM costs, or fitted demand elasticities are used.
Core calculation uses only the Python standard library (Python >= 3.10).
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
import argparse
import csv
import json
import math


def number(value: float, name: str, low: float = 0., high: float | None = None) -> None:
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
        raise ValueError(f'{name} must be a finite number')
    if value < low or (high is not None and value > high):
        raise ValueError(f'{name} outside allowed range')


def simple_delta(n: float, baseline_ltv: float, uplift: float, fixed_pv: float,
                 transition_cost: float, exit_share: float, spend_haircut: float = 0.) -> float:
    """PV difference for a homogeneous cohort. Uplift already includes variable savings.

    exit_share: policy-induced loss relative to the counterfactual, not total churn.
    spend_haircut: proportional reduction in contribution among retained members.
    All monetary inputs except n, shares are present values for the SAME horizon.
    """
    for k,v in locals().copy().items():
        number(v,k)
    number(exit_share,'exit_share',0,1)
    number(spend_haircut,'spend_haircut',0,1)
    return n*((1-exit_share)*(1-spend_haircut)*(baseline_ltv+uplift)-baseline_ltv)+fixed_pv-transition_cost


def exit_break_even(n: float, baseline_ltv: float, uplift: float,
                    fixed_pv: float, transition_cost: float, spend_haircut: float = 0.) -> float | None:
    """Unclipped root: negative means losing even with zero exit; >1 means all-exit positive.
    None means the remaining contribution denominator is zero.
    """
    for k,v in locals().copy().items():
        number(v,k)
    number(spend_haircut,'spend_haircut',0,1)
    if n <= 0:
        raise ValueError('n must be positive')
    denominator = (1-spend_haircut)*(baseline_ltv+uplift)
    if denominator == 0:
        return None
    return 1-(baseline_ltv-(fixed_pv-transition_cost)/n)/denominator


@dataclass(frozen=True)
class Segment:
    name: str
    members: float
    margin_y1: float
    physical_units_y1: float
    contribution_uplift_per_copy: float
    baseline_retention: float

    def validate(self) -> None:
        if not self.name:
            raise ValueError('segment name cannot be empty')
        for k,v in asdict(self).items():
            if k != 'name': number(v,k)
        number(self.baseline_retention,'baseline_retention',0,1)


@dataclass(frozen=True)
class Response:
    initial_exit: float = 0.
    annual_extra_exit: float = 0.
    spend_haircut: float = 0.
    conversion_fraction: float = 1.
    annual_assurance_cost_per_member: float = 0.

    def validate(self) -> None:
        for k,v in asdict(self).items():
            number(v,k,0, None if k == 'annual_assurance_cost_per_member' else 1)


def evaluate(segments: list[Segment], responses: dict[str,Response], *, years: int = 5,
             discount: float = .08, natural_digital_migration: float = .15,
             avoided_fixed_annual: float = 0., transition_cost: float = 0.) -> dict:
    """Closed starting cohort; no new acquisitions, terminal value or hardware savings.

    Baseline natural digital migration increases its margin too. Policy claims ONLY
    the extra shift versus that year's baseline. Purchase reduction also scales
    the policy uplift, so unbought games cannot earn a conversion benefit.
    Baseline costs not changing with policy cancel out; avoided_fixed_annual is
    net incremental cash saving, not allocated overhead or gross accounting cost.
    """
    if isinstance(years,bool) or not isinstance(years,int) or years < 1:
        raise ValueError('years must be a positive integer')
    for name,value in [('discount',discount),('avoided_fixed_annual',avoided_fixed_annual),('transition_cost',transition_cost)]:
        number(value,name)
    number(natural_digital_migration,'natural_digital_migration',0,1)
    names=[s.name for s in segments]
    if not names or len(set(names)) != len(names) or set(names) != set(responses):
        raise ValueError('unique segments and exactly corresponding responses required')
    for s in segments: s.validate(); responses[s.name].validate()
    rows=[]
    for t in range(1,years+1):
        row=dict(year=t,baseline_contribution=0., policy_before_fixed=0.,
                 retained_uplift=0., exit_loss=0., spend_loss=0., assurance_cost=0.,
                 avoided_fixed=avoided_fixed_annual, baseline_members=0.,policy_members=0.)
        for s in segments:
            a=responses[s.name]
            nb=s.members*s.baseline_retention**(t-1)
            np_=nb*(1-a.initial_exit)*(1-a.annual_extra_exit)**(t-1)
            physical=s.physical_units_y1*(1-natural_digital_migration)**(t-1)
            mb=s.margin_y1+(s.physical_units_y1-physical)*s.contribution_uplift_per_copy
            u=a.conversion_fraction*physical*s.contribution_uplift_per_copy
            row['baseline_members']+=nb
            row['policy_members']+=np_
            row['baseline_contribution']+=nb*mb
            row['policy_before_fixed']+=np_*((1-a.spend_haircut)*(mb+u)-a.annual_assurance_cost_per_member)
            row['retained_uplift']+=np_*u
            row['exit_loss']+=(nb-np_)*mb
            row['spend_loss']+=np_*a.spend_haircut*(mb+u)
            row['assurance_cost']+=np_*a.annual_assurance_cost_per_member
        row['delta']=row['policy_before_fixed']-row['baseline_contribution']+avoided_fixed_annual
        row['discount_factor']=(1+discount)**(-t)
        row['discounted_delta']=row['delta']*row['discount_factor']
        rows.append(row)
    components={k:sum(x[k]*x['discount_factor'] for x in rows) for k in
                ['retained_uplift','exit_loss','spend_loss','assurance_cost','avoided_fixed']}
    components['transition_cost']=transition_cost
    npv=sum(x['discounted_delta'] for x in rows)-transition_cost
    return {'npv':npv,'components_pv':components,'yearly':rows}


def information_value(good: float, bad: float, good_probability: float, research_cost: float = 0.) -> dict:
    """Perfect-information upper bound, not an empirical probability of success.
    Alternatives: adopt with state-contingent payoff, or baseline (payoff zero).
    Payoffs and research cost are already discounted to a common point.
    """
    for k,v in [('good',good),('bad',bad)]:
        if not isinstance(v,(int,float)) or not math.isfinite(v): raise ValueError(k)
    number(good_probability,'good_probability',0,1); number(research_cost,'research_cost')
    expected=good_probability*good+(1-good_probability)*bad
    without=max(expected,0.)
    perfect=good_probability*max(good,0.)+(1-good_probability)*max(bad,0.)
    return {'adopt_without_information':expected,'best_without_information':without,
            'perfect_information_value_before_cost':perfect,
            'evpi':perfect-without,'net_upper_bound_of_research':perfect-without-research_cost}


def from_config(config: dict) -> dict:
    segments=[Segment(**x) for x in config['segments']]
    all_results={}
    for policy in config['policies']:
        params={**config['common'], **policy['parameters']}
        responses={k:Response(**v) for k,v in policy['responses'].items()}
        all_results[policy['id']]=evaluate(segments,responses,**params)
    return all_results


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,default=Path(__file__).with_name('scenarios.json'))
    parser.add_argument('--out',type=Path,default=Path(__file__).parents[1]/'results')
    args=parser.parse_args()
    config=json.loads(args.config.read_text(encoding='utf-8'))
    results=from_config(config)
    args.out.mkdir(parents=True,exist_ok=True)
    simple=dict(n=1_000_000,baseline_ltv=40_000,uplift=3_000,fixed_pv=300_000_000,transition_cost=100_000_000)
    summary={'status':'HYPOTHETICAL_SCENARIOS_NOT_SONY_FORECAST','simple_inputs':simple,
             'simple':{'break_even_exit':exit_break_even(**simple),
                       'break_even_with_1pct_spending_loss':exit_break_even(**simple,spend_haircut=.01),
                       'cost_only_break_even':exit_break_even(**{**simple,'uplift':600}),
                       'exit_5pct_delta':simple_delta(**simple,exit_share=.05),
                       'exit_8pct_delta':simple_delta(**simple,exit_share=.08)},
             'policies':results,
             'information_example':information_value(4e9,-3e9,.55,2e8)}
    (args.out/'results.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
    with (args.out/'policies.csv').open('w',newline='',encoding='utf-8') as f:
        fields=['policy','npv']+list(next(iter(results.values()))['components_pv'])
        writer=csv.DictWriter(f,fieldnames=fields); writer.writeheader()
        for name,r in results.items(): writer.writerow({'policy':name,'npv':r['npv'],**r['components_pv']})
    with (args.out/'yearly.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=['policy']+list(next(iter(results.values()))['yearly'][0]));writer.writeheader()
        for name,r in results.items():
            for row in r['yearly']: writer.writerow({'policy':name,**row})
    print(json.dumps({'simple':summary['simple'],'npv':{k:v['npv'] for k,v in results.items()},'information':summary['information_example']},indent=2))

if __name__ == '__main__': main()

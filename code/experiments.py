"""Sensitivity checks; scenario frequencies are NOT probabilities."""
from __future__ import annotations
import copy
import csv
import json
from pathlib import Path
from model import from_config, simple_delta


def run(out: Path | None = None) -> dict:
    root=Path(__file__).parents[1]
    out=out or root/'results';out.mkdir(parents=True,exist_ok=True)
    config=json.loads(Path(__file__).with_name('scenarios.json').read_text(encoding='utf-8'))
    decay=[]
    for rate in [0,.15,.30]:
        c=copy.deepcopy(config);c['common']['natural_digital_migration']=rate
        for name,r in from_config(c).items():
            decay.append({'natural_migration':rate,'policy':name,'npv':r['npv']})
    no_effect=copy.deepcopy(config)
    policy=no_effect['policies'][3]
    policy['responses']=copy.deepcopy(no_effect['policies'][2]['responses'])
    for response in policy['responses'].values():
        response['annual_assurance_cost_per_member']=120
    no_effect_result=from_config(no_effect)['full_assurance']
    grid=[]
    for u in range(0,6001,100):
        for di in range(151):
            d=di/1000
            delta=simple_delta(1e6,40000,u,3e8,1e8,d)
            grid.append({'uplift_pv_per_member':u,'incremental_exit':d,'delta_pv':delta})
    for filename,rows in [('natural_migration.csv',decay),('simple_frontier.csv',grid)]:
        with (out/filename).open('w',encoding='utf-8',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    data={'status':'ILLUSTRATIVE_SENSITIVITY_NOT_PROBABILISTIC_FORECAST',
          'assurance_without_behavior_change':no_effect_result,'grid_rows':len(grid),
          'natural_migration':decay}
    (out/'sensitivity.json').write_text(json.dumps(data,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
    return data

if __name__=='__main__':
    data=run()
    print(json.dumps({'grid_rows':data['grid_rows'],'assurance_without_behavior_change_npv':data['assurance_without_behavior_change']['npv']},indent=2))

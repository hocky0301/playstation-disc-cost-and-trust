"""Reproduce article figures from saved model outputs; no external market data.
Run: python charts.py  (requires matplotlib and numpy).
"""
from pathlib import Path
import csv
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from model import simple_delta


def render(root: Path | None = None) -> list[str]:
    root=root or Path(__file__).parents[1]
    out=root/'images/ps-disc-trust';out.mkdir(parents=True,exist_ok=True)
    results=json.loads((root/'results/results.json').read_text())
    generated=[]
    def save(fig,name):
        fig.tight_layout();fig.savefig(out/name,dpi=170,bbox_inches='tight');plt.close(fig)
        generated.append(name)
    # One figure per output, using Matplotlib default colors.
    fig,ax=plt.subplots(figsize=(8.6,5.1))
    x=np.linspace(0,.15,151)
    for u in [600,1500,3000,5000]:
        y=[simple_delta(1e6,40000,u,3e8,1e8,d)/1e9 for d in x]
        ax.plot(x*100,y,label=f'Uplift PV per retained member = JPY {u:,}')
    ax.axhline(0,linestyle='--',linewidth=1)
    ax.set(xlabel='Incremental exit caused by policy (%)',ylabel='Incremental PV (JPY billion)',
           title='When does removal stop paying?\nHypothetical cohort: 1 million members; baseline LTV JPY 40,000')
    ax.legend(fontsize=8);ax.grid(alpha=.2);save(fig,'break_even.png')
    fig,ax=plt.subplots(figsize=(8.6,5.1))
    labels={'full_calm':'Full removal / calm response','full_stress':'Full removal / strong response',
            'full_assurance':'Full removal / assurance investment','selective_physical':'Selective physical supply'}
    for name,label in labels.items():
        rows=results['policies'][name]['yearly']
        ax.plot([r['year'] for r in rows],[r['delta']/1e9 for r in rows],marker='o',label=label)
    ax.axhline(0,linestyle='--',linewidth=1)
    ax.set(xlabel='Year after transition starts',ylabel='Annual contribution difference (JPY billion)',
           title='Annual change versus natural digital migration\nHypothetical scenarios; upfront transition costs excluded from this plot')
    ax.set_xticks(range(1,6));ax.legend(fontsize=8);ax.grid(alpha=.2);save(fig,'yearly.png')
    fig,ax=plt.subplots(figsize=(8.6,5.1))
    c=results['policies']['full_stress']['components_pv']
    names=['Retained-user channel uplift','Avoided fixed costs','Lost contribution from exit','Lower spending among retained users','Transition cost','Net difference']
    vals=[c['retained_uplift'],c['avoided_fixed'],-c['exit_loss'],-c['spend_loss'],-c['transition_cost'],results['policies']['full_stress']['npv']]
    bars=ax.barh(names,[v/1e9 for v in vals])
    ax.axvline(0,linestyle='--',linewidth=1)
    for bar,v in zip(bars,vals):
        ax.annotate(f'{v/1e9:+.3f}',(v/1e9,bar.get_y()+bar.get_height()/2),xytext=(5 if v>=0 else -5,0),
                    textcoords='offset points',ha='left' if v>=0 else 'right',va='center',fontsize=9)
    ax.set_xlim(-2.7,2.15)
    ax.set(xlabel='Five-year discounted contribution (JPY billion)',title='Full removal / strong response: what drives the loss?\nAssumed inputs, not Sony financial results')
    ax.invert_yaxis();save(fig,'bridge.png')
    fig,ax=plt.subplots(figsize=(8.6,5.1))
    u=np.arange(0,6001,100);d=np.arange(151)/1000
    z=np.array([[simple_delta(1e6,40000,float(ui),3e8,1e8,float(di))/1e9 for di in d] for ui in u])
    im=ax.imshow(z,origin='lower',aspect='auto',extent=[0,15,0,6000])
    # The dashed curve gives the analytic break-even boundary, not a fitted estimate.
    boundary=(u+200)/(40000+u)*100
    ax.plot(boundary,u,linestyle='--',linewidth=2,label='Break-even boundary')
    ax.set(xlabel='Incremental exit (%)',ylabel='Uplift PV per retained member (JPY)',
           title='A decision boundary, not a probability forecast\nHypothetical simple model; no spending haircut')
    fig.colorbar(im,ax=ax,label='Incremental PV (JPY billion)');ax.legend(fontsize=8);save(fig,'frontier.png')
    fig,ax=plt.subplots(figsize=(8.6,5.1))
    with (root/'results/natural_migration.csv').open() as f: rows=list(csv.DictReader(f))
    for name,label in labels.items():
        rr=[r for r in rows if r['policy']==name]
        ax.plot([float(r['natural_migration'])*100 for r in rr],[float(r['npv'])/1e9 for r in rr],marker='o',label=label)
    ax.axhline(0,linestyle='--',linewidth=1)
    ax.set(xlabel='Natural annual digital migration (%)',ylabel='Five-year incremental PV (JPY billion)',
           title='How much transition would happen without the ban?\nAssumed behavior and fixed-cost savings held unchanged')
    ax.legend(fontsize=8);ax.grid(alpha=.2);save(fig,'natural_migration.png')
    return generated

if __name__=='__main__': print('\n'.join(render()))

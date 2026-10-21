"""Optional OR-Tools9.15.6755 binary-model control; replay does not import this."""
import copy
import json
from pathlib import Path
from ortools.sat.python import cp_model
from loss_closure import cut_frontiers
ROOT=Path(__file__).resolve().parents[2]

def solve(g,budget,forced=()):
    ns=g['nodes'];idx={n['id']:i for i,n in enumerate(ns)}
    m=cp_model.CpModel();live=[m.new_bool_var('L'+str(i)) for i in range(len(ns))];replay=[m.new_bool_var('R'+str(i)) for i in range(len(ns))]
    for i,n in enumerate(ns):
        if not n['recomputable']:m.add(replay[i]==0)
        for d in n['deps']:
            if d in idx:m.add(replay[i]<=live[idx[d]]+replay[idx[d]])
        for d in n['backward_requires']:
            if d in idx:m.add(live[idx[d]]+replay[idx[d]]>=1)
    for d in set(g['outputs'])|set(forced):m.add(live[idx[d]]==1)
    m.add(sum(n['cost']*replay[i] for i,n in enumerate(ns))<=budget)
    m.minimize(sum(n['bytes']*live[i] for i,n in enumerate(ns)))
    solver=cp_model.CpSolver();solver.parameters.num_search_workers=1;solver.parameters.random_seed=20261021;solver.parameters.max_time_in_seconds=10
    status=solver.solve(m)
    if status!=cp_model.OPTIMAL:raise RuntimeError('control did not complete: '+solver.status_name(status))
    return sum(v['bytes'] for v in g['inputs'])+sum(n['bytes']*solver.value(live[i]) for i,n in enumerate(ns))

def main():
    rows=json.loads((ROOT/'records/working-frontiers.json').read_text());cache={};count=0
    for row in rows:
        g=json.loads((ROOT/'benchmarks/graphs'/str(row['graph']+'.json')).read_text());budget=row['budget']
        if row['graph'] not in cache:cache[row['graph']]=cut_frontiers(g,max(r['budget'] for r in rows if r['graph']==row['graph']))
        expected=cache[row['graph']]
        assert solve(g,budget)==min(m for m,c in expected['loss']['frontier'] if c<=budget);count+=1
        needed={d for n in g['nodes'] for d in n['backward_requires']};ancestors={n['id']:set() for n in g['inputs']}
        for v in g['nodes']:
            seen={v['id']}
            for d in v['deps']:seen|=ancestors[d]
            ancestors[v['id']]=seen
            sub=copy.deepcopy(g);sub['nodes']=[copy.deepcopy(n) for n in g['nodes'] if n['id'] in seen];sub['outputs']=[v['id']];sub['nodes'][-1]['backward_requires']=sorted(needed&seen)
            actual=solve(sub,budget,[d for d in v['deps'] if d in seen])
            assert actual==min(m for m,c in expected['first-forward:'+v['id']]['frontier'] if c<=budget)
            count+=1
    print(json.dumps(dict(status='PASS',fixed_rows=len(rows),cut_comparisons=count,solver='OR-Tools9.15.6755 CP-SAT',scope='same necessary relaxation; integer optimum status required; author-team control')))

if __name__=='__main__':main()

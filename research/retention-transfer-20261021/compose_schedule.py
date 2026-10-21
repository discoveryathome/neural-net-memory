"""Compose exact one-block schedules with all three block-entry checkpoints.

No global optimum claim: earlier blocks keep only their output; the last block
uses an exact full-training regional plan; backward blocks use exact tail plans.
The frozen full-graph verifier is the final acceptance gate.
"""
import argparse,copy,json,time
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(HERE))
from regional_exact import solve,Limited
from verifier import digest,load,verify
from search import certificate

def forward_only(g):
    nodes={v['id']:v for v in g['nodes']};order=list(nodes)
    for name in list(order):
        if name.endswith('_v'):
            order.remove(name);order.insert(order.index(name[:-1]+'probs')+1,name)
    live=set();acts=[]
    for at,name in enumerate(order):
        acts.append(dict(op='forward',node=name));live.add(name)
        needed=set(g['outputs'])
        for future in order[at+1:]:needed.update(nodes[future]['deps'])
        for old in sorted(live-needed):acts.append(dict(op='drop',node=old));live.remove(old)
    return acts

def compose(g,cap,budget):
    if digest(g)!='7d60aaf32c25d4d000872f9d317cdb0cbc71c929307eb69faf7e974c795d5854':raise ValueError('bounded construction requires the frozen four-block graph')
    u=g['inputs'][0]['bytes'];local=copy.deepcopy(g);local['nodes']=local['nodes'][:14];local['outputs']=['b0_residual2'];local['id']='regional-transformer-control'
    if cap<13*u:raise ValueError('this all-entry-checkpoint construction requires at least 13 chunks')
    acts=[];live=set();rows=[]
    def add(action,block):
        a=dict(action)
        if 'node' in a:a['node']=a['node'].replace('b0_',f'b{block}_',1)
        acts.append(a)
        if a['op']=='forward':
            if a['node'] in live:raise ValueError('regional composition overwrites live value')
            live.add(a['node'])
        elif a['op']=='drop':
            if a['node'] not in live:raise ValueError('regional composition drops absent value')
            live.remove(a['node'])
    def cleanup(block):
        for n in sorted(live.copy()):
            if n.startswith(f'b{block}_'):add(dict(op='drop',node=n),block)
    fw=forward_only(local)
    for block in range(3):
        for action in fw:add(action,block)
    lcap=cap-3*u
    last=solve(local,lcap,budget,states=750000,seconds=30)
    if last is None:raise ValueError('no last-block regional plan under cap')
    for a in last['actions']:add(a,3)
    rows.append(dict(block=3,kind='full-training',local_cap=lcap,recompute_cost=last['claims']['recompute_cost'],states=last['metadata']['states']))
    cleanup(3)
    for block in (2,1,0):
        source=f'b{block}_residual2'
        if source in live:add(dict(op='drop',node=source),block)
        lcap=cap-block*u
        plan=solve(local,lcap,budget,states=750000,seconds=30,backward_only=True)
        if plan is None:raise ValueError('no regional backward tail under cap')
        for action in plan['actions'][plan['metadata']['prefix_actions']:]:add(action,block)
        rows.append(dict(block=block,kind='backward-tail',local_cap=lcap,recompute_cost=plan['claims']['recompute_cost'],states=plan['metadata']['states']))
        cleanup(block)
    total=sum(row['recompute_cost'] for row in rows)
    if total>budget:raise ValueError(f'regional construction costs {total}, above fixed budget {budget}')
    c=certificate(g,acts,budget,'exact-region-composition')
    if c['claims']['peak_bytes']>cap:raise ValueError('composed schedule exceeded global cap')
    return acts,dict(global_optimal=False,scope='fixed block order; all block-entry checkpoints retained; exact one-block regions',regions=rows)

def main():
    p=argparse.ArgumentParser();p.add_argument('--graph',required=True);p.add_argument('--cap',required=True,type=int);p.add_argument('--budget',required=True,type=int);p.add_argument('--out',required=True);a=p.parse_args();g=load(a.graph);t=time.perf_counter()
    acts,stats=compose(g,a.cap,a.budget);stats['seconds']=time.perf_counter()-t
    c=certificate(g,acts,a.budget,'exact-region-composition',stats);verify(g,c,a.budget);Path(a.out).write_text(json.dumps(c,indent=2)+'\n');print(json.dumps(dict(**c['claims'],**stats)),flush=True)
if __name__=='__main__':main()

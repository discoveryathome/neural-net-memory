"""Pinned transformer composition using exact one-block subproblems.

This extends the prior retention-transfer construction to the frozen 1/2/4 block
suite. Earlier checkpoints are charged in global memory. No global optimum claim.
"""
import argparse, copy, json, sys, time
from pathlib import Path
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[1]
sys.path[:0]=[str(ROOT),str(HERE)]
from regional_exact import solve
from verifier import digest, load, verify
from search import certificate
PINNED={
 'transformer-b1-t32':'2d2cab8d86ee8d6397bb33c363b826908dbfa204309a64f7882ca106186068fc',
 'transformer-b2-t64':'49253c00a0941d94630e5323343af6e2d19e7317f26864fc19e01bc782bc638b',
 'transformer-b4-t128':'7d60aaf32c25d4d000872f9d317cdb0cbc71c929307eb69faf7e974c795d5854',
}
def forward_only(g,keep=()):
 nodes={v['id']:v for v in g['nodes']};order=list(nodes)
 for name in list(order):
  if name.endswith('_v'):
   order.remove(name);order.insert(order.index(name[:-1]+'probs')+1,name)
 live=set();actions=[]
 for at,name in enumerate(order):
  actions.append(dict(op='forward',node=name));live.add(name)
  needed=set(g['outputs'])|set(keep)
  for future in order[at+1:]:needed.update(nodes[future]['deps'])
  for old in sorted(live-needed):actions.append(dict(op='drop',node=old));live.remove(old)
 return actions

def compose(g,cap,budget,states=220000,seconds=15,retained=None):
 if digest(g)!=PINNED.get(g['id']):raise ValueError('requires unchanged frozen transformer graph')
 blocks=len(g['nodes'])//14;unit=g['inputs'][0]['bytes'];local=copy.deepcopy(g)
 local['nodes']=local['nodes'][:14];local['outputs']=['b0_residual2'];local['id']=g['id']+'-one-block-region'
 retained=[[] for _ in range(blocks-1)] if retained is None else retained
 if len(retained)!=blocks-1:raise ValueError('one retained set is required per earlier block')
 sizes={v['id']:v['bytes'] for v in local['nodes']}
 for keep in retained:
  if len(set(keep))!=len(keep) or any(n not in sizes or n=='b0_residual2' for n in keep):raise ValueError('invalid retained activation set')
 cached_bytes=[sum(sizes[n] for n in keep) for keep in retained]
 actions=[];live=set();rows=[]
 def add(action,block):
  a=dict(action)
  if 'node' in a:a['node']=a['node'].replace('b0_',f'b{block}_',1)
  actions.append(a)
  if a['op']=='forward':
   if a['node'] in live:raise ValueError('regional composition overwrites live value')
   live.add(a['node'])
  elif a['op']=='drop':
   if a['node'] not in live:raise ValueError('regional composition drops absent value')
   live.remove(a['node'])
 def cleanup(block):
  for n in sorted(live.copy()):
   if n.startswith(f'b{block}_'):add(dict(op='drop',node=n),block)
 for block in range(blocks-1):
  for action in forward_only(local,retained[block]):add(action,block)
 for block in reversed(range(blocks)):
  full=block==blocks-1; lcap=cap-block*unit-sum(cached_bytes[:block])
  if not full:
   source=f'b{block}_residual2'
   if source in live:add(dict(op='drop',node=source),block)
  plan=solve(local,lcap,budget,states=states,seconds=seconds,backward_only=not full,initial_live=() if full else retained[block])
  if plan is None:raise ValueError(f'no regional plan for block {block}')
  for a in plan['actions'][plan['metadata']['prefix_actions']:]:add(a,block)
  rows.append(dict(block=block,kind='full-training' if full else 'backward-tail',local_cap=lcap,recompute_cost=plan['claims']['recompute_cost'],states=plan['metadata']['states'],retained=[] if full else retained[block]))
  cleanup(block)
 total=sum(row['recompute_cost'] for row in rows)
 if total>budget:raise ValueError(f'regional construction costs {total}, above fixed budget {budget}')
 c=certificate(g,actions,budget,'exact-region-composition-round2')
 if c['claims']['peak_bytes']>cap:raise ValueError('composed schedule exceeded global cap')
 return actions,dict(global_optimal=False,scope='fixed block order; all block-entry checkpoints and chosen local activations retained; exact one-block regions',regions=rows)

def main():
 p=argparse.ArgumentParser();p.add_argument('--graph',required=True);p.add_argument('--cap',required=True,type=int);p.add_argument('--budget',required=True,type=int);p.add_argument('--out',required=True);a=p.parse_args();g=load(a.graph);t=time.perf_counter()
 acts,stats=compose(g,a.cap,a.budget);stats['seconds']=time.perf_counter()-t
 c=certificate(g,acts,a.budget,'exact-region-composition-round2',stats);verify(g,c,a.budget);Path(a.out).write_text(json.dumps(c,indent=2)+'\n');print(json.dumps(dict(**c['claims'],**stats)),flush=True)
if __name__=='__main__':main()

"""Tiny exact positive control: a saved intermediate may enable useful pre-drop forwarding."""
import hashlib,heapq,json,sys,time,os
from pathlib import Path
PACKAGE=Path(__file__).resolve().parent;P=Path(os.environ.get('NATIVE_PROOF_OUT',str(PACKAGE/'generated')));P.mkdir(exist_ok=True);sys.path.insert(0,str(PACKAGE.parents[1]))
from verifier import validate_graph,verify
from search import certificate

g=dict(model='activation-memory/v1',id='mandatory-drop-prefetch-control',inputs=[dict(id='x',bytes=1)],outputs=['c'],nodes=[
 dict(id='a',deps=['x'],bytes=1,cost=10,backward_cost=1,backward_requires=['x'],recomputable=True),
 dict(id='b',deps=['a'],bytes=1,cost=1,backward_cost=1,backward_requires=['b'],recomputable=True),
 dict(id='c',deps=['b'],bytes=1,cost=1,backward_cost=1,backward_requires=['b'],recomputable=True)])
validate_graph(g);ns=g['nodes'];dep=[0,1,2];req=[0,2,2];children=[2,4,0]

def exact(initial,chosen,immediate=False):
 start=(initial,0,False,False);prefix=[]
 if immediate:start=(initial^chosen,0,True,False);prefix=[dict(op='drop',node=ns[chosen.bit_length()-1]['id'])]
 best={start:0};parent={start:None};queue=[(0,start)]
 while queue:
  cost,state=heapq.heappop(queue)
  if best[state]!=cost:continue
  live,done,dropped,phase=state
  if phase and done==7:
   actions=[];at=state
   while parent[at] is not None:
    before,action=parent[at];actions.append(action);at=before
   return cost,prefix+list(reversed(actions)),len(best)
  moves=[]
  if not phase and dropped and live&4:moves.append(((live,done,dropped,True),0,dict(op='loss')))
  for i,node in enumerate(ns):
   bit=1<<i;name=node['id']
   if live&bit:moves.append(((live^bit,done,dropped or bit==chosen,phase),0,dict(op='drop',node=name)))
   elif live&dep[i]==dep[i] and 1+(live|bit).bit_count()<=4:moves.append(((live|bit,done,dropped,phase),node['cost'],dict(op='forward',node=name)))
   if phase and not done&bit and done&children[i]==children[i] and live&req[i]==req[i]:moves.append(((live,done|bit,dropped,phase),0,dict(op='backward',node=name)))
  for target,extra,action in moves:
   new=cost+extra
   if new>=best.get(target,10**20):continue
   best[target]=new;parent[target]=(state,action);heapq.heappush(queue,(new,target))
 raise AssertionError('control unexpectedly infeasible')

rows=[]
for name,initial,chosen,expected,immediate_expected in [('intermediate',1,1,2,12),('output',4,4,12,12)]:
 cost,actions,states=exact(initial,chosen);early,_,_=exact(initial,chosen,True)
 assert (cost,early)==(expected,immediate_expected)
 prefix=[dict(op='forward',node=v['id']) for v in ns]+[dict(op='drop',node=v['id']) for i,v in enumerate(ns) if not initial>>i&1]
 cert=certificate(g,prefix+actions,100,'mandatory-drop-positive-control',dict(scope='tiny control only; all first forwards precede the cut; chosen value must drop before loss'))
 assert verify(g,cert,100)['recompute_cost']==cost
 (P/f'{name}-drop-control.json').write_text(json.dumps(cert,indent=2)+'\n')
 rows.append(dict(control=name,late_drop_minwork=cost,immediate_drop_minwork=early,states=states,actions_after_cut=actions))
out=dict(status='PASS',source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),scope='exact tiny arbitrary-drop oracle and unchanged-verifier accepted certificates; initial removal overcharges an intermediate but is exact for output without own consumers',rows=rows)
(P/'drop-prefetch-falsifier.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))

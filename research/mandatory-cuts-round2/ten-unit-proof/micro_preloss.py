"""Explicit preloss graph with all individual drops, no macro normalizations.

The local output-demand and terminal/backward distances lower-bound the owned
continuation work after each state. A surviving loss boundary is OPEN, not a
legal full witness. Exhaustion excludes only the separately justified favorable
critical-cut relaxation. The accompanying cut mapping justifies the global fixed-cap conclusion.
"""
from array import array
from functools import lru_cache
from pathlib import Path
import argparse,hashlib,heapq,itertools,json,sys,time
p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--pdb-dir',type=Path,required=True);p.add_argument('--budget',type=int,required=True);a=p.parse_args()
sys.path.insert(0,str(a.repo))
from verifier import load,digest
G=load(a.repo/'benchmarks/graphs/transformer-b2-t64.json');assert digest(G)=='49253c00a0941d94630e5323343af6e2d19e7317f26864fc19e01bc782bc638b'
ns=G['nodes'];idx={v['id']:i for i,v in enumerate(ns)};unit=G['inputs'][0]['bytes'];cap=10*unit
mask=lambda names:sum(1<<idx[n] for n in names if n in idx)
dep=[mask(v['deps']) for v in ns];allseen=(1<<26)-1;forced=(1<<24)|(1<<25)
closure=forced
for i in reversed(range(28)):
 if closure>>i&1:closure|=dep[i]
assert closure==allseen and ns[24]['id']=='b1_up' and ns[25]['id']=='b1_gelu'
sizes=[v['bytes'] for v in ns]
@lru_cache(maxsize=None)
def memory(live):
 return sum(v['bytes'] for v in G['inputs'])+sum(sizes[i] for i in range(28) if live>>i&1)
def read(stem):
 m=load(a.pdb_dir/(stem+'.json'));assert m['full_graph_sha256']==digest(G) and m['cap_bytes']==cap
 raw=(a.pdb_dir/m['binary_file']).read_bytes();assert hashlib.sha256(raw).hexdigest()==m['binary_sha256'];v=array('I');v.frombytes(raw)
 if sys.byteorder!='little':v.byteswap()
 return m,v
bm,back=read('b2-backward-pdb-cap10');dm,demand=read('b2-output-demand-pdb-cap10');tm,terminal=read('b2-terminal-phase-pdb-cap10');cu=bm['cost_unit'];assert dm['cost_unit']==cu==tm['cost_unit'];zero=bm['done_masks'].index(0)*4096;INF=(1<<32)-1
def lower(live,phase,loss=False):
 first=demand[live&16383]
 second=back[zero+((live>>14)&4095)] if loss else terminal[phase*8192+((live>>14)&8191)]
 return None if first==INF or second==INF else (int(first)+int(second))*cu
options=[i for i in range(26) if not(forced>>i&1) and sizes[i]==unit]
assert len(options)==18 and memory(forced)==9*unit
seeds=[forced]+[forced|(1<<i) for i in options]
best={};queue=[];pruned=0
for live in seeds:
 h=lower(live,0)
 if h is None or h>a.budget:pruned+=1;continue
 best[live]=0;heapq.heappush(queue,(0,live))
started=time.monotonic();expanded=generated=boundaries=0;min_boundary=None;status='EXHAUSTED';witness=None
while queue:
 cost,key=heapq.heappop(queue)
 if cost!=best[key]:continue
 live=key&((1<<28)-1);phase=key>>28;expanded+=1
 if expanded>500000 or time.monotonic()-started>30:status='LIMIT';break
 moves=[]
 for i,v in enumerate(ns):
  bit=1<<i
  if live&bit:moves.append((live^bit,phase,0))
  elif live&dep[i]==dep[i] and memory(live|bit)<=cap and (i!=27 or phase):
   if i==27:
    boundaries+=1;h=lower(live|bit,phase,True);total=None if h is None else cost+h
    if total is not None:min_boundary=total if min_boundary is None else min(min_boundary,total)
    if total is not None and total<=a.budget:status='OPEN_LOSS_BOUNDARY';witness=dict(cost=cost,lower=h,live=live|bit,phase=phase)
    continue
   first=i==26 and phase==0;moves.append((live|bit,1 if first else phase,0 if first else v['cost']))
 for nxt,np,extra in moves:
  generated+=1;value=cost+extra;target=nxt|(np<<28)
  if value>=best.get(target,10**100):continue
  h=lower(nxt,np)
  if h is None or value+h>a.budget:pruned+=1;continue
  best[target]=value;heapq.heappush(queue,(value,target))
 if status=='OPEN_LOSS_BOUNDARY':break
result=dict(status=status,budget=a.budget,cap_bytes=cap,seeds=len(seeds),states=len(best),expanded=expanded,generated=generated,pruned=pruned,loss_boundaries=boundaries,minimum_boundary_total=min_boundary,open_boundary=witness,seconds=time.monotonic()-started,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),graph_sha256=digest(G),table_sha256=dict(backward=bm['binary_sha256'],demand=dm['binary_sha256'],terminal=tm['binary_sha256']),scope='All one-node drops and legal old forwards; favorable critical-cut initial states; charged old work and free first terminal forwards; exact local distances supply disjoint continuation lower bounds.')
print(json.dumps(result,sort_keys=True),flush=True)

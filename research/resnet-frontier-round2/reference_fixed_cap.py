"""Independent generic explicit-state fixed-cap Dijkstra, no chain normalization."""
import heapq,time,sys
from pathlib import Path
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R))
from verifier import validate_graph,load
class Limited(RuntimeError):pass
def solve(g,cap,budget,limit=200000,seconds=60):
 validate_graph(g);ns=g['nodes'];n=len(ns);idx={x['id']:i for i,x in enumerate(ns)}
 def mask(names):return sum(1<<idx[x] for x in names if x in idx)
 dep=[mask(v['deps']) for v in ns];req=[mask(v['backward_requires']) for v in ns]
 children=[sum(1<<j for j,v in enumerate(ns) if x['id'] in v['deps']) for x in ns]
 fixed=sum(v['bytes'] for v in g['inputs']);full=(1<<n)-1;outputs=mask(g['outputs'])
 mem={0:fixed};costs={0:0}
 def value(m,cache,field,base):
  if m in cache:return cache[m]
  original=m;v=base
  while m:
   b=m&-m;v+=ns[b.bit_length()-1][field];m^=b
  cache[original]=v;return v
 def memory(m):return value(m,mem,'bytes',fixed)
 def work(m):return value(m,costs,'cost',0)
 remaining={}
 def required(done):
  if done not in remaining:
   remaining[done]=0
   for i,r in enumerate(req):
    if not(done>>i&1):remaining[done]|=r
  return remaining[done]
 start=(0,0,0,False);best={start:0};queue=[(0,start)];expanded=0;t=time.monotonic()
 while queue:
  cost,state=heapq.heappop(queue)
  if cost!=best[state]:continue
  if time.monotonic()-t>seconds:raise Limited('time cap')
  live,seen,done,phase=state;expanded+=1
  if phase and done==full:return cost,dict(states=len(best),expanded=expanded,seconds=time.monotonic()-t)
  moves=[]
  if not phase and seen==full and live&outputs==outputs:moves.append(((live,seen,done,True),0))
  for i,v in enumerate(ns):
   bit=1<<i
   if live&bit:moves.append(((live^bit,seen,done,phase),0))
   elif live&dep[i]==dep[i] and (not(seen&bit) or v['recomputable']) and (seen&bit or not phase):
    if memory(live|bit)<=cap:moves.append(((live|bit,seen|bit,done,phase),v['cost'] if seen&bit else 0))
   if phase and not(done&bit) and done&children[i]==children[i] and live&req[i]==req[i]:
    moves.append(((live,seen,done|bit,phase),0))
  for target,extra in moves:
   new=cost+extra
   if new>budget or new>=best.get(target,10**100):continue
   tl,ts,td,tp=target
   if new+work(required(td)&ts&~tl)>budget:continue
   if target not in best and len(best)>=limit:raise Limited('state cap')
   best[target]=new;heapq.heappush(queue,(new,target))
 return None,dict(states=len(best),expanded=expanded,seconds=time.monotonic()-t)

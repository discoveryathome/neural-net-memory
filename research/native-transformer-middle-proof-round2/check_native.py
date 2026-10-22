"""Independent arbitrary-drop, unnormalized fixed-order oracle for native search."""
import hashlib,heapq,itertools,json,random,subprocess,time,sys,resource,os
from pathlib import Path
P=Path(__file__).resolve().parent;OUT=Path(os.environ.get('NATIVE_PROOF_OUT',str(P/'generated')));sys.path.insert(0,str(P.parents[1]))
from verifier import validate_graph

def oracle(g,cap,budget,order,start):
 ns=g['nodes'];n=len(ns);idx={v['id']:i for i,v in enumerate(ns)};full=(1<<n)-1
 def mask(xs):return sum(1<<idx[x] for x in xs if x in idx)
 dep=[mask(v['deps']) for v in ns];req=[mask(v['backward_requires']) for v in ns]
 child=[mask([w['id'] for w in ns if v['id'] in w['deps']]) for v in ns]
 mem=[sum(v['bytes'] for v in g['inputs'])]*(1<<n)
 for bits in range(1,1<<n):
  bit=bits&-bits;mem[bits]=mem[bits^bit]+ns[bit.bit_length()-1]['bytes']
 orderidx=[idx[x] for x in order];out=mask(g['outputs'])
 live,done,m=start;seen=sum(1<<x for x in orderidx[:min(m,n)])
 first=(live,seen,done,m==n+1)
 if mem[live]>cap:return None,0
 queue=[(0,first)];best={first:0};expanded=0
 while queue:
  cost,state=heapq.heappop(queue)
  if best[state]!=cost:continue
  live,seen,done,phase=state;expanded+=1
  if phase and done==full:return cost,expanded
  moves=[]
  if not phase and seen==full and live&out==out:moves.append(((live,seen,done,True),0))
  for i,v in enumerate(ns):
   bit=1<<i
   if live&bit:moves.append(((live^bit,seen,done,phase),0))
   elif live&dep[i]==dep[i] and (seen&bit or not phase):
    repeat=bool(seen&bit)
    permitted=(not repeat and orderidx[seen.bit_count()]==i) or (repeat and v['recomputable'])
    if permitted and mem[live|bit]<=cap:moves.append(((live|bit,seen|bit,done,phase),v['cost'] if repeat else 0))
   if phase and not(done&bit) and done&child[i]==child[i] and live&req[i]==req[i]:
    moves.append(((live,seen,done|bit,phase),0))
  for target,extra in moves:
   new=cost+extra
   if new>budget or new>=best.get(target,10**100):continue
   assert len(best)<200000,'oracle limit'
   best[target]=new;heapq.heappush(queue,(new,target))
 return None,expanded

def native(g,cap,budget,order,start):
 ns=g['nodes'];n=len(ns);idx={v['id']:i for i,v in enumerate(ns)}
 def mask(xs):return sum(1<<idx[x] for x in xs if x in idx)
 lines=[f'{n} {sum(v["bytes"] for v in g["inputs"])} {cap} {budget} 200000 20 1 0']
 for v in ns:
  children=mask([w['id'] for w in ns if v['id'] in w['deps']])
  lines.append(f'{v["id"]} {v["bytes"]} {v["cost"]} {mask(v["deps"])} {mask(v["backward_requires"])} {children} {int(v["recomputable"])}')
 lines+=[' '.join(str(idx[x]) for x in order),str(mask(g['outputs'])),'1',f'{start[0]} {start[1]} {start[2]} 0','0 0 0','0 0']
 path=OUT/'native-control.input';path.write_text('\n'.join(lines)+'\n')
 result=subprocess.run([str(OUT/'native_search'),str(path)],capture_output=True,text=True,timeout=25)
 assert result.returncode==0,result.stderr
 out=json.loads(result.stdout);assert out['status'] in ['FEASIBLE','EXHAUSTED_FIXED_ORDER'],out
 return out.get('cost'),out
rng=random.Random(0x815a77d1);started=time.monotonic();total=0;maxstates=0;cases=[]
for fixture in range(80):
 ns=[];anc={'x':{'x'},'y':{'y'}}
 for i in range(1+fixture%7):
  name='n'+str(i);names=['x','y']+[x['id'] for x in ns]
  deps=rng.sample(names,rng.randint(1,min(3,len(names))));anc[name]={name}
  for d in deps:anc[name]|=anc[d]
  req=rng.sample(sorted(anc[name]),rng.randint(0,min(3,len(anc[name]))))
  ns.append(dict(id=name,deps=deps,bytes=rng.randint(1,4),cost=rng.randint(1,6),backward_cost=1,backward_requires=req,recomputable=rng.randrange(5)>0))
 used={d for v in ns for d in v['deps']}
 g=dict(model='activation-memory/v1',id='native-control-'+str(fixture),inputs=[dict(id='x',bytes=1),dict(id='y',bytes=2)],nodes=ns,outputs=[v['id'] for v in ns if v['id'] not in used]);validate_graph(g)
 n=len(ns);idx={v['id']:i for i,v in enumerate(ns)}
 order=[];remaining=set(idx)
 while remaining:
  ready=sorted(v for v in remaining if all(d not in remaining for d in ns[idx[v]]['deps']))
  v=rng.choice(ready);order.append(v);remaining.remove(v)
 child=[sum(1<<j for j,w in enumerate(ns) if v['id'] in w['deps']) for v in ns]
 ideals=[d for d in range(1<<n) if all(not(d>>i&1) or d&child[i]==child[i] for i in range(n))]
 cap=rng.randint(6,14);valid=[m for m in range(1<<n) if 3+sum(v['bytes'] for i,v in enumerate(ns) if m>>i&1)<=cap]
 start=(rng.choice(valid),rng.choice(ideals),n+1)
 partial_m=rng.randrange(n+1);partial_seen=sum(1<<idx[v] for v in order[:partial_m])
 partial=(rng.choice([live for live in valid if live&~partial_seen==0]),0,partial_m)
 for begin in [(0,0,0),start,partial]:
  for budget in [0,7,20]:
   expected,count=oracle(g,cap,budget,order,begin)
   actual,stats=native(g,cap,budget,order,begin)
   assert expected==actual,(fixture,cap,budget,begin,expected,actual,g,stats)
   total+=1;maxstates=max(maxstates,count);cases.append(dict(fixture=fixture,cap=cap,budget=budget,start=begin,cost=actual,oracle_expanded=count,native_states=stats['states']))
out=dict(status='PASS',comparisons=total,max_oracle_expanded=maxstates,
 source_sha256=hashlib.sha256((P/'native_search.cpp').read_bytes()).hexdigest(),
 binary_sha256=hashlib.sha256((OUT/'native_search').read_bytes()).hexdigest(),
 seconds=time.monotonic()-started,maxrss_children_bytes=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,cases=cases,
 scope='random legal fixed first-forward orders; fresh, arbitrary valid postloss and partial preloss states; full arbitrary-drop unnormalized oracle; no global transformer proof by itself')
(OUT/'native-differential-results.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k!='cases'}),flush=True)

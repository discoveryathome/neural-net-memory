"""Check recursive region bounds against four frozen legal continuations.

This is a portable harness for the existing 1,130-state control. It checks
each actual region-minimum case against the separately charged work of its
own block, as well as the minimum over all cases against total remaining
work. Dependencies: standard library and the unchanged repository verifier.
"""
from array import array
from pathlib import Path
import argparse
import hashlib
import itertools
import json
import sys

p=argparse.ArgumentParser()
p.add_argument('--repo',required=True,type=Path)
p.add_argument('--pdb-dir',required=True,type=Path)
p.add_argument('--cert-dir',required=True,type=Path)
args=p.parse_args()
R=args.repo.resolve();out=args.pdb_dir.resolve()
sys.path.insert(0,str(R))
from verifier import load,digest,verify
from search import certificate
def event(record):
 print(json.dumps(record,sort_keys=True),flush=True)
G=load(R/'benchmarks/graphs/transformer-b4-t128.json')
assert digest(G)=='7d60aaf32c25d4d000872f9d317cdb0cbc71c929307eb69faf7e974c795d5854'
ns=G['nodes'];idx={v['id']:i for i,v in enumerate(ns)};N=len(ns);full=(1<<N)-1;mask=lambda names:sum(1<<idx[x] for x in set(names) if x in idx);deps=[mask(v['deps']) for v in ns];req=[mask(v['backward_requires']) for v in ns];output=mask(G['outputs']);unit=G['inputs'][0]['bytes']
def read(stem):
 m=load(out/(stem+'.json'));assert m['binary_file']==stem+'.bin';assert m['full_graph_sha256']==digest(G);raw=(out/m['binary_file']).read_bytes();assert hashlib.sha256(raw).hexdigest()==m['binary_sha256'];a=array('I');a.frombytes(raw);assert a.itemsize==4
 if sys.byteorder!='little':a.byteswap()
 return m,a
bm,back12=read('b4-backward-pdb-cap12');cu=bm['cost_unit'];di={d:i for i,d in enumerate(bm['done_masks'])};back={c:read(f'b4-backward-pdb-cap{c}')[1] for c in [9,10,11,12]};terminal={c:read(f'b4-terminal-phase-pdb-cap{c}')[1] for c in [9,10,11,12]};_,demand=read('b4-output-demand-pdb-cap12');INF=(1<<32)-1;owned_memory=[0]*16384
for lv in range(1,16384):bit=lv&-lv;owned_memory[lv]=owned_memory[lv^bit]+ns[bit.bit_length()-1]['bytes']//unit
E=[min(int(demand[lv])*cu for lv in range(16384) if owned_memory[lv]<=m and demand[lv]!=INF) for m in range(12)]
manifest=load(args.cert_dir/'manifest.json')
assert len(manifest)==4
certs=[]
for record in manifest:
 assert Path(record['file']).name==record['file']
 raw=(args.cert_dir/record['file']).read_bytes()
 assert hashlib.sha256(raw).hexdigest()==record['raw_sha256']
 c=json.loads(raw)
 assert digest(c)==record['certificate_sha256'] and c['claims']==record['claims']
 certs.append(c)
all_checks=0;per_block_checks=0;stages={1:0,2:0,3:0};max_gain=0
for number,c in enumerate(certs):
 verify(G,c,c['budget']);acts=c['actions'];oldloss=next(i for i,a in enumerate(acts) if a['op']=='loss');firstsink=next(i for i,a in enumerate(acts) if a==dict(op='forward',node='b3_residual2'));acts=acts[:firstsink+1]+[dict(op='loss')]+acts[firstsink+1:oldloss]+acts[oldloss+1:];moved=certificate(G,acts,c['budget'],'recursive-earliest-loss-control',{});_,trace=verify(G,moved,c['budget'],True);assert moved['claims']==c['claims'];endpoints={j:next(i for i,a in enumerate(acts) if a==dict(op='backward',node=f'b{j}_norm1')) for j in [1,2,3]};minima_by_stage={}
 for j,T in endpoints.items():
  values=[[0]*T for _ in range(j)]
  for b in range(j):
   minimum=10**9
   for step in reversed(range(T)):
    occupancy=sum(ns[idx[x]]['bytes'] for x in trace[step]['live'] if x in idx and idx[x]//14==b)//unit;minimum=min(minimum,occupancy);values[b][step]=minimum
  minima_by_stage[j]=values
 remaining=[0]*4;seen=0
 for a in acts:
  if a['op']=='forward':
   i=idx[a['node']]
   if seen>>i&1:remaining[i//14]+=ns[i]['cost']
   seen|=1<<i
 live=seen=done=0;loss=False;localchecks=0
 for at,a in enumerate([None]+acts,start=-1):
  if a:
   op=a['op'];i=idx[a['node']] if 'node' in a else None
   if op=='forward':
    if seen>>i&1:remaining[i//14]-=ns[i]['cost']
    seen|=1<<i;live|=1<<i
   elif op=='drop':live^=1<<i
   elif op=='backward':done|=1<<i
   elif op=='loss':loss=True
  active=next((j for j in reversed(range(4)) if (done>>(14*j))&16383!=16383),-1)
  if active<=0:continue
  shift=14*active;earlier=(1<<shift)-1;target12=4095<<shift
  if seen&earlier!=earlier or done&earlier or done>>shift&1 or seen&target12!=target12 or (not loss and seen>>(shift+13)&1):continue
  assert at>=0 and at<endpoints[active]
  needed=0
  for i in range(N):
   if not(done>>i&1):needed|=req[i]
  if not loss:needed|=(full^seen)|output
  missing=needed&~live
  for i in reversed(range(N)):
   if missing>>i&1:missing|=deps[i]&~live
  repeat=missing&seen;base=[];locals=[(live>>(14*b))&16383 for b in range(4)];phase=None if loss else int(bool(seen>>(shift+12)&1));targetdone=(done>>shift)&16383
  for b in range(4):
   sh=14*b;lv=locals[b];dn=(done>>sh)&16383;own=sum(ns[i]['cost'] for i in range(sh,sh+14) if repeat>>i&1);outside=sum(ns[i]['cost'] for i in range(sh+12,sh+14) if repeat>>i&1);candidates=[own]
   if seen&(4095<<sh)==4095<<sh:v=back12[di[dn]*4096+(lv&4095)];assert v!=INF;candidates.append(int(v)*cu+outside)
   if b<3 and seen&(16383<<sh)==16383<<sh and dn==0 and not(done>>(sh+14)&1):v=demand[lv];assert v!=INF;candidates.append(int(v)*cu)
   if b==3 and not loss and dn==0 and seen&(4095<<sh)==4095<<sh and not(seen>>(sh+13)&1):v=terminal[12][int(bool(seen>>(sh+12)&1))*8192+(lv&8191)];assert v!=INF;candidates.append(int(v)*cu)
   base.append(max(candidates))
  actual=tuple(minima_by_stage[active][b][at] for b in range(active));current=[owned_memory[locals[b]] for b in range(active)];best=None;actualcomponents=None
  for minima in itertools.product(*(range(v+1) for v in current)):
   cap=max(9,12-sum(minima));v=back[cap][di[targetdone]*4096+(locals[active]&4095)] if loss else terminal[cap][phase*8192+(locals[active]&8191)]
   if v==INF:continue
   components=list(base)
   for b in range(active):components[b]=max(components[b],E[minima[b]])
   components[active]=max(components[active],int(v)*cu);score=sum(components);best=score if best is None else min(best,score)
   if minima==actual:actualcomponents=components
  assert actualcomponents is not None,(number,at,active,actual,current)
  assert all(actualcomponents[b]<=remaining[b] for b in range(4)),(number,at,active,actual,actualcomponents,remaining)
  assert best is not None and sum(base)<=best<=sum(remaining)
  all_checks+=1;localchecks+=1;per_block_checks+=4;stages[active]+=1;max_gain=max(max_gain,best-sum(base))
 event(dict(kind='recursive_active_region_trace',control=number,status='PASS',states_checked=localchecks,certificate_sha256=digest(c)))
assert (all_checks,per_block_checks,stages)==(1130,4520,{1:301,2:362,3:467})
event(dict(kind='recursive_active_region_done',status='PASS',legal_traces=len(certs),states_checked=all_checks,per_block_actual_case_checks=per_block_checks,states_by_active_stage=stages,max_gain_over_baseline=max_gain))

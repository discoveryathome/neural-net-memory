"""Exact local preloss down/residual2 phases followed by relaxed backward.

All first12 local values were seen; no local backward ran. The remaining first
down and first residual2 forwards are free, all other forwards are repeats.
The block input is freely available; fixed external bytes charge global x.
"""
from array import array
from pathlib import Path
import hashlib,heapq,json,sys,time
from pattern_db import PatternDB,INF
from verifier import digest

class TerminalPhaseDB:
 def __init__(self,g,cap,backward=None):
  self.g=g;self.cap=cap;self.backward=backward or PatternDB(g,cap).build();self.nodes=g['nodes'];assert len(self.nodes)==14;self.idx={v['id']:i for i,v in enumerate(self.nodes)};self.width=8192;self.cost_unit=self.backward.cost_unit
  assert g['outputs']==[self.nodes[13]['id']] and self.nodes[12]['id'].endswith('_down') and self.nodes[13]['id'].endswith('_residual2');self.down=1<<12;self.output_size=self.nodes[13]['bytes'];self.output_deps=sum(1<<self.idx[d] for d in self.nodes[13]['deps'] if d in self.idx)
  self.deps=[sum(1<<self.idx[d] for d in v['deps'] if d in self.idx) for v in self.nodes[:13]];self.costs=[v['cost']//self.cost_unit for v in self.nodes[:13]];self.mem=[sum(v['bytes'] for v in g['inputs'])]*self.width
  for live in range(1,self.width):bit=live&-live;self.mem[live]=self.mem[live^bit]+self.nodes[bit.bit_length()-1]['bytes']
  self.dist=array('I',[INF])*(2*self.width);self.stats={}
 def valid(self,phase,live):return self.mem[live]<=self.cap and (phase==1 or not(live&self.down))
 def build(self,seconds=30):
  start=time.monotonic();queue=[];expanded=0
  for live in range(self.width):
   if self.valid(1,live) and live&self.output_deps==self.output_deps and self.mem[live]+self.output_size<=self.cap:
    value=self.backward.dist[self.backward.di[0]*self.backward.width+(live&4095)]
    if value!=INF:at=self.width+live;self.dist[at]=value;queue.append((value,at))
  heapq.heapify(queue)
  while queue:
   cost,at=heapq.heappop(queue)
   if cost!=self.dist[at]:continue
   expanded+=1
   if expanded%1024==0 and time.monotonic()-start>seconds:raise RuntimeError('terminal phase PDB incomplete: time limit')
   phase,live=divmod(at,self.width)
   moves=[]
   for i,node in enumerate(self.nodes[:13]):
    bit=1<<i
    if live&bit:
     if node['recomputable'] and live&self.deps[i]==self.deps[i]:
      moves.append((phase*self.width+(live^bit),self.costs[i]))
      if i==12 and phase==1:moves.append((live^bit,0))
    elif self.valid(phase,live|bit):moves.append((phase*self.width+(live|bit),0))
   for target,extra in moves:
    value=cost+extra
    if value<self.dist[target]:self.dist[target]=value;heapq.heappush(queue,(value,target))
  self.stats=dict(completed=True,seconds=time.monotonic()-start,expanded=expanded,reached=sum(v!=INF for v in self.dist),dense_states=len(self.dist),storage_bytes=4*len(self.dist));return self
 def value(self,names,phase=0):
  if phase not in (0,1) or any(self.idx[x]>=13 for x in names if x in self.idx):raise ValueError('invalid terminal phase projection')
  live=sum(1<<self.idx[x] for x in set(names) if x in self.idx);value=self.dist[phase*self.width+live];return None if value==INF else int(value)*self.cost_unit
 def write(self,path,backward_meta,full_graph_sha256):
  path=Path(path);a=array('I',self.dist)
  if sys.byteorder!='little':a.byteswap()
  raw=a.tobytes();binary=path.with_suffix('.bin');binary.write_bytes(raw)
  meta=dict(schema='terminal-phase-pattern-db/v1',local_graph=self.g,local_graph_sha256=digest(self.g),full_graph_sha256=full_graph_sha256,cap_bytes=self.cap,live_nodes=[v['id'] for v in self.nodes[:13]],row_width=self.width,phases=[dict(down_seen=False,output_seen=False),dict(down_seen=True,output_seen=False)],cost_unit=self.cost_unit,unreachable=INF,binary_file=binary.name,binary_sha256=hashlib.sha256(raw).hexdigest(),binary_format='little-endian uint32, phase*8192+local13bit live; multiply finite by cost_unit',preconditions=['all first12 local forward values seen','no local backward executed','local residual2 unseen','phase0 iff local down unseen; phase1 iff down seen'],backward_metadata=backward_meta,stats=self.stats,generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
  path.with_suffix('.json').write_text(json.dumps(meta,indent=2)+'\n');return meta

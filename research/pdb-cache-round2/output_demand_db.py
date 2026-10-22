"""Backward PDB with a necessary local output demand before local backward.

Applicable when all local forwards have happened, no local backward has happened,
and a later consumer's unfinished backward still requires this block's output.
The demand can be met as soon as the output is live. All cross-block delay after
that read is relaxed away; the local input is always free/available.
"""
from array import array
import hashlib,heapq,json,sys,time
from pathlib import Path
from pattern_db import PatternDB,INF
from verifier import digest
class OutputDemandDB:
 def __init__(self,g,cap,backward=None):
  self.g=g;self.cap=cap;self.backward=backward or PatternDB(g,cap).build();self.nodes=g['nodes'];self.idx={v['id']:i for i,v in enumerate(self.nodes)};self.width=1<<len(self.nodes)
  if len(g['outputs'])!=1:raise ValueError('one local output required')
  self.output_bit=1<<self.idx[g['outputs'][0]];self.cost_unit=self.backward.cost_unit;self.costs=[v['cost']//self.cost_unit for v in self.nodes];self.deps=[sum(1<<self.idx[d] for d in v['deps'] if d in self.idx) for v in self.nodes];fixed=sum(v['bytes'] for v in g['inputs']);self.mem=[fixed]*self.width
  for live in range(1,self.width):bit=live&-live;self.mem[live]=self.mem[live^bit]+self.nodes[bit.bit_length()-1]['bytes']
  self.dist=array('I',[INF])*self.width;self.projection=[sum(1<<self.backward.li[v['id']] for i,v in enumerate(self.nodes) if live>>i&1 and v['id'] in self.backward.li) for live in range(self.width)];self.stats={}
 def build(self,seconds=60):
  start=time.monotonic();queue=[];expanded=0
  for live in range(self.width):
   if self.mem[live]<=self.cap and live&self.output_bit:
    value=self.backward.dist[self.backward.di[0]*self.backward.width+self.projection[live]]
    if value!=INF:self.dist[live]=value;queue.append((value,live))
  heapq.heapify(queue)
  while queue:
   cost,live=heapq.heappop(queue)
   if cost!=self.dist[live]:continue
   expanded+=1
   if expanded%1024==0 and time.monotonic()-start>seconds:raise RuntimeError('output-demand DB limit; no completed table')
   for i,node in enumerate(self.nodes):
    bit=1<<i
    if live&bit:
     if live&self.deps[i]!=self.deps[i] or not node['recomputable']:continue
     target=live^bit;value=cost+self.costs[i]
    else:
     target=live|bit
     if self.mem[target]>self.cap:continue
     value=cost
    if value<self.dist[target]:self.dist[target]=value;heapq.heappush(queue,(value,target))
  self.stats=dict(completed=True,seconds=time.monotonic()-start,expanded=expanded,reached=sum(v!=INF for v in self.dist),dense_states=self.width,storage_bytes=len(self.dist)*4)
  return self
 def value(self,names):
  live=sum(1<<self.idx[n] for n in names if n in self.idx);value=self.dist[live];return None if value==INF else int(value)*self.cost_unit
 def write(self,path,backward_meta,full_graph_sha256):
  path=Path(path);a=array('I',self.dist)
  if sys.byteorder!='little':a.byteswap()
  raw=a.tobytes();binary=path.with_suffix('.bin');binary.write_bytes(raw)
  meta=dict(schema='output-demand-pattern-db/v1',local_graph=self.g,local_graph_sha256=digest(self.g),full_graph_sha256=full_graph_sha256,cap_bytes=self.cap,live_nodes=[v['id'] for v in self.nodes],row_width=self.width,cost_unit=self.cost_unit,unreachable=INF,binary_file=binary.name,binary_sha256=hashlib.sha256(raw).hexdigest(),binary_format='little-endian uint32, index full local14bit live mask; multiply by cost_unit',preconditions=['all14 local forward values have been seen','no local backward has executed','a future later-consumer backward must read local output before any local backward is enabled'],backward_metadata=backward_meta,stats=self.stats,generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
  path.with_suffix('.json').write_text(json.dumps(meta,indent=2)+'\n');return meta

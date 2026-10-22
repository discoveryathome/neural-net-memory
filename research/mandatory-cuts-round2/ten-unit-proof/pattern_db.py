"""Exact backward pattern database with permanently available local inputs.

The local graph's external input allocation stands for the one global immutable
input. Every other block-entry input is free and permanently available in the
relaxation. All first forwards and the loss barrier are omitted; all later
forwards cost their full declared cost. Internal dependency/backward order and
output-before-drop allocation remain exact inside this local pattern.
"""
from array import array
import hashlib,heapq,json,math,sys,time
from pathlib import Path
from verifier import validate_graph,digest
INF=(1<<32)-1

class PatternDB:
 def __init__(self,g,cap):
  validate_graph(g);self.g=g;self.cap=cap;ns=g['nodes'];self.n=len(ns)
  if self.n>16:raise ValueError('pattern limit16nodes')
  self.idx={v['id']:i for i,v in enumerate(ns)}
  def mask(names):return sum(1<<self.idx[x] for x in names if x in self.idx)
  full=(1<<self.n)-1;children=[sum(1<<j for j,v in enumerate(ns) if a['id'] in v['deps']) for a in ns]
  # Ancestor closure of backward reads excludes unnecessary output-only nodes.
  relevant=set().union(*(set(v['backward_requires']) for v in ns))&set(self.idx)
  for v in reversed(ns):
   if v['id'] in relevant:relevant.update(d for d in v['deps'] if d in self.idx)
  self.live_nodes=[v['id'] for v in ns if v['id'] in relevant];self.li={x:i for i,x in enumerate(self.live_nodes)};self.width=1<<len(self.live_nodes)
  cmask=lambda names:sum(1<<self.li[x] for x in names if x in self.li)
  self.sizes=[ns[self.idx[x]]['bytes'] for x in self.live_nodes];self.deps=[cmask(ns[self.idx[x]]['deps']) for x in self.live_nodes]
  self.cost_unit=math.gcd(*(v['cost'] for v in ns));self.costs=[ns[self.idx[x]]['cost']//self.cost_unit for x in self.live_nodes]
  self.done_masks=[d for d in range(full+1) if all(not(d>>i&1) or d&children[i]==children[i] for i in range(self.n))];self.di={d:i for i,d in enumerate(self.done_masks)}
  self.reverse_backs=[]
  for done in self.done_masks:
   self.reverse_backs.append([(self.di[done^(1<<i)],cmask(v['backward_requires'])) for i,v in enumerate(ns) if done>>i&1 and done^(1<<i) in self.di])
  fixed=sum(v['bytes'] for v in g['inputs']);self.memory=[fixed]*self.width
  for live in range(1,self.width):
   bit=live&-live;self.memory[live]=self.memory[live^bit]+self.sizes[bit.bit_length()-1]
  self.valid=[mem<=cap for mem in self.memory];self.dist=array('I',[INF])*(self.width*len(self.done_masks));assert self.dist.itemsize==4
  self.stats={}
 def build(self,seconds=120,states=1000000):
  start=time.monotonic();goal=self.di[(1<<self.n)-1];queue=[];expanded=0;reached=0
  # A complete certificate need not free final values. All goal live sets cost0.
  for live,valid in enumerate(self.valid):
   if valid:
    at=goal*self.width+live;self.dist[at]=0;queue.append((0,at));reached+=1
  heapq.heapify(queue)
  while queue:
   cost,at=heapq.heappop(queue)
   if self.dist[at]!=cost:continue
   if expanded%1024==0 and time.monotonic()-start>seconds:raise RuntimeError('PDB time limit; no completed table')
   expanded+=1;done_index,live=divmod(at,self.width)
   moves=[]
   for i in range(len(self.live_nodes)):
    bit=1<<i
    if not(live&bit):
     target=live|bit
     if self.valid[target]:moves.append((done_index*self.width+target,0))
    elif live&self.deps[i]==self.deps[i] and self.g['nodes'][self.idx[self.live_nodes[i]]]['recomputable']:
     moves.append((done_index*self.width+(live^bit),self.costs[i]))
   for previous,required in self.reverse_backs[done_index]:
    if live&required==required:moves.append((previous*self.width+live,0))
   for target,extra in moves:
    value=cost+extra
    if value<self.dist[target]:
     if self.dist[target]==INF:
      reached+=1
      if reached>states:raise RuntimeError('PDB state limit; no completed table')
     self.dist[target]=value;heapq.heappush(queue,(value,target))
  self.stats=dict(completed=True,seconds=time.monotonic()-start,expanded=expanded,reached=reached,done_ideals=len(self.done_masks),live_bits=len(self.live_nodes),dense_states=len(self.dist),valid_live_states=sum(self.valid),storage_bytes=len(self.dist)*4)
  return self
 def project(self,names):return sum(1<<self.li[x] for x in names if x in self.li)
 def value(self,live_names,done=0):
  live=self.project(live_names);value=self.dist[self.di[done]*self.width+live]
  return None if value==INF else int(value)*self.cost_unit
 def write(self,path,full_graph_sha256=None):
  path=Path(path);data=array('I',self.dist)
  if sys.byteorder!='little':data.byteswap()
  raw=data.tobytes();binary=path.with_suffix('.bin');binary.write_bytes(raw)
  meta=dict(schema='backward-pattern-db/v1',local_graph=self.g,local_graph_sha256=digest(self.g),full_graph_sha256=full_graph_sha256,cap_bytes=self.cap,external_input_convention='fixed local external bytes stand for global immutable input; other local block input always free/available',live_nodes=self.live_nodes,done_masks=self.done_masks,row_width=self.width,cost_unit=self.cost_unit,unreachable=INF,binary_format='little-endian uint32, index done_index*row_width+compressed_live_mask; multiply finite value by cost_unit',binary_file=binary.name,binary_sha256=hashlib.sha256(raw).hexdigest(),stats=self.stats)
  path.with_suffix('.json').write_text(json.dumps(meta,indent=2)+'\n');return meta

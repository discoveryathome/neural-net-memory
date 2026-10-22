"""Construct a full charged trace using local PDB marginal eviction prices.

Derived from Doug Colkitt (@Mister-Meeseeks) trial Cache. Local exact PDBs are
optimistic eviction scores, not a global correctness or optimality argument.
"""
from pathlib import Path
import math
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from verifier import digest,validate_graph
from pattern_db import PatternDB,INF
from output_demand_db import OutputDemandDB

GRAPH_SHA256='7d60aaf32c25d4d000872f9d317cdb0cbc71c929307eb69faf7e974c795d5854'
WINNING_POLICY=dict(beta=.85,bonus=3.2,
    keepers=['b0_residual1','b1_residual2','b3_residual1'],
    forward_v=[5,3,3,5],backward_v=[5,5,5,5])

class Failed(RuntimeError):
    """A heuristic construction failed; this implies no impossibility claim."""

class Cache:
    def __init__(self,graph,cap,budget,policy):
        validate_graph(graph)
        if digest(graph)!=GRAPH_SHA256:raise ValueError('requires the pinned frozen b4 graph')
        if any(type(v) is not int or v<0 for v in (cap,budget)):raise ValueError('nonnegative integer cap and budget required')
        if cap%131072 or not 9<=cap//131072<=13:raise ValueError('construction domain is nine through thirteen allocation units')
        self.graph=graph;self.nodes={v['id']:v for v in graph['nodes']};self.ids=list(self.nodes)
        self.idx={name:i for i,name in enumerate(self.ids)};self.sizes={v['id']:v['bytes'] for v in graph['inputs']+graph['nodes']}
        self.cap=cap;self.budget=budget;self.beta=policy['beta'];self.bonus=policy['bonus'];self.keepers=set(policy['keepers'])
        if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in (self.beta,self.bonus)) or self.beta<0 or self.bonus<1:raise ValueError('finite nonnegative distance exponent and bonus at least one required')
        if not self.keepers<=set(self.ids):raise ValueError('unknown keeper')
        first=self.order(policy['forward_v']);back=list(reversed(self.order(policy['backward_v'])))
        self.requests=[('forward',name) for name in first]+[('loss',None)]+[('backward',name) for name in back]
        self.direct=[set(self.nodes[name]['deps']) if op=='forward' else set(self.nodes[name]['backward_requires']) if op=='backward' else set(graph['outputs']) for op,name in self.requests]
        closures={}
        def closure(name):
            if name not in closures:
                closures[name]={name}|set().union(*(closure(dep) for dep in self.nodes.get(name,{}).get('deps',[])))
            return closures[name]
        for name in self.ids:closure(name)
        self.future=[set().union(*(closure(name) for targets in self.direct[at:] for name in targets)) for at in range(len(self.requests))]+[set()]
        local=dict(graph,nodes=graph['nodes'][:14],outputs=['b0_residual2'],id='transformer-b4-t128-local-backward-pattern')
        self.back=PatternDB(local,cap).build();self.demand=OutputDemandDB(local,cap,self.back).build()
        self.values={}
        self.live={v['id'] for v in graph['inputs']};self.seen=set();self.done=0;self.spent=0;self.actions=[];self.index=0
    def order(self,positions):
        if len(positions)!=4 or any(type(v) is not int or not 1<=v<=5 for v in positions):raise ValueError('four valid V positions required')
        result=[]
        for block,position in enumerate(positions):
            row=self.ids[14*block:14*block+14];name=f'b{block}_v';row.remove(name);row.insert(position,name);result.extend(row)
        return result
    def emit(self,op,name=None):
        self.actions.append(dict(op=op,**(dict(node=name) if name is not None else {})))
        if op=='forward':
            if name in self.seen:self.spent+=self.nodes[name]['cost']
            self.seen.add(name);self.live.add(name)
            if self.spent>self.budget:raise Failed('work budget exceeded')
        elif op=='drop':self.live.remove(name)
        elif op=='backward':self.done|=1<<self.idx[name]
    def local_value(self,mask,block,done,consumer_done):
        key=(mask,block,done,consumer_done)
        if key not in self.values:
            if not done and block<3 and not consumer_done:value=self.demand.dist[mask]
            else:value=self.back.dist[self.back.di[done]*4096+(mask&4095)]
            self.values[key]=10**15 if value==INF else int(value)*self.back.cost_unit
        return self.values[key]
    def score(self,name):
        i=self.idx[name];block=i//14;done=(self.done>>(14*block))&16383
        consumer_done=bool(self.done>>(14*(block+1))&1)
        mask=sum(1<<(self.idx[x]%14) for x in self.live if x in self.idx and self.idx[x]//14==block)
        delta=max(0,self.local_value(mask&~(1<<(i%14)),block,done,consumer_done)-self.local_value(mask,block,done,consumer_done))
        distance=len(self.requests)+1
        for at in range(self.index,len(self.requests)):
            if name in self.direct[at]:distance=at-self.index+1;break
        value=delta/(self.sizes[name]*(distance**self.beta))
        return value*self.bonus if name in self.keepers else value
    def reserve(self,amount,protected):
        while sum(self.sizes[name] for name in self.live)+amount>self.cap:
            choices=[name for name in self.ids if name in self.live and name not in protected and self.nodes[name]['recomputable']]
            if not choices:raise Failed('protected allocation exceeds cap')
            dead=[name for name in choices if name not in self.future[self.index]]
            victim=dead[0] if dead else min(choices,key=lambda name:(self.score(name),name))
            self.emit('drop',victim)
    def ensure(self,name,protected):
        if name in self.live:return
        if name not in self.nodes:raise Failed('external input missing')
        if name in self.seen and not self.nodes[name]['recomputable']:raise Failed('nonrecomputable value absent')
        held=set(protected)
        for dep in self.nodes[name]['deps']:self.ensure(dep,held);held.add(dep)
        self.reserve(self.sizes[name],held);self.emit('forward',name)
    def run(self):
        for self.index,(op,name) in enumerate(self.requests):
            if op=='forward':self.ensure(name,set())
            else:
                held=set()
                for target in sorted(self.direct[self.index]):self.ensure(target,held);held.add(target)
                self.emit(op,name)
            for old in self.ids:
                if old in self.live and old not in self.future[self.index+1]:self.emit('drop',old)
        return self.actions

def construct(graph,cap=1441792,budget=956301312,policy=None):
    """Return actions. Always run the unchanged full verifier on the result."""
    return Cache(graph,cap,budget,WINNING_POLICY if policy is None else policy).run()

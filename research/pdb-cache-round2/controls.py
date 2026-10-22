"""Fixed-parameter mechanism ablation, not a retuned scheduler comparison."""
import json
from pathlib import Path
import sys
P=Path(__file__).resolve().parent;ROOT=P.parents[1]
sys.path[:0]=[str(ROOT),str(P)]
from cache_policy import Cache,WINNING_POLICY
from verifier import load,verify
from search import certificate

class Recovery(Cache):
    def score(self,name):
        seen=set()
        def walk(node,root=False):
            if node in seen or (node in self.live and not root) or node not in self.nodes:return 0
            seen.add(node)
            return self.nodes[node]['cost']+sum(walk(dep) for dep in self.nodes[node]['deps'])
        distance=len(self.requests)+1
        for at in range(self.index,len(self.requests)):
            if name in self.direct[at]:distance=at-self.index+1;break
        value=walk(name,True)/(self.sizes[name]*(distance**self.beta))
        return value*self.bonus if name in self.keepers else value
class Zero(Cache):
    def score(self,name):return 0.

def main():
    graph=load(ROOT/'benchmarks/graphs/transformer-b4-t128.json');rows=[]
    for label,cls in [('PDB marginal',Cache),('ancestor recovery',Recovery),('zero marginal',Zero)]:
        cache=cls(graph,1441792,10**10,WINNING_POLICY)
        cert=certificate(graph,cache.run(),10**10,'fixed-parameter-mechanism-ablation')
        metrics=verify(graph,cert,10**10);assert metrics['peak_bytes']==1441792
        rows.append(dict(mode=label,claims=metrics,original_budget_met=metrics['recompute_cost']<=956301312))
    assert [row['claims']['recompute_cost'] for row in rows]==[702349312,1517387776,4557045760]
    print(json.dumps(dict(status='PASS',fixed_parameter_ablation=True,retuned_comparison=False,rows=rows)),flush=True)
if __name__=='__main__':main()

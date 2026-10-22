import sys
import unittest
import random
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(P))
from interval_relaxation import check_mapping,events,solve
from search import certificate,exact
from verifier import verify

def synthetic(seed,n):
    rng=random.Random(seed);nodes=[]
    for i in range(n):
        prev='x' if i==0 else f'v{i-1}';names=['x']+[f'v{j}' for j in range(i+1)];deps=[prev]
        if i>1 and rng.random()<.55:
            extra=rng.choice(names[:-1])
            if extra not in deps:deps.append(extra)
        nodes.append(dict(id=f'v{i}',deps=deps,bytes=rng.randint(1,5),cost=rng.randint(1,4),backward_cost=1,backward_requires=rng.sample(names,rng.randrange(min(3,len(names))+1)),recomputable=rng.random()>.2))
    return dict(model='activation-memory/v1',id=f'chain-control-{seed}',inputs=[dict(id='x',bytes=rng.randint(1,4))],nodes=nodes,outputs=[f'v{n-1}'])


def prefetch_fixture():
    specs=[('a',['x'],5),('q',['a'],1),('k',['a'],1),('v',['a'],1),('s',['q','k'],5),('c',['s','v'],1)]
    g=dict(model='activation-memory/v1',id='prefetched-parallel-control',inputs=[dict(id='x',bytes=1)],nodes=[dict(id=name,deps=deps,bytes=size,cost=1,backward_cost=1,backward_requires=[],recomputable=True) for name,deps,size in specs],outputs=['c'])
    actions=[dict(op='forward',node=x) for x in ('a','v','q','k')]
    actions += [dict(op='drop',node='a'),dict(op='forward',node='s')]
    actions += [dict(op='drop',node=x) for x in ('q','k')]
    actions += [dict(op='forward',node='c')]
    actions += [dict(op='drop',node=x) for x in ('v','s')]
    actions += [dict(op='loss')]+[dict(op='backward',node=x) for x in ('c','s','v','k','q','a')]
    c=certificate(g,actions,0,'explicit-prefetch-counterexample')
    return g,c,['a','s','c']


class Controls(unittest.TestCase):
    def test_integer_work_above_float_exact_range(self):
        costs=[2**53+1,2**53+3,1]
        nodes=[dict(id=f'v{i}',deps=['x' if i==0 else f'v{i-1}'],bytes=1,cost=costs[i],backward_cost=1,backward_requires=['x' if i==0 else f'v{i-1}'],recomputable=True) for i in range(3)]
        g=dict(model='activation-memory/v1',id='large-integer-work',inputs=[dict(id='x',bytes=1)],nodes=nodes,outputs=['v2'])
        result=solve(g,['v0','v1','v2'],3,costs[0],seconds=5,persistent_allocations=True)
        self.assertEqual(result['status'],'OPTIMAL')
        self.assertEqual(result['relaxation_work'],2**53+1)
        self.assertEqual(result['certified_global_lower_bound'],2**53+1)

    def test_prefetch_counterexample(self):
        g,c,pivots=prefetch_fixture();verify(g,c,0)
        self.assertEqual(c['claims']['peak_bytes'],9)
        self.assertEqual(check_mapping(g,pivots,9,c,persistent_allocations=True)['mapped_interval_charge'],0)
        safe=solve(g,pivots,9,0,seconds=5,persistent_allocations=True)
        self.assertEqual(safe['status'],'OPTIMAL')
        self.assertEqual(safe['certified_global_lower_bound'],0)
        wrong=solve(g,pivots,9,0,seconds=5,naive=True)
        self.assertEqual(wrong['status'],'INFEASIBLE')

    def test_30_tiny_exact_optima_and_trace_mappings(self):
        for seed in range(10):
            g=synthetic(17653+seed,3+seed%3)
            pivots=[v['id'] for v in g['nodes']]
            for budget in (0,3,9):
                with self.subTest(seed=seed,budget=budget):
                    c=exact(g,budget);cap=c['claims']['peak_bytes']
                    check_mapping(g,pivots,cap,c,persistent_allocations=True)
                    result=solve(g,pivots,cap,budget,seconds=5,persistent_allocations=True)
                    self.assertEqual(result['status'],'OPTIMAL')
                    self.assertLessEqual(result['certified_global_lower_bound'],c['claims']['recompute_cost'])

    def test_90_parallel_branch_exact_optima_and_mappings(self):
        rename=dict(a='b0_norm1',q='b0_q',k='b0_k',v='b0_v',s='b0_scores',c='b0_context')
        for seed in range(30):
            rng=random.Random(8431+seed);g,_,_=prefetch_fixture()
            for v in g['nodes']:
                v['id']=rename[v['id']];v['deps']=[rename.get(d,d) for d in v['deps']]
                v.update(bytes=rng.randint(1,5),cost=rng.randint(1,4),recomputable=rng.random()>.15)
            g['outputs']=['b0_context'];anc={}
            for v in g['nodes']:
                ancestors={v['id'],'x'}
                for d in v['deps']:ancestors|=anc.get(d,{d})
                anc[v['id']]=ancestors
                v['backward_requires']=rng.sample(sorted(ancestors),rng.randrange(min(3,len(ancestors))+1))
            pivots=['b0_norm1','b0_scores','b0_context']
            for budget in (0,3,9):
                with self.subTest(seed=seed,budget=budget):
                    c=exact(g,budget);cap=c['claims']['peak_bytes']
                    check_mapping(g,pivots,cap,c,True,True)
                    result=solve(g,pivots,cap,budget,seconds=5,qk_backward_cut=True,persistent_allocations=True)
                    self.assertEqual(result['status'],'OPTIMAL')
                    self.assertLessEqual(result['certified_global_lower_bound'],c['claims']['recompute_cost'])

    def test_rejects_unordered_pivots(self):
        g,c,pivots=prefetch_fixture()
        with self.assertRaises(ValueError):events(g,['q','v','c'])


if __name__=='__main__':unittest.main()

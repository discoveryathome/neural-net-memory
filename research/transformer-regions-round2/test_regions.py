import unittest
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(HERE))
from regional_exact import solve,Limited
from compose_schedule import compose
from verifier import load,verify,simulate


def chain():
    ns=[]
    for name,dep,req,cost in [('a','x','x',100),('b','a','a',1),('c','b','b',1)]:
        ns.append(dict(id=name,bytes=1,cost=cost,backward_cost=2,deps=[dep],backward_requires=[req],recomputable=True))
    return dict(model='activation-memory/v1',id='region-chain',inputs=[dict(id='x',bytes=1)],nodes=ns,outputs=['c'])


class RegionTests(unittest.TestCase):
    def test_exact_weighted_cost_and_budget(self):
        g=chain();c=solve(g,3,100,seconds=5)
        self.assertEqual(verify(g,c,100)['recompute_cost'],100)
        self.assertIsNone(solve(g,3,99,seconds=5))
    def test_limit_never_claims_an_optimum(self):
        with self.assertRaises(Limited):solve(chain(),3,100,states=1,seconds=5)
    def test_tail_charges_every_forward(self):
        c=solve(chain(),3,101,seconds=5,backward_only=True)
        self.assertEqual(verify(chain(),c,101)['recompute_cost'],101)
        self.assertFalse(c['metadata']['optimal_at_cap'])
        self.assertEqual(c['metadata']['tail_peak_bytes'],3)
    def test_tail_cache_and_initial_allocation(self):
        c=solve(chain(),3,1,seconds=5,backward_only=True,initial_live=['a'])
        self.assertEqual(verify(chain(),c,1)['recompute_cost'],1)
        self.assertIsNone(solve(chain(),1,100,backward_only=True,initial_live=['a']))
    def test_all25_tiny_exact_frontiers(self):
        rows=[r for r in load(ROOT/'records/frontiers.json') if r['bound_method']=='exact-minimax']
        self.assertEqual(len(rows),25)
        for r in rows:
            g=load(ROOT/f"benchmarks/graphs/{r['graph']}.json");c=solve(g,r['peak_bytes'],r['budget'],seconds=10)
            self.assertEqual(verify(g,c,r['budget'])['peak_bytes'],r['peak_bytes'])
    def test_frozen_full_graph_composition(self):
        g=load(ROOT/'benchmarks/graphs/transformer-b4-t128.json')
        actions,stats=compose(g,1703936,478150656)
        m=simulate(g,actions,478150656)
        self.assertEqual(m['peak_bytes'],1703936)
        self.assertEqual(m['recompute_cost'],421494784)
        self.assertEqual(m['recompute_cost'],sum(r['recompute_cost'] for r in stats['regions']))
        self.assertFalse(stats['global_optimal'])
    def test_changed_graph_rejected(self):
        g=load(ROOT/'benchmarks/graphs/transformer-b4-t128.json');g['nodes'][0]['bytes']+=1
        with self.assertRaises(ValueError):compose(g,1703936,478150656)

if __name__=='__main__':unittest.main()

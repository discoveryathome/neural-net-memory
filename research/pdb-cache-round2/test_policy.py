import copy
from pathlib import Path
import sys
import unittest
P=Path(__file__).resolve().parent;ROOT=P.parents[1]
sys.path[:0]=[str(ROOT),str(P)]
from cache_policy import Cache,construct,Failed,WINNING_POLICY
from verifier import load,verify,Invalid

class PolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.graph=load(ROOT/'benchmarks/graphs/transformer-b4-t128.json')
    def test_exact_trace_and_full_verifier(self):
        saved=load(P/'certificates/transformer-b4-t128-cap11.json')
        self.assertEqual(construct(self.graph),saved['actions'])
        self.assertEqual(verify(self.graph,saved,956301312)['recompute_cost'],702349312)
    def test_work_limit_is_charged(self):
        with self.assertRaisesRegex(Failed,'budget'):construct(self.graph,budget=702349311)
    def test_foreign_graph_rejected(self):
        graph=copy.deepcopy(self.graph);graph['nodes'][0]['cost']+=1
        with self.assertRaisesRegex(ValueError,'pinned'):construct(graph)
    def test_invalid_numeric_and_order_parameters(self):
        for beta,bonus in [(float('nan'),3.2),(.85,float('inf')),(-1.,3.2),(.85,.5)]:
            p=dict(WINNING_POLICY,beta=beta,bonus=bonus)
            with self.assertRaises(ValueError):construct(self.graph,policy=p)
        p=dict(WINNING_POLICY,backward_v=[0,3,3,5])
        with self.assertRaises(ValueError):construct(self.graph,policy=p)
    def test_missing_regeneration_fails_full_verifier(self):
        saved=copy.deepcopy(load(P/'certificates/transformer-b4-t128-cap11.json'));seen=set()
        for at,action in enumerate(saved['actions']):
            if action['op']!='forward':continue
            if action['node'] in seen:del saved['actions'][at];break
            seen.add(action['node'])
        with self.assertRaises(Invalid):verify(self.graph,saved,956301312)

if __name__=='__main__':unittest.main()

from pathlib import Path
import sys
import unittest
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE));sys.path.insert(0,str(HERE.parents[1]))
from verifier import Invalid,load
from verify_result import check_proposal

class PackageTests(unittest.TestCase):
    def setUp(self):
        self.g=load(HERE.parents[1]/'benchmarks/graphs/transformer-b4-t128.json')
        self.p=load(HERE/'proposed-frontiers.json')['rows'][0]
        self.c=load(HERE.parents[1]/self.p['object'])
        self.r=next(r for r in load(HERE.parents[1]/'records/working-frontiers.json') if r['graph']==self.g['id'] and r['budget']==self.p['budget'])
    def test_fixed_budget_witness(self):
        self.assertLess(check_proposal(self.g,self.r,self.p,self.c)['peak_bytes'],self.r['peak_bytes'])
    def test_budget_substitution_rejected(self):
        self.c['budget']+=1
        with self.assertRaises(Invalid):check_proposal(self.g,self.r,self.p,self.c)
    def test_optimistic_claim_rejected(self):
        self.c['claims']['peak_bytes']-=131072
        with self.assertRaises(Invalid):check_proposal(self.g,self.r,self.p,self.c)
    def test_stale_incumbent_rejected(self):
        self.p['previous_peak_bytes']+=1
        with self.assertRaises(Invalid):check_proposal(self.g,self.r,self.p,self.c)
    def test_global_optimum_overclaim_rejected(self):
        self.p['global_optimal']=True
        with self.assertRaises(Invalid):check_proposal(self.g,self.r,self.p,self.c)
    def test_changed_graph_rejected(self):
        self.g['nodes'][0]['bytes']+=1
        with self.assertRaises(Invalid):check_proposal(self.g,self.r,self.p,self.c)

if __name__=='__main__':unittest.main()

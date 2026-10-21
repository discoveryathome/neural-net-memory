import copy
from pathlib import Path
import sys
import unittest
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(HERE))
from verifier import Invalid,load,verify
from budget_cut import make_budget_proof,check_budget_proof

class BudgetCutTests(unittest.TestCase):
    def setUp(self):
        self.g=load(ROOT/'benchmarks/graphs/transformer-b4-t128.json')
        self.p=make_budget_proof(self.g)
    def test_exact_threshold_and_unique_later_block_states(self):
        result=check_budget_proof(self.g,self.p)
        self.assertEqual(result['extra_work_lower_bound'],985661440)
        self.assertEqual(result['memory_bound_bytes'],1441792)
        self.assertEqual(sum(r['enumerated_cases'] for r in self.p['production_states']),820)
        for i in (1,2,3):
            self.assertEqual(self.p['production_states'][i]['admissible'],[dict(barrier=f'b{i}_gelu',survivor=f'b{i}_residual1')])
    def test_wrong_work_bound_rejected(self):
        self.p['extra_work_lower_bound']+=1
        with self.assertRaises(Invalid):check_budget_proof(self.g,self.p)
    def test_wrong_prefix_multiplicity_rejected(self):
        self.p['prefix_lengths']=[4,2,1]
        with self.assertRaises(Invalid):check_budget_proof(self.g,self.p)
    def test_forged_survivor_rejected(self):
        self.p['production_states'][3]['admissible'][0]['survivor']='b0_residual2'
        with self.assertRaises(Invalid):check_budget_proof(self.g,self.p)
    def test_boolean_count_rejected(self):
        self.p['up_replays_per_block']=True
        with self.assertRaises(Invalid):check_budget_proof(self.g,self.p)
    def test_changed_frozen_graph_rejected(self):
        self.g['nodes'][0]['cost']+=1
        with self.assertRaises(Invalid):check_budget_proof(self.g,self.p)
    def test_existing_witnesses_do_not_contradict_threshold(self):
        high=load(ROOT/'research/trial-30m/certificates/transformer-b4-t128-b956301312-p1441792.json')
        m=verify(self.g,high,956301312)
        self.assertEqual(m['peak_bytes'],self.p['memory_bound_bytes'])
        self.assertLess(high['budget'],self.p['extra_work_lower_bound'])
        aux=load(HERE/'certificates/auxiliary-budget.json');m=verify(self.g,aux,aux['budget'])
        self.assertEqual(m['peak_bytes'],self.p['cap_bytes'])
        self.assertGreaterEqual(m['recompute_cost'],self.p['extra_work_lower_bound'])
    def test_single_block_exact_control(self):
        sys.path.insert(0,str(ROOT/'research/retention-transfer-20261021'))
        from regional_exact import solve
        g=copy.deepcopy(self.g);g['id']='budget-first-block-control';g['nodes']=g['nodes'][:14];g['outputs']=['b0_residual2']
        c=solve(g,1310720,200000000,seconds=10)
        self.assertEqual(c['claims']['recompute_cost'],85032960)
        self.assertGreaterEqual(c['claims']['recompute_cost'],8*8388608)

if __name__=='__main__':unittest.main()

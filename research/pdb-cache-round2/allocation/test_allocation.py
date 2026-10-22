"""Full legal traces and rejection controls for the fixed-cache constructor."""
import copy
import sys
import unittest
from pathlib import Path

HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
from allocation_dp import ROOT,BUDGET,EXPECTED,PRIOR,local_graph,load,verify

class AllocationControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.graph=load(ROOT/'benchmarks/graphs/transformer-b4-t128.json')
        cls.saved={cap:load(HERE/f'certificates/transformer-b4-t128-cap{cap}.json') for cap in EXPECTED}

    def test_both_complete_traces_improve_work_at_original_caps(self):
        for cap,c in self.saved.items():
            with self.subTest(cap=cap):
                actual=verify(self.graph,c,BUDGET[cap])
                self.assertEqual(actual['peak_bytes'],131072*cap)
                self.assertEqual(actual['recompute_cost'],EXPECTED[cap])
                self.assertLess(actual['recompute_cost'],PRIOR[cap])

    def test_changed_frozen_cost_is_rejected(self):
        changed=copy.deepcopy(self.graph);changed['nodes'][0]['cost']+=1
        with self.assertRaises(ValueError):local_graph(changed)

    def test_dropping_checkpoint_before_its_first_reader_is_rejected(self):
        for cap,saved in self.saved.items():
            with self.subTest(cap=cap):
                changed=copy.deepcopy(saved);actions=changed['actions']
                drop=next(i for i,a in enumerate(actions) if a==dict(op='drop',node='b0_residual2'))
                action=actions.pop(drop)
                reader=next(i for i,a in enumerate(actions) if a==dict(op='forward',node='b1_norm1'))
                actions.insert(reader,action)
                with self.assertRaises(ValueError):verify(self.graph,changed,BUDGET[cap])

    def test_loss_before_all_first_forwards_is_rejected(self):
        changed=copy.deepcopy(self.saved[22]);changed['actions'].insert(0,dict(op='loss'))
        with self.assertRaises(ValueError):verify(self.graph,changed,BUDGET[22])

if __name__=='__main__':unittest.main()

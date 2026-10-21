import unittest
from trace_solver import solve_slots
from verifier import verify


def graph(recomputable=True):
    ns=[]
    for name,dep,req,cost in [('a','x','x',100),('b','a','a',1),('c','b','b',1)]:
        ns.append(dict(id=name,bytes=1,cost=cost,backward_cost=2,deps=[dep],backward_requires=[req],recomputable=recomputable))
    return dict(model='activation-memory/v1',id='slots-chain',inputs=[dict(id='x',bytes=1)],nodes=ns,outputs=['c'])

def slots(extra=True):
    a=[dict(op='forward',node=n) for n in 'abc']+[dict(op='loss'),dict(op='backward',node='c')]
    if extra:a.append(dict(op='forward',node='a'))
    return a+[dict(op='backward',node=n) for n in 'ba']

class SlotTests(unittest.TestCase):
    def test_repair_requires_new_recomputation_slot(self):
        stats,c=solve_slots(graph(),slots(False),100,3,5)
        self.assertIsNone(c)
        self.assertEqual(stats['status'],'INFEASIBLE')
        stats,c=solve_slots(graph(),slots(),100,3,5)
        self.assertIsNotNone(c)
        self.assertEqual(verify(graph(),c,100)['recompute_cost'],100)
        self.assertEqual(c['claims']['peak_bytes'],3)
        self.assertFalse(c['metadata']['global_optimal'])
    def test_weighted_budget_is_enforced(self):
        _,c=solve_slots(graph(),slots(),99,3,5)
        self.assertIsNone(c)
    def test_allocation_before_drop(self):
        _,c=solve_slots(graph(),slots(),1000,2,5)
        self.assertIsNone(c)
    def test_nonrecomputable_cannot_be_repeated(self):
        _,c=solve_slots(graph(False),slots(),1000,3,5)
        self.assertIsNone(c)
    def test_all_first_forwards_precede_loss(self):
        seq=[dict(op='loss')]+slots()[0:3]+[dict(op='backward',node=n) for n in 'cba']
        _,c=solve_slots(graph(),seq,1000,4,5)
        self.assertIsNone(c)
    def test_duplicate_forward_is_optional_and_cannot_overwrite(self):
        seq=slots(False);seq.insert(1,dict(op='forward',node='a'))
        _,c=solve_slots(graph(),seq,0,4,5)
        self.assertIsNotNone(c)
        verify(graph(),c,0)
        self.assertEqual(sum(a==dict(op='forward',node='a') for a in c['actions']),1)
    def test_invalid_backward_order_rejected(self):
        seq=slots(False);seq[-2:]=seq[-2:][::-1]
        with self.assertRaises(ValueError):solve_slots(graph(),seq,100,4,5)

if __name__=='__main__':unittest.main()

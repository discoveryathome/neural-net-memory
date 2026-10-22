import copy, sys, unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];sys.path[:0]=[str(ROOT),str(HERE)]
from verifier import load,verify,simulate,Invalid
from compose_schedule import compose
from reset_cut import check_cut
from verify_result import WITNESSES,WORK_WITNESS
from regional_exact import solve
class ResultTests(unittest.TestCase):
 def test_one_block_secondary_work_boundary(self):
  gid,budget,cap,oldwork,work=WORK_WITNESS
  graph=load(ROOT/f'benchmarks/graphs/{gid}.json')
  saved=load(HERE/'certificates/transformer-b1-t32-b26615808-p294912-minwork.json')
  self.assertEqual((verify(graph,saved,budget)['peak_bytes'],saved['claims']['recompute_cost']),(cap,work))
  self.assertLess(work,oldwork)
  self.assertIsNone(solve(graph,cap,work-1,states=220000,seconds=15))
 def test_two_complete_fixed_budget_constructions(self):
  for gid,budget,before,peak,cost,retained in WITNESSES:
   g=load(ROOT/f'benchmarks/graphs/{gid}.json');actions,stats=compose(g,peak,budget,retained=retained);m=simulate(g,actions,budget)
   self.assertEqual((m['peak_bytes'],m['recompute_cost']),(peak,cost));self.assertLess(peak,before);self.assertFalse(stats['global_optimal'])
 def test_retention_is_charged_globally(self):
  g=load(ROOT/'benchmarks/graphs/transformer-b2-t64.json')
  with self.assertRaises(ValueError):compose(g,655360,110821376,retained=[['b0_up']])
 def test_malformed_retention_rejected(self):
  g=load(ROOT/'benchmarks/graphs/transformer-b2-t64.json')
  for retained in ([],[['b0_up','b0_up']],[['missing']],[['b0_residual2']]):
   with self.assertRaises(ValueError):compose(g,1245184,27705344,retained=retained)
 def test_checkpoint_cannot_be_dropped_early(self):
  g=load(ROOT/'benchmarks/graphs/transformer-b2-t64.json');c=load(HERE/'certificates/transformer-b2-t64-b110821376-p655360.json');c=copy.deepcopy(c)
  i=next(i for i,a in enumerate(c['actions']) if a.get('node')=='b1_norm1');c['actions'].insert(i,dict(op='drop',node='b0_residual2'))
  with self.assertRaises(Invalid):verify(g,c,110821376)
 def test_false_metrics_and_budget_are_rejected(self):
  g=load(ROOT/'benchmarks/graphs/transformer-b2-t64.json');source=load(HERE/'certificates/transformer-b2-t64-b27705344-p1245184.json')
  for field in ('peak_bytes','recompute_cost'):
   c=copy.deepcopy(source);c['claims'][field]-=1
   with self.assertRaises(Invalid):verify(g,c,27705344)
  with self.assertRaises(Invalid):verify(g,source,27705343)
 def test_cut_false_bound_and_missing_barrier_rejected(self):
  g=load(ROOT/'benchmarks/graphs/transformer-b2-t64.json');source=load(HERE/'b2-reset-cut.json');self.assertEqual(check_cut(g,source),655360)
  c=copy.deepcopy(source);c['lower_bound_bytes']+=65536
  with self.assertRaises(Invalid):check_cut(g,c)
  c=copy.deepcopy(source);c['barriers']=c['barriers'][:1]
  with self.assertRaises(Invalid):check_cut(g,c)
if __name__=='__main__':unittest.main()

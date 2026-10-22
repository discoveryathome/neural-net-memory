"""Replay proposed witnesses and fixed-cap results with the frozen verifier."""
import argparse, hashlib, json, sys, subprocess, tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[1]
sys.path[:0]=[str(ROOT),str(HERE)]
from verifier import load, verify, digest
from compose_schedule import compose
from regional_exact import solve
from reset_cut import check_cut, find_cut

WITNESSES=[
 ('transformer-b2-t64',27705344,1310720,1245184,26869760,[['b0_q','b0_k','b0_residual1','b0_up']]),
 ('transformer-b2-t64',110821376,720896,655360,106725376,None),
]
EXACT=[(6653952,393216,360448,7725056),(13307904,360448,327680,15851520)]
WORK_WITNESS=('transformer-b1-t32',26615808,294912,24854528,23281664)

def main(reconstruct=False):
 manifest=load(HERE/'VERIFY.json')
 for name,expected in manifest['artifacts_sha256'].items():
  path=(HERE/name).resolve()
  path.relative_to(HERE)
  if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:raise ValueError('package artifact mismatch: '+name)
 sources=load(HERE/'SOURCES.json')
 for name,expected in sources['frozen_repository_files'].items():
  actual=hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
  if actual!=expected:raise ValueError('pinned source mismatch: '+name)
 result=[]
 for gid,budget,before,peak,cost,retained in WITNESSES:
  graph=load(ROOT/f'benchmarks/graphs/{gid}.json')
  name=f'{gid}-b{budget}-p{peak}.json';cert=load(HERE/'certificates'/name)
  actual=verify(graph,cert,budget)
  if actual['peak_bytes']!=peak or actual['recompute_cost']!=cost or peak>=before:raise ValueError('witness comparison mismatch')
  if reconstruct:
   actions,_=compose(graph,peak,budget,retained=retained)
   if actions!=cert['actions']:raise ValueError('constructor action replay mismatch')
  result.append(dict(graph=gid,budget=budget,before_peak=before,**actual))
 gid,budget,cap,oldwork,work=WORK_WITNESS
 graph=load(ROOT/f'benchmarks/graphs/{gid}.json')
 cert=load(HERE/'certificates/transformer-b1-t32-b26615808-p294912-minwork.json')
 actual=verify(graph,cert,budget)
 if actual['peak_bytes']!=cap or actual['recompute_cost']!=work or work>=oldwork:raise ValueError('work improvement mismatch')
 if reconstruct:
  solved=solve(graph,cap,budget,states=220000,seconds=15)
  if solved is None or solved['actions']!=cert['actions']:raise ValueError('work construction replay mismatch')
  if solve(graph,cap,work-1,states=220000,seconds=15) is not None:raise ValueError('smaller work unexpectedly feasible')
 result.append(dict(graph=gid,budget=budget,objective='recompute at fixed peak',before_work=oldwork,exact_minimum_work=work,**actual))
 graph=load(ROOT/'benchmarks/graphs/transformer-b1-t32.json')
 for budget,peak,cap,minwork in EXACT:
  name=f'transformer-b1-t32-cap{cap}-minwork.json';cert=load(HERE/'certificates'/name)
  actual=verify(graph,cert,100000000)
  if actual['peak_bytes']!=cap or actual['recompute_cost']!=minwork or minwork<=budget:raise ValueError('fixed-cap minimum-work comparison mismatch')
  if reconstruct:
   solved=solve(graph,cap,100000000,states=220000,seconds=15)
   if solved is None or solved['claims']['recompute_cost']!=minwork:raise ValueError('exact-search replay mismatch')
  result.append(dict(graph=graph['id'],budget=budget,peak_optimum=peak,rejected_cap=cap,minimum_work_at_rejected_cap=minwork,scope='full frozen graph fixed-cap exact Dijkstra; author checked'))
 graph=load(ROOT/'benchmarks/graphs/transformer-b2-t64.json');cut=load(HERE/'b2-reset-cut.json');bound=check_cut(graph,cut)
 if reconstruct and find_cut(graph)!=cut:raise ValueError('cut classifier replay mismatch')
 if bound!=655360:raise ValueError('unexpected structural floor')
 curve=None
 if reconstruct:
  with tempfile.TemporaryDirectory(prefix='work-curve-',dir=HERE) as temporary:
   call=subprocess.run([sys.executable,'-B',str(HERE/'work-curve/replay.py'),'--out',temporary],capture_output=True,text=True,timeout=300)
   if call.returncode:raise RuntimeError(call.stderr)
   curve=json.loads(call.stdout)
  if curve['status']!='PASS' or len(curve['rows'])!=11:raise ValueError('work curve replay failed')
 print(json.dumps(dict(status='PASS',evidence_level='author-checked',reconstructed=reconstruct,results=result,b2_universal_floor=bound,one_block_work_curve=curve),sort_keys=True))
 return result
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--reconstruct',action='store_true');args=parser.parse_args();main(args.reconstruct)

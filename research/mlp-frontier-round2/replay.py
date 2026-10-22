#!/usr/bin/env python3
"""Replay all original MLP rows, exclusion searches and diagnostic prices."""
from __future__ import annotations
import argparse
import hashlib
import json
import platform
import resource
import subprocess
import tempfile
import sys
import time
from pathlib import Path
P=Path(__file__).resolve().parent
R=P.parents[1]
sys.path.insert(0,str(R))
from verifier import load,verify,digest
from chain_exact import solve
from reference_fixed_cap import solve as reference

BASE='a95cc1588fc57a07cfcf5a350206825e6f5b4b52'
ROWS=[
 ('mlp-b4',0,151552,151552),
 ('mlp-b4',2129920,86016,86016),
 ('mlp-b4',4259840,53248,53248),
 ('mlp-b4',8519680,45056,45056),
 ('mlp-b4',17039360,40960,40960),
 ('mlp-b8',0,299008,299008),
 ('mlp-b8',4259840,135168,135168),
 ('mlp-b8',8519680,69632,69632),
 ('mlp-b8',17039360,53248,53248),
 ('mlp-b8',34078720,45056,40960),
]
STATE_CAP=500000
REFERENCE_CAP=200000
TIME_CAP=120

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def dump(path,value):path.write_text(json.dumps(value,indent=2)+'\n')

def run(record=False):
 started=time.monotonic()
 if not record:
  for source in load(P/'SOURCES.json')['files']:
   assert sha(R/source['path'])==source['sha256'],source
 working={(r['graph'],r['budget']):r for r in load(R/'records/working-frontiers.json')}
 results=[];proposed=[]
 for graph,budget,old,target in ROWS:
  g=load(R/f'benchmarks/graphs/{graph}.json')
  assert working[graph,budget]['peak_bytes']==old
  assert all(x['bytes']%4096==0 for x in g['inputs']+g['nodes'])
  before=time.monotonic()
  c,positive=solve(g,target,budget,state_cap=STATE_CAP,seconds=TIME_CAP)
  assert c is not None and c['claims']['peak_bytes']==target
  verify(g,c,budget)
  path=P/'certificates'/f'{graph}-b{budget}-p{target}.json'
  if record:
   path.parent.mkdir(exist_ok=True);dump(path,c)
  else:
   stored=load(path);verify(g,stored,budget)
   assert c['actions']==stored['actions'] and c['claims']==stored['claims']
  exclusion_cap=target-4096
  absent,negative=solve(g,exclusion_cap,budget,state_cap=STATE_CAP,seconds=TIME_CAP)
  assert absent is None and negative['status'].startswith('infeasible')
  oracle_cost,oracle=reference(g,exclusion_cap,budget,limit=REFERENCE_CAP,seconds=TIME_CAP)
  assert oracle_cost is None
  result=dict(graph=graph,graph_sha256=digest(g),budget=budget,
              previous_peak_bytes=old,optimal_peak_bytes=target,
              minimum_work_at_optimal_peak=c['claims']['recompute_cost'],
              exclusion_cap_bytes=exclusion_cap,
              chain_positive=positive,chain_exclusion=negative,
              generic_unnormalized_exclusion=oracle,
              certificate=str(path.relative_to(R)),certificate_sha256=sha(path),
              seconds=time.monotonic()-before)
  results.append(result)
  if budget:
   proposed.append(dict(graph=graph,budget=budget,peak_bytes=target,lower_bound=target,
                        optimal=True,previous_peak_bytes=old,
                        recompute_cost=c['claims']['recompute_cost'],
                        bound_method='exact-chain-fixed-cap-exclusion',
                        object=str(path.relative_to(R)),sha256=sha(path),
                        evidence_level=['author-checked'],
                        acceptance='proposal; independent review and maintainer acceptance pending'))
  print(json.dumps(result),flush=True)
 # The newly improved certificate is separately cross-checked without normalization.
 graph='mlp-b8';g=load(R/f'benchmarks/graphs/{graph}.json')
 cost,oracle=reference(g,40960,34078720,limit=REFERENCE_CAP,seconds=TIME_CAP)
 assert cost==34078720
 diagnostics=[]
 for graph,budget,expected in [('mlp-b4',100000000,21299200),('mlp-b8',200000000,93716480)]:
  g=load(R/f'benchmarks/graphs/{graph}.json')
  c,stats=solve(g,36864,budget,state_cap=STATE_CAP,seconds=TIME_CAP)
  assert c and c['claims']['recompute_cost']==expected
  path=P/'certificates'/f'diagnostic-{graph}-cap36864.json'
  if record:dump(path,c)
  else:
   stored=load(path);verify(g,stored,budget)
   assert c['actions']==stored['actions'] and c['claims']==stored['claims']
  diagnostics.append(dict(graph=graph,cap=36864,diagnostic_budget=budget,
                          minimum_work=expected,stats=stats,
                          object=str(path.relative_to(R)),sha256=sha(path)))
 with tempfile.TemporaryDirectory(prefix='mlp-work-curve-') as directory:
  subprocess.run([sys.executable,'-B',str(P/'work-curve/replay.py'),
                  '--repo',str(R),'--out',directory],check=True,cwd=R)
  curve=load(Path(directory)/'RESULTS.json')
  curve_summary={key:curve[key] for key in ('status','verified_cap_points',
    'nondominated_steps','work_minus_one_exclusions','original_budget_replays')}
 result=dict(base_commit=BASE,evidence_level='author-checked',
             complete_work_curves=curve_summary,
             status='PASS',rows=results,diagnostics=diagnostics,
             improved_positive_generic=dict(minimum_work=cost,**oracle),
             seconds=time.monotonic()-started,
             maxrss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
             environment=dict(python=sys.version,platform=platform.platform()),
             run_at_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
             solver_source_sha256=sha(P/'chain_exact.py'),
             generic_source_sha256=sha(P/'reference_fixed_cap.py'))
 if record:
  dump(P/'results.json',result);dump(P/'proposed-frontiers.json',proposed)
 print(json.dumps(dict(status='PASS',rows=len(results),improvements=1,
                       newly_closed_rows=8,complete_work_curves=curve_summary,seconds=result['seconds'],
                       maxrss_bytes=result['maxrss_bytes'])),flush=True)
 return result

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--record',action='store_true')
 run(ap.parse_args().record)

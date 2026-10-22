#!/usr/bin/env python3
"""Differential and failure controls for the declared chain specialization."""
from __future__ import annotations
import copy
import random
import sys
import unittest
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[1]
sys.path.insert(0,str(R))
from verifier import Invalid,digest,load,verify
from search import exact
from chain_exact import Limited,solve
from reference_fixed_cap import solve as reference

def graph(nodes=4):
 ns=[]
 for i in range(nodes):
  parent='n'+str(i-1) if i else 'x'
  ns.append(dict(id='n'+str(i),deps=[parent],bytes=1,cost=1,
                 backward_cost=1,backward_requires=[parent],recomputable=True))
 return dict(model='activation-memory/v1',id='test-chain',
             inputs=[dict(id='x',bytes=1)],nodes=ns,outputs=[ns[-1]['id']])

class ChainTests(unittest.TestCase):
 def test_random_chains_against_unnormalized_reference(self):
  rng=random.Random(0xdafc4be0);cases=0
  for fixture in range(50):
   g=graph(1+fixture%7)
   for v in g['nodes']:
    v.update(bytes=rng.randrange(1,6),cost=rng.randrange(1,8),
             recomputable=rng.random()>.1)
   for cap in (5,8,12,20):
    for budget in (0,3,15,50):
     with self.subTest(fixture=fixture,cap=cap,budget=budget):
      c,_=solve(g,cap,budget,seconds=10)
      cost,_=reference(g,cap,budget,seconds=10)
      self.assertEqual(None if c is None else c['claims']['recompute_cost'],cost)
     cases+=1
  self.assertEqual(cases,800)
 def test_original_tiny_exact_solver(self):
  for name in ('chain6-unit','chain6-weighted'):
   g=load(R/f'benchmarks/graphs/{name}.json')
   for budget in (0,1,3,6,12):
    with self.subTest(graph=name,budget=budget):
     c=exact(g,budget)
     peak=c['claims']['peak_bytes']
     candidate,_=solve(g,peak,budget)
     excluded,_=solve(g,peak-1,budget)
     self.assertIsNotNone(candidate);self.assertIsNone(excluded)
 def test_output_allocates_before_input_drop(self):
  g=graph(2)
  g['nodes'][0]['bytes']=4;g['nodes'][1]['bytes']=4
  self.assertIsNone(solve(g,8,100)[0])
  self.assertEqual(solve(g,9,100)[0]['claims']['peak_bytes'],9)
 def test_limits_do_not_produce_claims(self):
  with self.assertRaises(Limited):solve(graph(),4,10,state_cap=1)
  for kwargs in (dict(cap=True,budget=1),dict(cap=4,budget=False),
                 dict(cap=4,budget=1,state_cap=0),dict(cap=4,budget=1,seconds=0),
                 dict(cap=4,budget=1,seconds=float('nan')),
                 dict(cap=4,budget=1,seconds=float('inf'))):
   with self.assertRaises(ValueError):solve(graph(),**kwargs)
 def test_rejects_other_backward_semantics(self):
  g=graph();g['nodes'][2]['backward_requires']=['n0']
  with self.assertRaises(ValueError):solve(g,20,20)
 def test_verifier_negative_controls(self):
  g=load(R/'benchmarks/graphs/mlp-b8.json')
  c=load(P/'certificates/mlp-b8-b34078720-p40960.json')
  verify(g,c,34078720)
  bad=copy.deepcopy(c);bad['claims']['peak_bytes']-=4096
  with self.assertRaises(Invalid):verify(g,bad,34078720)
  bad=copy.deepcopy(c);bad['actions']=[a for a in bad['actions'] if a['op']!='loss']
  with self.assertRaises(Invalid):verify(g,bad,34078720)
  bad=copy.deepcopy(c);bad['actions'].pop(0)
  with self.assertRaises(Invalid):verify(g,bad,34078720)
  bad=copy.deepcopy(c);positions=[i for i,a in enumerate(bad['actions']) if a['op']=='backward']
  i,j=positions[:2];bad['actions'][i],bad['actions'][j]=bad['actions'][j],bad['actions'][i]
  with self.assertRaises(Invalid):verify(g,bad,34078720)
  bad=copy.deepcopy(c);bad['budget']=34078719
  with self.assertRaises(Invalid):verify(g,bad,34078719)
  changed=copy.deepcopy(g);changed['nodes'][0]['recomputable']=False
  bad=copy.deepcopy(c);bad['graph_sha256']=digest(changed)
  with self.assertRaises(Invalid):verify(changed,bad,34078720)

if __name__=='__main__':unittest.main()

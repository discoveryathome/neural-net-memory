"""Independent exhaustive finite-slot oracle, deliberately different transitions."""
import itertools
import random
import unittest
from trace_solver import solve_slots
from verifier import verify


def oracle(g,slots,budget,cap):
    ns={n['id']:n for n in g['nodes']};names=set(ns);fixed=sum(n['bytes'] for n in g['inputs'])
    inputs={n['id'] for n in g['inputs']}
    states={(frozenset(),frozenset(),False):0}
    for action in slots:
        nxt={}
        for (live,seen,phase),cost in states.items():
            live_list=sorted(live)
            for k in range(len(live_list)+1):
                for kept_tuple in itertools.combinations(live_list,k):
                    kept=set(kept_tuple);mem=fixed+sum(ns[v]['bytes'] for v in kept)
                    if mem>cap:continue
                    options=[];op=action['op'];name=action.get('node')
                    if op=='forward':
                        options.append((kept,seen,phase,cost))
                        v=ns[name];repeat=name in seen
                        if name not in kept and set(v['deps'])<=kept|inputs and (not repeat or v['recomputable']) and (repeat or not phase):
                            spend=cost+(v['cost'] if repeat else 0)
                            if spend<=budget and mem+v['bytes']<=cap:
                                options.append((kept|{name},seen|{name},phase,spend))
                    elif op=='loss':
                        if not phase and seen==names and set(g['outputs'])<=kept|inputs:options.append((kept,seen,True,cost))
                    elif phase and set(ns[name]['backward_requires'])<=kept|inputs:
                        options.append((kept,seen,phase,cost))
                    for l,s,p,c in options:
                        key=(frozenset(l),frozenset(s),p)
                        if c<nxt.get(key,10**100):nxt[key]=c
        states=nxt
    return min(states.values()) if states else None


class DifferentialTests(unittest.TestCase):
    def test_small_dags_against_exact_enumeration(self):
        rng=random.Random(0xdafc4be0)
        tested=0
        for fixture in range(12):
            nodes=[]
            for i in range(4):
                name='n'+str(i);parents=['x'] if not i else [nodes[i-1]['id']]
                if i>1 and rng.randrange(2):parents.append(nodes[rng.randrange(i-1)]['id'])
                ancestors={'x',name}
                for p in parents:
                    ancestors.add(p)
                    if p!='x':ancestors|=set(nodes[int(p[1:])]['_ancestors'])
                req=rng.sample(sorted(ancestors),min(len(ancestors),rng.randrange(1,3)))
                nodes.append(dict(id=name,bytes=rng.randrange(1,4),cost=rng.randrange(1,7),backward_cost=1,deps=parents,backward_requires=req,recomputable=True,_ancestors=sorted(ancestors)))
            for n in nodes:n.pop('_ancestors')
            g=dict(model='activation-memory/v1',id='oracle-'+str(fixture),inputs=[dict(id='x',bytes=1)],nodes=nodes,outputs=['n3'])
            seq=[dict(op='forward',node=n['id']) for n in nodes]+[dict(op='loss')]
            for n in reversed(nodes):
                seq.extend(dict(op='forward',node=p['id']) for p in nodes)
                seq.append(dict(op='backward',node=n['id']))
            for cap in (5,7,10):
                b=12
                expected=oracle(g,seq,b,cap)
                stats,c=solve_slots(g,seq,b,cap,5)
                with self.subTest(fixture=fixture,cap=cap):
                    self.assertNotEqual(stats['status'],'UNKNOWN')
                    actual=None if c is None else verify(g,c,b)['recompute_cost']
                    self.assertEqual(actual,expected)
                tested+=1
        self.assertEqual(tested,36)

if __name__=='__main__':unittest.main()

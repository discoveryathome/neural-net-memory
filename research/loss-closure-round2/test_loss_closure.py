import itertools
import random
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from loss_closure import loss_frontier, cut_frontiers, lower_bound, Limited
from search import exact

def brute(g,budget,forced=()):
    ns=g['nodes']; fixed=sum(x['bytes'] for x in g['inputs'])
    needed={x for n in ns for x in n['backward_requires']}; outputs=set(g['outputs'])|set(forced); ans={}
    for choices in itertools.product(range(3),repeat=len(ns)):
        d={n['id']:c for n,c in zip(ns,choices)}
        if any(d.get(x,1)==0 for x in needed) or any(d[x]!=1 for x in outputs):continue
        work=0;mem=fixed;ok=True
        for n,c in zip(ns,choices):
            if c==1:mem+=n['bytes']
            if c==2:
                work+=n['cost']
                if not n['recomputable'] or any(d.get(x,1)==0 for x in n['deps']):ok=False
        if ok and work<=budget:ans[mem]=min(ans.get(mem,10**30),work)
    return sorted((m,c) for m,c in ans.items() if not any(mm<=m and cc<=c and (mm,cc)!=(m,c) for mm,cc in ans.items()))

class ClosureTests(unittest.TestCase):
    def test_random_exhaustive(self):
        rng=random.Random(20261021)
        for trial in range(100):
            ns=[]
            for i in range(rng.randint(1,7)):
                names=['x']+[n['id'] for n in ns]; deps=rng.sample(names,rng.randint(1,min(2,len(names))))
                ns.append(dict(id='n'+str(i),deps=deps,bytes=rng.randint(1,4),cost=rng.randint(1,6),backward_cost=1,backward_requires=['n'+str(i)] if rng.randrange(2) else [],recomputable=bool(rng.randrange(4))))
            used={d for n in ns for d in n['deps']}
            g=dict(model='activation-memory/v1',id='r'+str(trial),inputs=[dict(id='x',bytes=2)],nodes=ns,outputs=[n['id'] for n in ns if n['id'] not in used])
            for budget in [0,7,50]:
                self.assertEqual(loss_frontier(g,budget)['frontier'],brute(g,budget))
                force=[ns[0]['id']]
                self.assertEqual(loss_frontier(g,budget,forced_live=force)['frontier'],brute(g,budget,force))

    def test_missing_ancestor_is_charged(self):
        g=dict(model='activation-memory/v1',id='chain',inputs=[dict(id='x',bytes=1)],nodes=[dict(id='a',deps=['x'],bytes=10,cost=100,backward_cost=1,backward_requires=[],recomputable=True),dict(id='b',deps=['a'],bytes=10,cost=1,backward_cost=1,backward_requires=['b'],recomputable=True),dict(id='c',deps=['b'],bytes=1,cost=1,backward_cost=1,backward_requires=[],recomputable=True)],outputs=['c'])
        self.assertEqual(loss_frontier(g,1)['frontier'][0][0],12)
        self.assertEqual(loss_frontier(g,101)['frontier'][0][0],2)
        self.assertEqual(loss_frontier(g,101,forced_live=(x for x in ['a'])),loss_frontier(g,101,forced_live=['a']))

    def test_limits_and_boolean_budget(self):
        g=dict(model='activation-memory/v1',id='one',inputs=[dict(id='x',bytes=1)],nodes=[dict(id='n',deps=['x'],bytes=1,cost=1,backward_cost=1,backward_requires=['n'],recomputable=True)],outputs=['n'])
        with self.assertRaises(ValueError):loss_frontier(g,True)
        with self.assertRaises(Limited):loss_frontier(g,10,max_labels=1)
        with self.assertRaises(ValueError):lower_bound(cut_frontiers(g,10),11)

    def test_event_bounds_below_true_optimum(self):
        rng=random.Random(91731)
        for trial in range(60):
            ns=[]
            for i in range(rng.randint(1,5)):
                names=['x','y']+[n['id'] for n in ns]
                deps=rng.sample(names,rng.randint(1,min(2,len(names))))
                ns.append(dict(id='n'+str(i),deps=deps,bytes=rng.randint(1,4),cost=rng.randint(1,4),backward_cost=1,backward_requires=['n'+str(i)] if rng.randrange(2) else [],recomputable=bool(rng.randrange(4))))
            used={d for n in ns for d in n['deps']}
            g=dict(model='activation-memory/v1',id='event'+str(trial),inputs=[dict(id='x',bytes=2),dict(id='y',bytes=3)],nodes=ns,outputs=[n['id'] for n in ns if n['id'] not in used])
            budget=rng.randrange(8)
            true=exact(g,budget,max_states=200000)
            bound,_=lower_bound(cut_frontiers(g,budget),budget)
            self.assertLessEqual(bound,true['claims']['peak_bytes'])

    def test_forged_record_rejected(self):
        from verify_result import check_record
        import copy
        row=dict(graph='x',graph_sha256='a'*64,budget=0,closure_bound=2,maximizing_cuts=['loss'],previous_bound=1,existing_upper=2)
        actual=[row];good=dict(schema='event-closure-bounds/v1',rows=[row])
        check_record(actual,good)
        for key,bad in [('budget',False),('closure_bound',3),('graph_sha256','stale')]:
            data=copy.deepcopy(good);data['rows'][0][key]=bad
            with self.assertRaises(ValueError):check_record(actual,data)
        with self.assertRaises(ValueError):check_record(actual,dict(schema='event-closure-bounds/v1',rows=[]))

if __name__=='__main__':unittest.main()

"""Frozen-graph survivor classification and budget-bound arithmetic.

This checks the finite structural lemma and costs for BUDGET-PROOF.md. The global
charging argument is author-reviewed mathematics, not proof-assistant validation.
No accepted result record is changed. Scope is activation-memory/v1 only.
"""
import argparse
import json
from pathlib import Path
from reset_cut import graph_facts,reachable
from verifier import digest,load,require

GRAPH_HASH='7d60aaf32c25d4d000872f9d317cdb0cbc71c929307eb69faf7e974c795d5854'


def make_budget_proof(g):
    require(digest(g)==GRAPH_HASH,'budget argument requires the unchanged frozen graph')
    nodes,inputs,sizes,ancestors,allocations=graph_facts(g)
    unit=sizes['x'];cap=10*unit
    require(inputs=={'x'} and all(z in (unit,4*unit) for z in sizes.values()),'unexpected storage shape')
    rows=[]
    for i in range(4):
        target=f'b{i}_residual2'
        barriers=[n for n in nodes if n in ancestors[target] and
                  sum(sizes[x] for x in allocations[n])==9*unit]
        cases=0;allowed=[]
        for barrier in barriers:
            initial=allocations[barrier]
            # Only one additional unit tensor fits; this enumerates every
            # possible live set, including values outside the target prefix.
            extras=[None]+[n for n in nodes if n not in initial and sizes[n]<=unit]
            for extra in extras:
                live=initial|({extra} if extra else set())
                require(sum(sizes[x] for x in live)<=cap,'survivor allocation overflow')
                # An old output cannot help produce its own strict ancestors.
                closure=reachable(g,live-{target},set(barriers));cases+=1
                if target in closure:allowed.append(dict(barrier=barrier,survivor=extra))
        rows.append(dict(target=target,barriers=barriers,enumerated_cases=cases,admissible=allowed))
        if i:
            require(allowed==[dict(barrier=f'b{i}_gelu',survivor=f'b{i}_residual1')],
                    'unique later-block production separator does not hold')
    c=nodes['b0_q']['cost'];block_costs=[]
    for i in range(4):
        for suffix in ('q','k','v','scores','context'):
            require(nodes[f'b{i}_{suffix}']['cost']==c,'attention costs differ')
        require(nodes[f'b{i}_up']['cost']==4*c,'UP weight differs')
        block_costs.append(sum(n['cost'] for name,n in nodes.items() if name.startswith(f'b{i}_')))
    require(len(set(block_costs))==1,'block forward costs differ')
    prefixes=[3,2,1];attention_count=4;up_count=1
    extra=sum(prefixes)*block_costs[0]+4*(attention_count*c+up_count*4*c)
    return dict(schema='last-barrier-budget-cut/v1',model=g['model'],graph_id=g['id'],graph_sha256=digest(g),
                cap_bytes=cap,memory_bound_bytes=11*unit,allocation_quantum_bytes=unit,
                extra_work_lower_bound=extra,threshold_comparison='budget < extra_work_lower_bound',
                prefix_lengths=prefixes,block_forward_cost=block_costs[0],attention_operation_cost=c,
                attention_replays_per_block=attention_count,up_replays_per_block=up_count,
                up_cost=4*c,blocks=4,production_states=rows,proof_document='BUDGET-PROOF.md',
                evidence_level='author-checked',
                scope='Finite survivor lemma and exact cost arithmetic; global charging proof is in the document and requires independent review')


def check_budget_proof(g,proof):
    require(isinstance(proof,dict),'budget proof must be an object')
    expected=make_budget_proof(g)
    # Serialized comparison also rejects bool-for-int and float-for-int claims.
    require(json.dumps(proof,sort_keys=True,separators=(',',':'))==
            json.dumps(expected,sort_keys=True,separators=(',',':')),
            'budget proof, separator table or arithmetic differs')
    return dict(extra_work_lower_bound=expected['extra_work_lower_bound'],
                memory_bound_bytes=expected['memory_bound_bytes'],
                cap_bytes=expected['cap_bytes'])


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('graph');p.add_argument('--out');p.add_argument('--check');a=p.parse_args();g=load(a.graph)
    if a.check:
        result=check_budget_proof(g,load(a.check));print(json.dumps(dict(status='PASS',**result)))
    else:
        proof=make_budget_proof(g)
        if a.out:Path(a.out).write_text(json.dumps(proof,indent=2)+'\n')
        print(json.dumps(proof,indent=2))


if __name__=='__main__':main()

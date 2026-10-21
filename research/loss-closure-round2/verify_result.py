"""Replay all frozen rows and reject stale/optimistic bound claims."""
import json
import hashlib
import sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE))
from loss_closure import cut_frontiers, lower_bound
from verifier import load, digest, integer

def check_record(actual,recorded):
    if recorded.get('schema')!='event-closure-bounds/v1' or type(recorded.get('rows')) is not list:raise ValueError('invalid result schema')
    for row in recorded['rows']:
        if any(not integer(row.get(k)) for k in ['budget','closure_bound','previous_bound','existing_upper']):raise ValueError('invalid integer claim')
    if actual!=recorded['rows']:raise ValueError('incorrect or incomplete bound claims')

def verify_package():
    manifest=load(HERE/'VERIFY.json')
    for name,wanted in manifest['artifacts_sha256'].items():
        path=(HERE/name).resolve()
        if HERE.resolve() not in path.parents:raise ValueError('artifact path escape')
        if hashlib.sha256(path.read_bytes()).hexdigest()!=wanted:raise ValueError('stale artifact: '+name)
    sources=load(HERE/'SOURCES.json')
    for name,wanted in sources['inputs_sha256'].items():
        path=(ROOT/name).resolve()
        if ROOT.resolve() not in path.parents:raise ValueError('source path escape')
        if hashlib.sha256(path.read_bytes()).hexdigest()!=wanted:raise ValueError('stale input: '+name)
    recorded=load(HERE/'results.json');rows=load(ROOT/'records/working-frontiers.json');cache={};actual=[]
    for row in rows:
        name=row['graph'];g=load(ROOT/'benchmarks/graphs'/str(name+'.json'))
        if name not in cache:cache[name]=cut_frontiers(g,max(x['budget'] for x in rows if x['graph']==name))
        bound,cuts=lower_bound(cache[name],row['budget'])
        out=dict(graph=name,graph_sha256=digest(g),budget=row['budget'],closure_bound=bound,maximizing_cuts=cuts,previous_bound=row['lower_bound'],existing_upper=row['peak_bytes'])
        if out['closure_bound']>out['existing_upper']:raise ValueError('bound exceeds known witness')
        actual.append(out)
    check_record(actual,recorded)
    print(json.dumps(dict(status='PASS',rows=len(actual),stronger_bounds=sum(r['closure_bound']>r['previous_bound'] for r in actual),matches_existing_upper=sum(r['closure_bound']==r['existing_upper'] for r in actual),evidence_level='author-checked',scope='necessary mandatory-event closure relaxation; witnesses establish matching peaks')))

if __name__=='__main__':verify_package()

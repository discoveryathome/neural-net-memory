"""Audit lower tables once, reconstruct69 full witnesses, and join the curves."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result

def run(repo,out):
    repo=Path(repo).resolve();out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
    lower_module=module('joined_lower_curve',HERE/'replay.py')
    factor=lower_module.factored_module()
    table_out=out/'factored-tables';proof=factor.run(repo,table_out)
    shared=(table_out,proof)
    lower=lower_module.run(repo,out/'lower',shared=shared)
    upper_module=module('joined_upper_curve',HERE.parent/'curve-construction/replay.py')
    upper=upper_module.run(repo,out/'constructions',shared=shared)
    assert lower['status']==upper['status']=='PASS'
    assert lower['graph_sha256']==upper['graph_sha256']
    bycap={r['cap_units']:r for r in upper['rows']}
    assert len(bycap)==len(upper['rows'])==69 and set(bycap)==set(range(14,83))
    expected={r['cap_units']:r for r in lower_module.load(HERE/'EXPECTED.json')['rows']}
    rows=[]
    for low in lower['rows']:
        cap=low['cap_units'];high=bycap[cap];metrics=high['verified_metrics']
        assert metrics['peak_bytes']<=low['peak_cap_bytes']==high['peak_cap_bytes']
        assert metrics['recompute_cost']==high['extra_work']==expected[cap]['constructive_work']
        assert low['lower_work']<=high['extra_work']
        gap=high['extra_work']-low['lower_work'];assert gap==expected[cap]['gap']
        rows.append(dict(cap_units=cap,peak_cap_bytes=low['peak_cap_bytes'],lower_work=low['lower_work'],extra_work=high['extra_work'],gap=gap,exact_fixed_cap_work=gap==0,verified_metrics=metrics,actions_sha256=high['actions_sha256']))
    exact=[r['cap_units'] for r in rows if r['exact_fixed_cap_work']]
    assert exact==list(range(16,83)) and len(exact)==67
    assert rows[-1]['extra_work']==rows[-1]['lower_work']==0 and rows[-2]['lower_work']==163840
    result=dict(schema='b4-work-curve/v1',status='PASS',graph_sha256=lower['graph_sha256'],unit_bytes=131072,rows=rows,diagnostics=lower['diagnostics'],exact_caps=exact,exact_points=len(exact),verified_constructive_points=len(rows),minimum_zero_additional_work_peak_bytes=82*131072,lower_audited_edges=proof['total_audited_edges']+lower['extra_audited_edges'],upper_negative_controls=upper['negative_controls'],additional_fixed_benchmark_wins_from_curve=0,scope='Global fixed-cap work minima at67caps16..82;14/15lower-uppergaps remain open. Auxiliary curve points are not additional fixed benchmark wins.',evidence='author-checked only; same-author-team checks are not independent scientific validation')
    (out/'RESULTS.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--repo',type=Path,default=ROOT);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    result=run(args.repo,args.out)
    print(json.dumps(dict(status=result['status'],constructive_points=result['verified_constructive_points'],exact_points=result['exact_points'],exact_caps='16..82',open_caps=[14,15],zero_work_peak_bytes=result['minimum_zero_additional_work_peak_bytes'],audited_edges=result['lower_audited_edges']),sort_keys=True),flush=True)

if __name__=='__main__':main()

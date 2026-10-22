"""Audit45 local tables once and verify the complete29-point b2 work curve."""
from array import array
from pathlib import Path
import argparse,hashlib,importlib.util,json,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result

def run(repo,out):
    repo=Path(repo).resolve();out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
    lower=module('joined_b2_curve_lower',HERE/'replay.py');table_out=out/'audited-tables';proof=lower.run(repo,table_out)
    upper=module('joined_b2_curve_upper',HERE.parent/'work-curve-construction/replay.py').run(repo,out/'constructions',shared=(table_out,proof))
    assert upper['status']==proof['status']=='PASS' and upper['graph_sha256']==proof['graph_sha256']
    graph=lower.load(repo/'benchmarks/graphs/transformer-b2-t64.json');memory,_=lower.bind_graph(graph)
    reset=module('b2_curve_credited_reset_cut',HERE.parent/'reset_cut.py')
    cut=lower.load(HERE.parent/'b2-reset-cut.json')
    assert reset.find_cut(graph)==cut and reset.check_cut(graph,cut)==10*65536
    expected=lower.load(HERE/'EXPECTED.json');hashes=expected['binary_sha256'];assert proof['binary_sha256']==hashes and set(proof['table_audits'])==set(hashes)
    def read(stem,cap):
        meta=lower.load(table_out/(stem+'.json'))
        assert meta['full_graph_sha256']==lower.digest(graph) and meta['local_graph']['nodes']==graph['nodes'][:14] and meta['local_graph']['inputs']==graph['inputs']
        assert meta['cap_bytes']==cap*65536 and lower.digest(meta['local_graph'])==meta['local_graph_sha256']
        raw=(table_out/meta['binary_file']).read_bytes();assert hashlib.sha256(raw).hexdigest()==meta['binary_sha256']==hashes[stem]
        values=array('I');values.frombytes(raw)
        if sys.byteorder!='little':values.byteswap()
        assert len(values)==16384 and meta['cost_unit']==16384
        return values
    demands={c:read(f'b2-output-demand-pdb-cap{c}',c) for c in range(9,24)}
    terminal={c:read(f'b2-terminal-phase-pdb-cap{c}',c) for c in range(9,24)}
    bycap={r['cap_units']:r for r in upper['rows']};assert len(bycap)==len(upper['rows'])==29 and set(bycap)==set(range(10,39))
    rows=[];summary_cache={}
    for low in proof['rows']:
        cap=low['cap_units'];high=bycap[cap];cost_unit=16384
        # The table cost unit is derived and checked in the lower replay.
        metadata=lower.load(table_out/f'b2-output-demand-pdb-cap{min(cap,23)}.json');cost_unit=metadata['cost_unit']
        if min(cap,23) not in summary_cache:summary_cache[min(cap,23)]=lower.summaries(demands[min(cap,23)],{c:terminal[c] for c in range(9,min(cap,23)+1)},cost_unit,memory)
        summary=summary_cache[min(cap,23)]
        certificate=lower.load(out/'constructions'/high['certificate_file'])
        actual=lower.actual_components(graph,certificate,cap,memory,demands[min(cap,23)],terminal,cost_unit,summary,low['lower_work'])
        metrics=actual['metrics'];assert metrics==high['verified_metrics']
        assert metrics['peak_bytes']<=cap*65536==low['peak_cap_bytes']
        assert metrics['recompute_cost']==high['extra_work']==low['lower_work']
        assert lower.digest(certificate['actions'])==high['actions_sha256']
        rows.append(dict(cap_units=cap,peak_cap_bytes=low['peak_cap_bytes'],lower_work=low['lower_work'],extra_work=high['extra_work'],gap=0,exact_fixed_cap_work=True,verified_metrics=metrics,actions_sha256=high['actions_sha256'],actual_owned_control=actual))
    assert [r['cap_units'] for r in rows]==list(range(10,39)) and rows[-1]['extra_work']==0 and rows[-2]['extra_work']==81920
    result=dict(schema='b2-work-curve/v1',status='PASS',graph_sha256=proof['graph_sha256'],unit_bytes=65536,rows=rows,exact_caps=list(range(10,39)),exact_points=29,verified_constructive_points=29,universal_peak_floor=dict(peak_units=10,peak_bytes=655360,credited_reset_cut_sha256=lower.digest(cut)),minimum_zero_additional_work_peak_bytes=38*65536,lower_audited_edges=proof['total_audited_edges'],lower_negative_tables=proof['negative_tables'],lower_negative_witnesses=proof['negative_witnesses'],upper_negative_controls=upper['negative_controls'],nineteen_roots=proof['nineteen_roots'],additional_fixed_benchmark_wins_from_curve=0,scope='Complete fixed-memory work frontier:29 global minima at caps10..38, universal10u structural floor, zero work from38u upward. Legal peaks are integral65536byte units. Auxiliary curve points are not additional fixed benchmark wins.',evidence='author-checked only; same-author-team reviews do not constitute independent scientific validation')
    (out/'RESULTS.json').write_text(json.dumps(result,indent=2)+'\n');return result

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--repo',type=Path,default=ROOT);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    result=run(args.repo,args.out);print(json.dumps(dict(status=result['status'],exact_points=29,exact_caps='10..38',zero_work_peak_bytes=result['minimum_zero_additional_work_peak_bytes'],audited_edges=result['lower_audited_edges'])),flush=True)
if __name__=='__main__':main()

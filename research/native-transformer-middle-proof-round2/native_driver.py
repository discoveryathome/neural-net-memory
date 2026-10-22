import argparse,functools,hashlib,json,math,subprocess,sys,time,resource,itertools,os
from pathlib import Path
PACKAGE=Path(__file__).resolve().parent;R=PACKAGE.parents[1];P=Path(os.environ.get('NATIVE_PROOF_OUT',str(PACKAGE/'generated')));P.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(R))
from verifier import load,verify,digest
from search import certificate

def run(g,cap,budget,order=None,weight=1,states=1000000,seconds=120,label=None,prefix=None,favorable_pivot=None,demand_mode=0,pdb=None,favorable_sealed=False,demand_pdb=None,terminal_pdb=None,region_bound=False):
 names=[v['id'] for v in g['nodes']];idx={v:i for i,v in enumerate(names)};n=len(names)
 if order is None:order=names
 assert sorted(order)==sorted(names)
 def mask(xs):return sum(1<<idx[x] for x in xs if x in idx)
 prefix_actions=[];initial_live=0;initial_cost=0;initial_m=0
 if prefix is not None:
  given=load(prefix);_,trace=verify(g,given,given['budget'],True)
  at=next(i for i,a in enumerate(given['actions']) if a['op']=='loss')
  assert max(x['live_bytes'] for x in trace[:at+1])<=cap
  initial_live=mask(trace[at]['live']);initial_cost=trace[at]['recompute_cost'];initial_m=n+1
  assert initial_cost<=budget
  prefix_actions=given['actions'][:at+1]
 quantum=functools.reduce(math.gcd,[v['bytes'] for v in g['nodes']+g['inputs']])
 lines=[f'{n} {sum(v["bytes"] for v in g["inputs"])//quantum} {cap//quantum} {budget} {states} {seconds} {weight} {demand_mode}']
 for v in g['nodes']:
  children=mask([w['id'] for w in g['nodes'] if v['id'] in w['deps']])
  lines.append(f'{v["id"]} {v["bytes"]//quantum} {v["cost"]} {mask(v["deps"])} {mask(v["backward_requires"])} {children} {int(v["recomputable"])}')
 lines.append(' '.join(str(idx[v]) for v in order));lines.append(str(mask(g['outputs'])))
 seeds=[(initial_live,0,initial_m,initial_cost)]
 if favorable_pivot:
  assert prefix is None
  initial_m=order.index(favorable_pivot)+1
  forced={favorable_pivot}|(set(g['nodes'][idx[favorable_pivot]]['deps'])&set(names))
  fixed_mask=mask(forced);remaining=(cap-sum(v['bytes'] for v in g['inputs'])-sum(g['nodes'][idx[v]]['bytes'] for v in forced))//quantum
  options=[v for v in order[:initial_m] if v not in forced and g['nodes'][idx[v]]['bytes']==quantum]
  if favorable_sealed:
   unseen=set(order[initial_m:]);reads={x for v in g['nodes'] for x in v['backward_requires']}
   assert unseen.isdisjoint(reads), 'omitted outputs may not be saved reads'
  seeds=[(fixed_mask|mask(chosen),0,n+1 if favorable_sealed else initial_m,0) for count in range(remaining+1) for chosen in itertools.combinations(options,count)]
 lines.append(str(len(seeds)));lines.extend(f'{live} {done} {m} {cost}' for live,done,m,cost in seeds)
 pdb_binary=None;pdb_hash=None
 if pdb:
  assert sys.byteorder=='little'
  meta=load(pdb);assert meta['cap_bytes']==cap and meta['full_graph_sha256']==digest(g)
  assert meta['local_graph_sha256']==digest(meta['local_graph'])
  assert meta['local_graph']['nodes']==g['nodes'][:14]
  assert meta['local_graph']['inputs']==g['inputs']
  for block in range(n//14):
   remap={v['id']:v['id'].replace('b0_',f'b{block}_',1) for v in g['nodes'][:14]};remap['x']='x' if block==0 else f'b{block-1}_residual2'
   for i,v in enumerate(meta['local_graph']['nodes']):
    expected=dict(v,id=remap[v['id']],deps=[remap[d] for d in v['deps']],backward_requires=[remap[d] for d in v['backward_requires']])
    assert expected==g['nodes'][block*14+i]
  assert meta['live_nodes']==names[:12] and meta['row_width']==4096
  pdb_binary=Path(pdb).parent/meta['binary_file'];pdb_hash=hashlib.sha256(pdb_binary.read_bytes()).hexdigest();assert pdb_hash==meta['binary_sha256']
  lines.append(f'{len(meta["done_masks"])} {meta["row_width"]} {meta["cost_unit"]}');lines.append(' '.join(map(str,meta['done_masks'])))
 else:lines.append('0 0 0')
 demand_binary=None;demand_hash=None
 if demand_pdb:
  assert pdb is not None
  dmeta=load(demand_pdb);assert dmeta['cap_bytes']==cap and dmeta['full_graph_sha256']==digest(g)
  assert dmeta['local_graph']==meta['local_graph'] and dmeta['local_graph_sha256']==digest(dmeta['local_graph'])
  assert dmeta['live_nodes']==names[:14] and dmeta['row_width']==16384 and dmeta['backward_metadata']==Path(pdb).name
  demand_binary=Path(demand_pdb).parent/dmeta['binary_file'];demand_hash=hashlib.sha256(demand_binary.read_bytes()).hexdigest();assert demand_hash==dmeta['binary_sha256']
  lines.append(f'{dmeta["row_width"]} {dmeta["cost_unit"]}')
 else:lines.append('0 0')
 terminal_binary=None;terminal_hash=None
 if terminal_pdb:
  assert pdb is not None and demand_pdb is not None
  tmeta=load(terminal_pdb);assert tmeta['cap_bytes']==cap and tmeta['full_graph_sha256']==digest(g)
  assert tmeta['local_graph']==meta['local_graph'] and tmeta['local_graph_sha256']==digest(tmeta['local_graph'])
  assert tmeta['live_nodes']==names[:13] and tmeta['row_width']==8192 and tmeta['backward_metadata']==Path(pdb).name
  assert tmeta['phases']==[dict(down_seen=False,output_seen=False),dict(down_seen=True,output_seen=False)]
  terminal_binary=Path(terminal_pdb).parent/tmeta['binary_file'];terminal_hash=hashlib.sha256(terminal_binary.read_bytes()).hexdigest();assert terminal_hash==tmeta['binary_sha256']
  lines.append(f'{tmeta["row_width"]} {tmeta["cost_unit"]}')
 else:lines.append('0 0')
 region_dir=None;region_hashes={}
 if region_bound:
  assert n==56 and cap==1572864 and pdb is not None and demand_pdb is not None and terminal_pdb is not None
  region_dir=Path(pdb).parent
  for c in [9,10,11]:
   for kind in ['backward','terminal-phase']:
    path=region_dir/f'b4-{kind}-pdb-cap{c}.json';lower=load(path)
    assert lower['cap_bytes']==c*quantum and lower['full_graph_sha256']==digest(g) and lower['local_graph']==meta['local_graph'] and lower['local_graph_sha256']==digest(lower['local_graph'])
    assert lower['cost_unit']==meta['cost_unit']
    if kind=='backward':assert lower['row_width']==4096 and lower['done_masks']==meta['done_masks'] and lower['live_nodes']==names[:12]
    else:assert lower['row_width']==8192 and lower['live_nodes']==names[:13] and lower['phases']==tmeta['phases'] and lower['backward_metadata']==f'b4-backward-pdb-cap{c}.json'
    assert lower['binary_file']==f'b4-{kind}-pdb-cap{c}.bin'
    raw=(region_dir/lower['binary_file']).read_bytes();actual=hashlib.sha256(raw).hexdigest();assert actual==lower['binary_sha256'];region_hashes[path.name]=actual
 lines.append('1' if region_bound else '0')
 label=(label or f'{g["id"]}-p{cap}-b{budget}-w{weight}-d{demand_mode}'+('-prefix' if prefix else '')+('-favorable' if favorable_pivot else '')+('-sealed' if favorable_sealed else ''))+f'-s{states}-{time.time_ns()}'
 inp=P/f'{label}.input';inp.write_text('\n'.join(lines)+'\n')
 source_hash=hashlib.sha256((PACKAGE/'native_search.cpp').read_bytes()).hexdigest();binary_hash=hashlib.sha256((P/'native_search').read_bytes()).hexdigest()
 t=time.monotonic();proc=subprocess.run([str(P/'native_search'),str(inp)]+([str(pdb_binary)] if pdb else [])+([str(demand_binary)] if demand_pdb else [])+([str(terminal_binary)] if terminal_pdb else [])+([str(region_dir)] if region_bound else []),capture_output=True,text=True,timeout=seconds+10)
 raw=P/f'{label}.native.json';raw.write_text(proc.stdout);(P/f'{label}.stderr').write_text(proc.stderr)
 if proc.returncode:raise RuntimeError((proc.returncode,proc.stderr))
 result=json.loads(proc.stdout)
 params=dict(graph=g['id'],graph_sha256=digest(g),cap=cap,budget=budget,first_forward_order=order,
             states=states,seconds=seconds,weight=weight,source_sha256=source_hash,run_id=label,
             prefix_source=None if prefix is None else str(prefix),
             favorable_pivot=favorable_pivot,initial_states=len(seeds),
             favorable_terminal_forwards_omitted=favorable_sealed,
             demand_mode=demand_mode,
             pdb_source=pdb,pdb_binary_sha256=pdb_hash,
             demand_pdb_source=demand_pdb,demand_pdb_binary_sha256=demand_hash,terminal_pdb_source=terminal_pdb,terminal_pdb_binary_sha256=terminal_hash,region_bound=region_bound,region_table_hashes=region_hashes,
             binary_sha256=binary_hash,
             elapsed=time.monotonic()-t,utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
             maxrss_children_bytes=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)
 if 'min_initial_h_live' in result:result['min_initial_h_seed_nodes']=[v for i,v in enumerate(names) if result['min_initial_h_live']>>i&1]
 if result['status']=='FEASIBLE':
  reconstructed_done=0
  if favorable_pivot:
   initial_live=result['initial_live'];initial_m=result['initial_progress']
   prefix_actions=[dict(op='forward',node=v) for v in order[:min(initial_m,n)]]
   if initial_m>n:
    reconstructed_done=result['initial_done'];prefix_actions.append(dict(op='loss'))
    prefix_actions.extend(dict(op='backward',node=v) for v in reversed(names) if reconstructed_done>>idx[v]&1)
   prefix_actions.extend(dict(op='drop',node=v) for v in order[:min(initial_m,n)] if not(initial_live>>idx[v]&1))
  live={v for v in names if initial_live>>idx[v]&1};seen=set(order[:min(initial_m,n)]);done={v for i,v in enumerate(names) if reconstructed_done>>i&1};sealed=initial_m>n;acts=list(prefix_actions)
  required={v['id']:set(v['backward_requires'])&set(names) for v in g['nodes']}
  children={v['id']:{w['id'] for w in g['nodes'] if v['id'] in w['deps']} for v in g['nodes']}
  deps={v['id']:set(v['deps'])&set(names) for v in g['nodes']}
  def emit(op,name=None):
   nonlocal sealed
   acts.append(dict(op=op,**({'node':name} if name is not None else {})))
   if op=='drop':live.remove(name)
   if op=='forward':live.add(name);seen.add(name)
   if op=='loss':sealed=True
   if op=='backward':done.add(name)
  def close():
   if not sealed and len(seen)==n and set(g['outputs'])<=live:emit('loss')
   if sealed:
    for v in reversed(names):
     if v not in done and children[v]<=done and required[v]<=live:emit('backward',v)
    need={r for v in names if v not in done for r in required[v]}
    useful=set(need);todo=list(need)
    while todo:
     for d in deps[todo.pop()]:
      if d not in useful:useful.add(d);todo.append(d)
    for v in names:
     if v in live and v not in useful:emit('drop',v)
  close()
  for i,gone in result['steps']:
   for j,v in enumerate(names):
    if gone>>j&1:emit('drop',v)
   emit('forward',names[i]);close()
  c=certificate(g,acts,budget,'native-dynamic-fixed-first-order',dict(construction_only=True,global_optimality_claim=False,params=params,
               search_stats={k:v for k,v in result.items() if k!='steps'}))
  metrics,trace=verify(g,c,budget,True);start_bytes=trace[len(prefix_actions)-1]['live_bytes'] if prefix_actions else sum(v['bytes'] for v in g['inputs']);tail_peak=max([start_bytes]+[x['live_bytes'] for x in trace[len(prefix_actions):]])
  assert (favorable_pivot or metrics['peak_bytes']<=cap) and tail_peak<=cap and metrics['recompute_cost']==result['cost']
  (P/f'{label}.certificate.json').write_text(json.dumps(c,indent=2)+'\n')
  result['verified_claims']=metrics
  result['tail_peak_bytes']=tail_peak;result['full_peak_candidate']=not bool(favorable_pivot)
 result.pop('steps',None);out=dict(params=params,result=result)
 (P/f'{label}.summary.json').write_text(json.dumps(out,indent=2)+'\n')
 with (P/'measurements.jsonl').open('a') as f:f.write(json.dumps(out)+'\n')
 print(json.dumps(out),flush=True);return out

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--controls',action='store_true');ap.add_argument('--graph',default='transformer-b4-t128');ap.add_argument('--cap',type=int,default=1703936);ap.add_argument('--budget',type=int,default=478150656);ap.add_argument('--weight',type=float,default=1);ap.add_argument('--states',type=int,default=1000000);ap.add_argument('--seconds',type=float,default=120);ap.add_argument('--order-from');ap.add_argument('--prefix-from');ap.add_argument('--favorable-pivot');ap.add_argument('--demand-mode',type=int,default=0);ap.add_argument('--pdb');ap.add_argument('--favorable-sealed',action='store_true');ap.add_argument('--demand-pdb');ap.add_argument('--terminal-pdb');ap.add_argument('--region-bound',action='store_true');a=ap.parse_args()
 if a.controls:
  rows=[x for x in load(R/'records/working-frontiers.json') if x['family']=='synthetic'];passed=0
  for row in rows:
   g=load(R/f'benchmarks/graphs/{row["graph"]}.json');c=load(R/row['object']);order=[]
   for v in c['actions']:
    if v['op']=='forward' and v['node'] not in order:order.append(v['node'])
   out=run(g,row['peak_bytes'],row['budget'],order,states=100000,seconds=10,label=f'control-{g["id"]}-b{row["budget"]}')
   assert out['result']['status']=='FEASIBLE';passed+=1
  print(json.dumps(dict(status='PASS',controls=passed)),flush=True)
 else:
  g=load(R/f'benchmarks/graphs/{a.graph}.json')
  if a.order_from:
   c=load(a.order_from);order=[]
   for v in c['actions']:
    if v['op']=='forward' and v['node'] not in order:order.append(v['node'])
  else:
   order=[v['id'] for v in g['nodes']]
   for b in range(4):
    v=f'b{b}_v';p=f'b{b}_probs'
    if v in order:order.remove(v);order.insert(order.index(p)+1,v)
  run(g,a.cap,a.budget,order,a.weight,a.states,a.seconds,prefix=a.prefix_from,favorable_pivot=a.favorable_pivot,demand_mode=a.demand_mode,pdb=a.pdb,favorable_sealed=a.favorable_sealed,demand_pdb=a.demand_pdb,terminal_pdb=a.terminal_pdb,region_bound=a.region_bound)

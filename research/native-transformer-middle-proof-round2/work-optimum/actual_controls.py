"""Separate Cartesian nested-h reference on every actual PR6 suffix state."""
from array import array
from pathlib import Path
import hashlib,itertools,json,subprocess,sys,time
import argparse
HERE=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--repo',type=Path,required=True);parser.add_argument('--tables',type=Path,required=True);parser.add_argument('--native',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);parser.add_argument('--cap',type=int,choices=[13,14],default=13);args=parser.parse_args()
ROOT=args.repo.resolve();P=args.out.resolve();P.mkdir(parents=True,exist_ok=True);T=args.tables.resolve()
sys.path.insert(0,str(ROOT))
from verifier import load,verify,digest
g=load(ROOT/'benchmarks/graphs/transformer-b4-t128.json');ns=g['nodes'];names=[v['id'] for v in ns];ix={x:i for i,x in enumerate(names)}
mask=lambda xs:sum(1<<ix[x] for x in set(xs) if x in ix)
dep=[mask(v['deps']) for v in ns];req=[mask(v['backward_requires']) for v in ns];children=[mask(w['id'] for w in ns if v['id'] in w['deps']) for v in ns]
sizes=[v['bytes']//131072 for v in ns];costs=[v['cost'] for v in ns];INF=4294967295;CU=32768;C=args.cap;full=(1<<56)-1
def bits(m):
 while m:
  bit=m&-m;m^=bit;yield bit.bit_length()-1
anc=[]
for i in range(56):anc.append((1<<i)|dep[i])
for i in range(56):
 for j in bits(dep[i]):anc[i]|=anc[j]
def close(live,done,sealed):
 if sealed:
  for i in reversed(range(56)):
   if not(done>>i&1) and done&children[i]==children[i] and live&req[i]==req[i]:done|=1<<i
  need=0
  for i in range(56):
   if not(done>>i&1):
    for j in bits(req[i]):need|=anc[j]
  live&=need
 return live,done
def read(kind,c):
 p=T/f'b4-{kind}-pdb-cap{c}.json';m=load(p)
 assert m['binary_file']==p.stem+'.bin' and m['cost_unit']==32768 and m['cap_bytes']==c*131072
 raw=p.with_suffix('.bin').read_bytes();assert hashlib.sha256(raw).hexdigest()==m['binary_sha256'];a=array('I');a.frombytes(raw)
 if sys.byteorder!='little':a.byteswap()
 return m,a
B={};D={};TERM={};E={};hashes={};owned=[sum(sizes[i] for i in bits(lv)) for lv in range(16384)]
for c in range(9,C+1):
 bm,B[c]=read('backward',c);dm,D[c]=read('output-demand',c);tm,TERM[c]=read('terminal-phase',c)
 E[c]=[min((int(v)*CU for lv,v in enumerate(D[c]) if owned[lv]<=m and v!=INF),default=10**15) for m in range(C)]
 for kind,m in [('backward',bm),('output-demand',dm),('terminal-phase',tm)]:hashes[f'b4-{kind}-pdb-cap{c}']=m['binary_sha256']
di={d:i for i,d in enumerate(bm['done_masks'])}
# The orchestrator completely audits all15 tables before this control.
assert hashes=={key:value for key,value in load(HERE/'EXPECTED.json')['table_binary_sha256'].items() if int(key.rsplit('cap',1)[1])<=C}
def ref(live,done,m,seen):
 needed=0
 for i in range(56):
  if not(done>>i&1):needed|=req[i]
 if m<=56:needed|=(full^seen)|mask(g['outputs'])
 missing=0;todo=needed&~live
 while todo:
  bit=todo&-todo;todo^=bit
  if missing&bit:continue
  missing|=bit;todo|=dep[bit.bit_length()-1]&~live&~missing
 repeat=missing&seen;bounds=[]
 for b in range(4):
  shift=14*b;ll=(live>>shift)&16383;ld=(done>>shift)&16383
  own=sum(costs[i] for i in bits(repeat&(16383<<shift)));outside=sum(costs[i] for i in bits(repeat&(12288<<shift)))
  bound=own
  if seen&(4095<<shift)==4095<<shift:
   v=B[C][di[ld]*4096+(ll&4095)];assert v!=INF;bound=max(bound,int(v)*CU+outside)
  if b<3 and seen&(16383<<shift)==16383<<shift and not ld and not(done>>(shift+14)&1):
   v=D[C][ll];assert v!=INF;bound=max(bound,int(v)*CU)
  if b==3 and m<=56 and not ld and seen&(4095<<shift)==4095<<shift and not(seen>>(shift+13)&1):
   phase=(seen>>(shift+12))&1;v=TERM[C][phase*8192+(ll&8191)];assert v!=INF;bound=max(bound,int(v)*CU)
  bounds.append(bound)
 answer=max(sum(costs[i] for i in bits(repeat)),sum(bounds));active=3
 while active>=0 and (done>>(14*active))&16383==16383:active-=1
 if active>0:
  shift=14*active;earlier=(1<<shift)-1
  if seen&earlier==earlier and not(done&earlier) and not(done>>shift&1) and seen&(4095<<shift)==4095<<shift and (m==57 or not(seen>>(shift+13)&1)):
   value=10**15
   for minima in itertools.product(*(range(owned[(live>>(14*b))&16383]+1) for b in range(active))):
    terms=[]
    for b,mi in enumerate(minima):
     c=max(9,C-sum(minima[:b]));d=D[c][(live>>(14*b))&16383]
     if d==INF:break
     terms.append(max(bounds[b],int(d)*CU,E[c][mi]))
    if len(terms)!=active:continue
    c=max(9,C-sum(minima));ll=(live>>shift)&16383;ld=(done>>shift)&16383
    v=B[c][di[ld]*4096+(ll&4095)] if m==57 else TERM[c][((seen>>(shift+12))&1)*8192+(ll&8191)]
    if v==INF:continue
    value=min(value,sum(terms)+max(bounds[active],int(v)*CU)+sum(bounds[active+1:]))
   answer=max(answer,value)
 return answer
path=HERE/('positive-witness.json' if C==13 else 'positive-cap14.json');w=load(path);metrics,trace=verify(g,w,w['budget'],True)
root=next(i for i,a in enumerate(w['actions']) if a==dict(op='forward',node='b3_gelu'));order=[];seen=done=0;sealed=False;cases=[];seeds=[]
for at,a in enumerate(w['actions']):
 if a['op']=='forward':
  i=ix[a['node']]
  if not(seen>>i&1):order.append(i)
  seen|=1<<i
 elif a['op']=='backward':done|=1<<ix[a['node']]
 elif a['op']=='loss':sealed=True
 if at<root:continue
 rawlive=mask(trace[at]['live']);m=57 if sealed else seen.bit_count()
 if m==56 and rawlive&mask(g['outputs'])==mask(g['outputs']):m=57
 live,closed=close(rawlive,done,m==57)
 want=ref(live,closed,m,seen);remaining=metrics['recompute_cost']-trace[at]['recompute_cost'];assert want<=remaining,(at,want,remaining)
 seeds.append(f'{rawlive} {done} {m} 0');cases.append(dict(at=at,h=want,remaining=remaining))
lines=[f'56 1 {C} 10000000000 1 .01 1 0']
lines += [f'{v["id"]} {sizes[i]} {costs[i]} {dep[i]} {req[i]} {children[i]} 1' for i,v in enumerate(ns)]
lines += [' '.join(map(str,order)),str(mask(g['outputs'])),str(len(seeds)),*seeds,f'{len(di)} 4096 {CU}',' '.join(map(str,bm['done_masks'])),'16384 32768','8192 32768','1']
inp=P/'all-actual-controls.input';inp.write_text('\n'.join(lines)+'\n')
command=[args.native.resolve(),inp,T/f'b4-backward-pdb-cap{C}.bin',T/f'b4-output-demand-pdb-cap{C}.bin',T/f'b4-terminal-phase-pdb-cap{C}.bin',T]
proc=subprocess.run(list(map(str,command)),capture_output=True,text=True,timeout=5);assert proc.returncode==0,proc.stderr
native=json.loads(proc.stdout)
(P/'heuristic-controls-native.json').write_text(json.dumps(native,indent=2)+'\n')
assert native['initial_h_values']==[x['h'] for x in cases],[(x['at'],v,x['h']) for v,x in zip(native['initial_h_values'],cases) if v!=x['h']][:10]
receipt=dict(status='PASS',actual_states=len(cases),all_native_equal_cartesian_reference=True,all_h_at_most_actual_remaining=True,first_h=cases[0]['h'],table_hashes_matched_expected_complete_audits=hashes,
 source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),native_sha256=hashlib.sha256((HERE/'native_search.cpp').read_bytes()).hexdigest(),cases=cases,scope='same-author-team admissibility controls; no scientific exclusion claim from construction variant')
(P/'heuristic-controls.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({k:v for k,v in receipt.items() if k not in ['cases','table_hashes_matched_expected_complete_audits']}),flush=True)

"""Source-only terminal-phase PDB replay for all required native capacities.

Dependencies: sibling pattern_db.py, terminal_phase_db.py, replay_pdb.py;
standard library; unchanged verifier.py from --repo. No committed binaries.
"""
from array import array
from collections import deque
from pathlib import Path
import argparse,copy,hashlib,heapq,json,math,sys,tempfile
import replay_pdb
INF=(1<<32)-1
BACK_HASH={9:'93ebed09daff951d1fe9ebcfee099879ca1b2f07f09e1a315db3e2f80254eb8b',10:'5a66a501384823793f9afb4529f7619465e199f869dd6ab98dec1d537c107a76',11:'e48ed0271ffbd28b5c267591fca82eeaeec06b1a696911c747ddaa05a559566b',12:'a4fcff1b2db6d60bc0e37ad7212e9ddbf7c1b64bbcc2c03efe542e6ad523acd9'}
TERMINAL_HASH={9:'c19fb01dee30f1dd65e628e5fc0e3280da7d962992ff5b569163f728812e074f',10:'6ec53acd481eca7879b557064481c5f2c8757d93d63ec79c4264a354bfff9fc6',11:'249780b445f43f336853c7d72f0a3136630e54ce8527e8ed7622c1771b92fb10',12:'f294de6a1bd14aac3e27fc3527e308dbac5bcd5c602a2b701bff68c7ef4279e9'}
def read(path,meta):
 raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest()==meta['binary_sha256'];a=array('I');a.frombytes(raw)
 if sys.byteorder!='little':a.byteswap()
 return a
def audit(mp):
 meta=load(mp);g=meta['local_graph'];frozen=load(R/'benchmarks/graphs/transformer-b4-t128.json');assert digest(g)==meta['local_graph_sha256'] and digest(frozen)==meta['full_graph_sha256'];assert g['nodes']==frozen['nodes'][:14] and g['inputs']==frozen['inputs'] and g['outputs']==['b0_residual2'];ns=g['nodes'];idx={v['id']:i for i,v in enumerate(ns)};width=meta['row_width'];assert width==8192 and meta['live_nodes']==[v['id'] for v in ns[:13]] and meta['phases']==[dict(down_seen=False,output_seen=False),dict(down_seen=True,output_seen=False)];cu=math.gcd(*(v['cost'] for v in ns));assert cu==meta['cost_unit'];a=read(mp.parent/meta['binary_file'],meta);assert len(a)==2*width;cap=meta['cap_bytes'];mask=lambda names:sum(1<<idx[x] for x in names if x in idx);dep=[mask(v['deps']) for v in ns];bpath=mp.parent/meta['backward_metadata'];bm=load(bpath);assert bm['cap_bytes']==cap and bm['local_graph_sha256']==meta['local_graph_sha256'] and bm['cost_unit']==cu;b=read(bpath.parent/bm['binary_file'],bm);zero=bm['done_masks'].index(0)*bm['row_width'];INF=(1<<32)-1;mem=[sum(v['bytes'] for v in g['inputs'])]*width
 for live in range(1,width):bit=live&-live;mem[live]=mem[live^bit]+ns[bit.bit_length()-1]['bytes']
 pred=[[] for _ in a];goals=[];finite=edges=0
 for phase in [0,1]:
  for live in range(width):
   at=phase*width+live;value=a[at]
   if mem[live]>cap or (phase==0 and live>>12&1):assert value==INF;continue
   finite+=value!=INF
   if phase==1 and live&dep[13]==dep[13] and mem[live]+ns[13]['bytes']<=cap:
    terminal=b[zero+(live&4095)]
    if terminal!=INF:
     assert value!=INF and value<=terminal
     if value==terminal:goals.append(at)
   for i,v in enumerate(ns[:13]):
    bit=1<<i
    if live&bit:nxt=phase*width+(live^bit);cost=0
    elif v['recomputable'] and live&dep[i]==dep[i] and mem[live|bit]<=cap:
     newphase=1 if i==12 else phase;nxt=newphase*width+(live|bit);cost=0 if i==12 and phase==0 else v['cost']//cu
    else:continue
    edges+=1;target=a[nxt]
    if target==INF:continue
    assert value!=INF and value<=cost+target,(phase,live,i,value,cost,target)
    if value==cost+target:pred[nxt].append(at)
 good=bytearray(len(a));queue=deque(goals)
 for at in goals:good[at]=1
 while queue:
  at=queue.popleft()
  for prev in pred[at]:
   if not good[prev]:good[prev]=1;queue.append(prev)
 assert sum(good)==finite
 return dict(valid_states=finite,edges=edges,tight_goal_states=len(goals))
def direct(g,cap,names,initial_phase):
 ns=g['nodes'];idx={v['id']:i for i,v in enumerate(ns)};mask=lambda names:sum(1<<idx[x] for x in names if x in idx);dep=[mask(v['deps']) for v in ns];req=[mask(v['backward_requires']) for v in ns];child=[sum(1<<j for j,v in enumerate(ns) if x['id'] in v['deps']) for x in ns];full=(1<<14)-1;mem=[sum(v['bytes'] for v in g['inputs'])]*(1<<14)
 for live in range(1,1<<14):bit=live&-live;mem[live]=mem[live^bit]+ns[bit.bit_length()-1]['bytes']
 initial=(mask(names),initial_phase,0,False);assert mem[initial[0]]<=cap and not(initial[0]>>13&1) and (initial_phase or not(initial[0]>>12&1));best={initial:0};queue=[(0,*initial)];expanded=0
 while queue:
  cost,live,phase,done,loss=heapq.heappop(queue);state=(live,phase,done,loss)
  if best[state]!=cost:continue
  expanded+=1
  if expanded>250000:raise RuntimeError('terminal direct state limit, no conclusion')
  if loss and done==full:return cost
  moves=[]
  if not loss and phase==2 and live>>13&1:moves.append(((live,phase,done,True),0))
  for i,v in enumerate(ns):
   bit=1<<i
   if live&bit:moves.append(((live^bit,phase,done,loss),0))
   elif v['recomputable'] and live&dep[i]==dep[i] and mem[live|bit]<=cap:
    if i==13 and phase==0:continue
    first=(i==12 and phase==0) or (i==13 and phase==1);newphase=phase+1 if first else phase;moves.append(((live|bit,newphase,done,loss),0 if first else v['cost']))
   if loss and not(done&bit) and done&child[i]==child[i] and live&req[i]==req[i]:moves.append(((live,phase,done|bit,loss),0))
  for target,extra in moves:
   value=cost+extra
   if value<best.get(target,10**100):best[target]=value;heapq.heappush(queue,(value,*target))
 return None
def negative_controls(mp):
 meta=load(mp);orig=read(mp.parent/meta['binary_file'],meta)
 kinds=['overstated','understated','phase0_down_live','invalid_memory','wrong_phase_metadata','wrong_full_graph_hash','rehashed_wrong_local_cost','wrong_terminal_cap']
 with tempfile.TemporaryDirectory(prefix='terminal-neg-',dir=mp.parent) as temp:
  root=Path(temp);back=load(mp.parent/meta['backward_metadata']);(root/meta['backward_metadata']).write_text(json.dumps(back));(root/back['binary_file']).write_bytes((mp.parent/back['binary_file']).read_bytes())
  for kind in kinds:
   forged=copy.deepcopy(meta);values=array('I',orig);at=8192+4096+256
   if kind=='overstated':values[at]+=1
   if kind=='understated':values[at]-=1
   if kind=='phase0_down_live':values[4096]=0
   if kind=='invalid_memory':values[8191]=0
   if kind=='wrong_phase_metadata':forged['phases'][0]['down_seen']=True
   if kind=='wrong_full_graph_hash':forged['full_graph_sha256']='0'*64
   if kind=='rehashed_wrong_local_cost':forged['local_graph']['nodes'][1]['cost']+=32768;forged['local_graph_sha256']=digest(forged['local_graph'])
   if kind=='wrong_terminal_cap':changed=copy.deepcopy(back);changed['cap_bytes']+=131072;p=root/'wrong-cap.json';p.write_text(json.dumps(changed));forged['backward_metadata']=p.name
   if sys.byteorder!='little':values.byteswap()
   raw=values.tobytes();bp=root/(kind+'.bin');bp.write_bytes(raw);forged['binary_file']=bp.name;forged['binary_sha256']=hashlib.sha256(raw).hexdigest();fp=root/(kind+'.json');fp.write_text(json.dumps(forged))
   try:audit(fp)
   except (AssertionError,ValueError,KeyError):continue
   raise AssertionError('accepted terminal negative '+kind)
 return len(kinds)

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--repo',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);parser.add_argument('--cap-units',type=int,choices=[9,10,11,12],action='append');args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True)
 global R,load,digest
 R=args.repo.resolve();sys.path.insert(0,str(R));from verifier import load,digest,validate_graph
 replay_pdb.load=load;replay_pdb.digest=digest;replay_pdb.validate_graph=validate_graph
 from pattern_db import PatternDB
 from terminal_phase_db import TerminalPhaseDB
 frozen=load(R/'benchmarks/graphs/transformer-b4-t128.json');assert digest(frozen)==replay_pdb.FULL_SHA;g=copy.deepcopy(frozen);g['nodes']=g['nodes'][:14];g['outputs']=['b0_residual2'];g['id']='transformer-b4-t128-local-backward-pattern';results=[]
 for capu in args.cap_units or [9,10,11,12]:
  cap=capu*g['inputs'][0]['bytes'];back=PatternDB(g,cap).build(seconds=30,states=1000000);bp=args.out/f'b4-backward-pdb-cap{capu}.json';bm=back.write(bp,digest(frozen));assert bm['binary_sha256']==BACK_HASH[capu];back_audit=replay_pdb.audit_backward(bp,frozen)
  db=TerminalPhaseDB(g,cap,back).build(seconds=30);mp=args.out/f'b4-terminal-phase-pdb-cap{capu}.json';meta=db.write(mp,bp.name,digest(frozen));assert meta['binary_sha256']==TERMINAL_HASH[capu];terminal_audit=audit(mp)
  fixtures=[(0,[]),(0,['b0_up','b0_gelu']),(0,['b0_up','b0_gelu','b0_residual1']),(0,['b0_context']),(1,[]),(1,['b0_up','b0_gelu']),(1,['b0_gelu','b0_down']),(1,['b0_down','b0_residual1'])];checked=0
  for phase,names in fixtures:
   if sum(v['bytes'] for v in g['inputs'])+sum(v['bytes'] for v in g['nodes'] if v['id'] in names)>cap:continue
   want=direct(g,cap,names,phase);got=db.value(names,phase);assert got==want,(capu,phase,names,got,want);checked+=1
  result=dict(status='PASS',cap_units=capu,backward_binary_sha256=bm['binary_sha256'],terminal_binary_sha256=meta['binary_sha256'],backward_audit=back_audit,terminal_audit=terminal_audit,direct_controls=checked,negative_controls=negative_controls(mp));results.append(result);print(json.dumps(result,sort_keys=True),flush=True)
 print(json.dumps(dict(status='PASS',capacities=len(results),direct_controls=sum(r['direct_controls'] for r in results),negative_controls=sum(r['negative_controls'] for r in results)),sort_keys=True),flush=True)

if __name__=='__main__':main()

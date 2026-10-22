"""Check a closed label set for the pinned, favorable 10-chunk tail problem.

Independent of the C++ search, hash table, queue and relaxation implementation.
This checks finite reduced-state closure. The mathematical reduction and safe
normalization arguments remain explicit proof obligations in the result package.
"""
import argparse
from array import array
import hashlib
import itertools
import json
from pathlib import Path
import struct
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from verifier import digest, validate_graph

GRAPH_HASH='7d60aaf32c25d4d000872f9d317cdb0cbc71c929307eb69faf7e974c795d5854'
FULL=(1<<56)-1
LIMIT=956301312
INF=(1<<32)-1

def read_json(path):
    return json.loads(Path(path).read_text())

def table(meta_path):
    meta=read_json(meta_path)
    raw=Path(meta_path).with_name(meta['binary_file']).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==meta['binary_sha256']
    values=array('I'); values.frombytes(raw)
    if sys.byteorder!='little':values.byteswap()
    assert values.itemsize==4
    return meta,values

def check(input_path,label_path,back_path,demand_path,sample=None):
    began=time.monotonic()
    g=read_json(ROOT/'benchmarks/graphs/transformer-b4-t128.json')
    validate_graph(g);assert digest(g)==GRAPH_HASH
    ns=g['nodes'];names=[v['id'] for v in ns];idx={name:i for i,name in enumerate(names)}
    mask=lambda xs:sum(1<<idx[x] for x in xs if x in idx)
    size=[v['bytes']//131072 for v in ns]
    dep=[mask(v['deps']) for v in ns]
    req=[mask(v['backward_requires']) for v in ns]
    child=[mask(v['id'] for v in ns if u['id'] in v['deps']) for u in ns]
    costs=[v['cost'] for v in ns]
    assert len(ns)==56 and all(s in (1,4) for s in size)
    assert g['inputs']==[{'id':'x','bytes':131072}]
    outputs=mask(g['outputs'])
    small=sum(1<<i for i,s in enumerate(size) if s==1)
    big=FULL^small
    mem=lambda live:1+(live&small).bit_count()+4*(live&big).bit_count()
    lines=Path(input_path).read_text().splitlines()
    header=lines[0].split()
    assert len(header)==8
    assert list(map(int,header[:4]))==[56,1,10,LIMIT]
    assert int(header[7])==0,'restricted-demand search is not a proof'
    for i,v in enumerate(ns):
        expected=[v['id'],str(size[i]),str(costs[i]),str(dep[i]),str(req[i]),str(child[i]),str(int(v['recomputable']))]
        assert lines[i+1].split()==expected
    order=list(map(int,lines[57].split()))
    assert sorted(order)==list(range(56))
    assert set(order[:54])==set(range(54)) and order[54:]==[54,55]
    assert int(lines[58])==outputs and int(lines[59])==39
    forced=mask(['b3_up','b3_gelu'])
    options=[i for i in range(54) if size[i]==1]
    seeds={(forced,0,54,0)}|{(forced|(1<<i),0,54,0) for i in options}
    actual={tuple(map(int,line.split())) for line in lines[60:99]}
    assert actual==seeds and len(actual)==39
    bmeta,back=table(back_path);dmeta,demand=table(demand_path)
    assert bmeta['full_graph_sha256']==dmeta['full_graph_sha256']==GRAPH_HASH
    assert bmeta['cap_bytes']==dmeta['cap_bytes']==1310720
    assert bmeta['local_graph']==dmeta['local_graph']
    local=bmeta['local_graph']
    assert digest(local)==bmeta['local_graph_sha256']==dmeta['local_graph_sha256']
    assert local['inputs']==g['inputs'] and local['nodes']==ns[:14]
    for block in range(4):
        rename={v['id']:v['id'].replace('b0_',f'b{block}_',1) for v in ns[:14]}
        rename['x']='x' if block==0 else f'b{block-1}_residual2'
        for j,v in enumerate(local['nodes']):
            expected=dict(v,id=rename[v['id']],deps=[rename[x] for x in v['deps']],backward_requires=[rename[x] for x in v['backward_requires']])
            assert expected==ns[14*block+j]
    assert bmeta['live_nodes']==names[:12] and bmeta['row_width']==4096
    assert dmeta['live_nodes']==names[:14] and dmeta['row_width']==16384
    assert bmeta['cost_unit']==dmeta['cost_unit']==32768
    done_row={value:i for i,value in enumerate(bmeta['done_masks'])}
    assert list(map(int,lines[99].split()))==[len(done_row),4096,32768]
    assert list(map(int,lines[100].split()))==bmeta['done_masks']
    assert list(map(int,lines[101].split()))==[16384,32768]
    assert len(lines)==102
    assert len(back)==4096*len(done_row) and len(demand)==16384
    prefix=[0]
    for i in order:prefix.append(prefix[-1]|(1<<i))
    closure_cache={};ready_cache={}
    def needs(done):
        if done not in closure_cache:
            required=0
            for i in range(56):
                if not done>>i&1:required|=req[i]
            useful=required
            for i in range(55,-1,-1):
                if useful>>i&1:useful|=dep[i]
            closure_cache[done]=(required,useful)
        return closure_cache[done]
    def ready(done):
        if done not in ready_cache:
            ready_cache[done]=[i for i in range(56) if not done>>i&1 and child[i]&done==child[i]]
        return ready_cache[done]
    def normalize(live,done,m):
        if m==56 and live&outputs==outputs:m=57
        if m==57:
            while True:
                newly=sum(1<<i for i in ready(done) if live&req[i]==req[i])
                if not newly:break
                done|=newly
            live&=needs(done)[1]
        return live,done,m
    local_cost=[0]*16384
    for bits in range(1,16384):
        bit=bits&-bits;local_cost[bits]=local_cost[bits^bit]+costs[bit.bit_length()-1]
    def heuristic(live,done,m):
        seen=prefix[min(m,56)]
        required=needs(done)[0]
        if m<=56:required|=(FULL^seen)|outputs
        absent=required&~live
        # Pull through every absent value; a resident value terminates its chain.
        for i in range(55,-1,-1):
            if absent>>i&1:absent|=dep[i]&~live
        repeat=absent&seen
        total=0
        for block in range(4):
            shift=14*block
            repeated=repeat>>shift&16383
            lower=local_cost[repeated]
            localdone=done>>shift&16383
            if (seen>>shift&4095)==4095:
                assert localdone in done_row
                value=back[done_row[localdone]*4096+(live>>shift&4095)]
                if value==INF:return LIMIT+1
                lower=max(lower,value*32768+local_cost[repeated&12288])
            if block<3 and (seen>>shift&16383)==16383 and localdone==0 and not(done>>(shift+14)&1):
                value=demand[live>>shift&16383]
                if value==INF:return LIMIT+1
                lower=max(lower,value*32768)
            total+=lower
        return total
    raw=Path(label_path).read_bytes()
    assert len(raw)%24==0
    labels={}
    for lp,done,cost in struct.iter_unpack('<QQQ',raw):
        assert (lp,done) not in labels
        labels[lp,done]=cost
    assert len(labels)==419463,'unexpected certificate label count'
    for live,done,m,cost in seeds:
        key=(live|(m<<56),done)
        assert labels.get(key, LIMIT+1)<=cost or heuristic(live,done,m)>LIMIT-cost
    checked=edges=pruned=0
    for (lp,done),spent in labels.items():
        live=lp&FULL;m=lp>>56
        assert spent<=LIMIT and m in (54,55,57) and done&~FULL==0
        assert live&~prefix[min(m,56)]==0 and mem(live)<=10
        assert normalize(live,done,m)==(live,done,m)
        assert done!=FULL,'certificate contains a feasible goal'
        assert heuristic(live,done,m)<=LIMIT-spent
        seen=prefix[min(m,56)]
        for i in range(56):
            bit=1<<i
            if (live|done)&bit or live&dep[i]!=dep[i]:continue
            old=bool(seen&bit)
            if not old and (m>=56 or order[m]!=i):continue
            cost=spent+(costs[i] if old else 0)
            if cost>LIMIT:continue
            deficit=mem(live)+size[i]-10
            available=live&~dep[i]
            if deficit<=0:evictions=(0,)
            else:
                assert deficit<=4
                large=[1<<j for j in range(56) if available&big&(1<<j)]
                units=[1<<j for j in range(56) if available&small&(1<<j)]
                evictions=itertools.chain(large,(sum(xs) for xs in itertools.combinations(units,deficit)))
            for gone in evictions:
                targetlive,targetdone,targetm=normalize((live&~gone)|bit,done,m+int(not old))
                assert mem((live&~gone)|bit)<=10
                key=(targetlive|(targetm<<56),targetdone)
                edges+=1
                if key in labels:
                    assert labels[key]<=cost,('edge violates label closure',key,cost,labels[key])
                else:
                    assert heuristic(targetlive,targetdone,targetm)>LIMIT-cost,('uncovered edge',key,cost)
                    pruned+=1
        checked+=1
        if sample and checked>=sample:break
    result=dict(status='SAMPLE_PASS' if sample else 'PASS',scope='closed reduced-state certificate; author-team implementation cross-check',
                checked_labels=checked,total_labels=len(labels),edges_checked=edges,absent_targets_pruned=pruned,
                labels_sha256=hashlib.sha256(raw).hexdigest(),seconds=time.monotonic()-began)
    print(json.dumps(result),flush=True)
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('input');p.add_argument('labels');p.add_argument('backward_pdb');p.add_argument('demand_pdb')
    p.add_argument('--sample',type=int)
    a=p.parse_args()
    check(a.input,a.labels,a.backward_pdb,a.demand_pdb,a.sample)

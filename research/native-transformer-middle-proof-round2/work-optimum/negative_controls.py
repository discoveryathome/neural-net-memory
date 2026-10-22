"""Challenge seed coverage, label costs, goals, domain and bound table binding."""
import argparse,itertools,json,shutil,struct,tempfile
from pathlib import Path
from check_closed import check

def run(repo,out,cap=13,tables=None):
    assert cap in (13,14)
    repo=Path(repo).resolve();out=Path(out).resolve();inp=out/f'critical-cap{cap}.input';labels=out/'closed-labels.bin';tables=out/'pdb' if tables is None else Path(tables).resolve();budget={13:421494783,14:355270655}[cap]
    receipt=[]
    def rejected(name,fn,reason=None):
        try:fn()
        except (AssertionError,ValueError,KeyError) as error:
            if reason is not None:assert reason in str(error),(name,str(error))
            receipt.append(dict(control=name,status='REJECTED',reason=str(error)))
        else:raise AssertionError('Accepted forged proof '+name)
    with tempfile.TemporaryDirectory(prefix='closed-proof-negative-',dir=out) as tmp:
        p=Path(tmp);raw=bytearray(labels.read_bytes());found=False
        for at in range(0,len(raw),24):
            lp,done,cost=struct.unpack_from('<QQQ',raw,at)
            if lp>>56==54 and done==0 and cost==0:
                struct.pack_into('<Q',raw,at+16,1);found=True;break
        assert found;forged=p/'positive-cost-seed.bin';forged.write_bytes(raw)
        rejected('surviving seed mislabeled cost one',lambda:check(repo,inp,forged,tables,sample=1))
        text=inp.read_text().splitlines();header=text[0].split();header[7]='1';text[0]=' '.join(header);restricted=p/'restricted.input';restricted.write_text('\n'.join(text)+'\n')
        rejected('restricted old-forward domain presented as exhaustive',lambda:check(repo,restricted,labels,tables,sample=1))
        text=inp.read_text().splitlines();count=int(text[59]);text[59]=str(count-1);del text[60+count-1];missing=p/'missing-four-unit-seed.input';missing.write_text('\n'.join(text)+'\n')
        rejected('last weighted optional cut omitted',lambda:check(repo,missing,labels,tables,sample=1))
        goal=p/'forged-affordable-goal.bin';goal.write_bytes(struct.pack('<QQQ',57<<56,(1<<56)-1,0)+labels.read_bytes())
        rejected('affordable complete-backward goal inserted',lambda:check(repo,inp,goal,tables,sample=1))
        copied=p/'tables';shutil.copytree(tables,copied)
        binary=copied/'b4-output-demand-pdb-cap10.bin';changed=bytearray(binary.read_bytes());changed[0]^=1;binary.write_bytes(changed)
        rejected('changed projected-cap demand values with original digest',lambda:check(repo,inp,labels,copied,sample=1))
        shutil.rmtree(copied);shutil.copytree(tables,copied)
        meta=copied/'b4-output-demand-pdb-cap10.json';data=json.loads(meta.read_text());data['binary_file']='redirected.bin';shutil.copyfile(copied/'b4-output-demand-pdb-cap10.bin',copied/'redirected.bin');meta.write_text(json.dumps(data))
        rejected('demand metadata redirects consumed canonical table',lambda:check(repo,inp,labels,copied,sample=1))
        shutil.rmtree(copied);shutil.copytree(tables,copied)
        meta=copied/'b4-output-demand-pdb-cap10.json';data=json.loads(meta.read_text());data['cost_unit']+=1;meta.write_text(json.dumps(data))
        rejected('projected demand cost unit changed',lambda:check(repo,inp,labels,copied,sample=1))
        # These forgeries preserve all table/domain/root checks. Find a real
        # tight positive-cost nonseed edge, then challenge edge domination.
        rows=list(struct.iter_unpack('<QQQ',labels.read_bytes()));lookup={(lp,d):g for lp,d,g in rows};graph=json.loads((repo/'benchmarks/graphs/transformer-b4-t128.json').read_text());ns=graph['nodes'];index={v['id']:i for i,v in enumerate(ns)};full=(1<<56)-1
        mask=lambda xs:sum(1<<index[x] for x in xs if x in index)
        dep=[mask(v['deps']) for v in ns];req=[mask(v['backward_requires']) for v in ns];child=[mask(v['id'] for v in ns if u['id'] in v['deps']) for u in ns];sizes=[v['bytes']//131072 for v in ns];small=sum(1<<i for i,s in enumerate(sizes) if s==1);big=full^small
        def normalize(live,done,m):
            if m==56 and live>>55&1:m=57
            if m==57:
                while True:
                    ready=sum(1<<i for i in range(56) if not(done>>i&1) and done&child[i]==child[i] and live&req[i]==req[i])
                    if not ready:break
                    done|=ready
                useful=0
                for i in range(56):
                    if not(done>>i&1):useful|=req[i]
                for i in reversed(range(56)):
                    if useful>>i&1:useful|=dep[i]
                live&=useful
            return live|(m<<56),done
        chosen=None
        for lp,done,spent in rows[:(1000 if cap==13 else len(rows))]:
            live=lp&full;m=lp>>56;seen=(1<<min(m,56))-1
            for i in range(56):
                bit=1<<i
                if (live|done)&bit or live&dep[i]!=dep[i]:continue
                old=bool(seen&bit)
                if not old and (m>=56 or m!=i):continue
                cost=spent+(ns[i]['cost'] if old else 0)
                if not cost or cost>budget:continue
                deficit=1+(live&small).bit_count()+4*(live&big).bit_count()+sizes[i]-cap;available=live&~dep[i]
                if deficit<=0:evictions=[0]
                else:
                    units=[1<<j for j in range(56) if available&small&(1<<j)];large=[1<<j for j in range(56) if available&big&(1<<j)]
                    evictions=itertools.chain(large,(sum(xs) for xs in itertools.combinations(units,deficit)))
                for gone in evictions:
                    target=normalize((live&~gone)|bit,done,m+int(not old))
                    if target!=(lp,done) and lookup.get(target)==cost:
                        chosen=(lp,done,spent,target,cost);break
                if chosen:break
            if chosen:break
        assert chosen is not None
        lp,d,g,target,cost=chosen;ordered=[(lp,d,g)]+[row for row in rows if row[:2]!=(lp,d)]
        for name,reason in [('raise tight nonseed target cost','edge violates label closure'),('omit tight nonseed target','uncovered edge')]:
            changed=[(a,b,c+1 if (a,b)==target else c) for a,b,c in ordered] if name.startswith('raise') else [row for row in ordered if row[:2]!=target]
            forged=p/(name.replace(' ','-')+'.bin');forged.write_bytes(b''.join(struct.pack('<QQQ',*row) for row in changed))
            rejected(name,lambda forged=forged:check(repo,inp,forged,tables,sample=1),reason)
    result=dict(status='PASS',cap_units=cap,forged_proofs_rejected=receipt)
    (out/'proof-negatives.json').write_text(json.dumps(result,indent=2)+'\n');return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--repo',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);parser.add_argument('--tables',type=Path);parser.add_argument('--cap',type=int,choices=[13,14],default=13);args=parser.parse_args()
    print(json.dumps(run(args.repo,args.out,args.cap,args.tables)),flush=True)

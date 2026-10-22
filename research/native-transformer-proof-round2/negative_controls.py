"""Meaningful forged-proof controls for the separately coded closure checker."""
import argparse,json,struct
from pathlib import Path
from check_closed import check

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--out',type=Path,default=Path(__file__).resolve().parent/'generated')
P=parser.parse_args().out
inp=P/'critical-cap10.input'
labels=P/'closed-labels.bin'
back=P/'pdb/b4-backward-pdb-cap10.json'
demand=P/'pdb/b4-output-demand-pdb-cap10.json'
out=P/'negative';out.mkdir(exist_ok=True)
def rejected(name,fn):
    try:fn()
    except AssertionError:return {'control':name,'status':'REJECTED'}
    raise AssertionError('forgery accepted: '+name)

rows=[]
text=inp.read_text().splitlines()
seed=tuple(map(int,text[60].split()));live,done,m,cost=seed
target=(live|(m<<56),done)
raw=bytearray(labels.read_bytes());found=False
for offset in range(0,len(raw),24):
    lp,d,c=struct.unpack_from('<QQQ',raw,offset)
    if (lp,d)==target:
        assert c==0
        struct.pack_into('<Q',raw,offset+16,1);found=True;break
assert found
forged=out/'positive-cost-seed.bin';forged.write_bytes(raw)
rows.append(rejected('initial seed mislabeled as costing one unit',lambda:check(inp,forged,back,demand,sample=1)))
restricted=out/'restricted.input';head=text[0].split();head[7]='1';text[0]=' '.join(head)
restricted.write_text('\n'.join(text)+'\n')
rows.append(rejected('restricted demand domain presented as exhaustive',lambda:check(restricted,labels,back,demand,sample=1)))
meta=json.loads(back.read_text());table=back.with_name(meta['binary_file'])
bad=bytearray(table.read_bytes());bad[0]^=1
(out/meta['binary_file']).write_bytes(bad)
forgedmeta=out/back.name;forgedmeta.write_text(json.dumps(meta))
rows.append(rejected('changed pattern value with original digest',lambda:check(inp,labels,forgedmeta,demand,sample=1)))
print(json.dumps({'status':'PASS','forged_proofs_rejected':rows}))

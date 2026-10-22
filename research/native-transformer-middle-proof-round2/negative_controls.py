"""Reject forged proof inputs using the separately authored closure checker."""
import argparse,json,struct
from pathlib import Path
from check_closed import check

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--out',type=Path,default=Path(__file__).resolve().parent/'generated')
P=parser.parse_args().out
inp=P/'critical-cap12.input';labels=P/'closed-labels.bin';tables=P/'pdb'
back=tables/'b4-backward-pdb-cap12.json';demand=tables/'b4-output-demand-pdb-cap12.json';terminal=tables/'b4-terminal-phase-pdb-cap12.json'
out=P/'negative';out.mkdir(exist_ok=True)
def rejected(name,fn):
    try:fn()
    except AssertionError:return dict(control=name,status='REJECTED')
    raise AssertionError('forgery accepted: '+name)
def run(i,l,b=back):return check(i,l,b,demand,terminal,tables,sample=1)
rows=[];raw=bytearray(labels.read_bytes());found=False
for offset in range(0,len(raw),24):
    lp,done,cost=struct.unpack_from('<QQQ',raw,offset)
    if lp>>56==54 and done==0 and cost==0:
        struct.pack_into('<Q',raw,offset+16,1);found=True;break
assert found
forged=out/'positive-cost-seed.bin';forged.write_bytes(raw)
rows.append(rejected('a surviving initial seed mislabeled as cost one',lambda:run(inp,forged)))
text=inp.read_text().splitlines();header=text[0].split();header[7]='1';text[0]=' '.join(header)
restricted=out/'restricted.input';restricted.write_text('\n'.join(text)+'\n')
rows.append(rejected('restricted-demand domain presented as exhaustive',lambda:run(restricted,labels)))
meta=json.loads(back.read_text());bad=bytearray(back.with_name(meta['binary_file']).read_bytes());bad[0]^=1
(out/meta['binary_file']).write_bytes(bad);forgedmeta=out/back.name;forgedmeta.write_text(json.dumps(meta))
rows.append(rejected('changed pattern value with original digest',lambda:run(inp,labels,forgedmeta)))
meta=json.loads(back.read_text())
meta['binary_file']='different-table.bin'
(out/meta['binary_file']).write_bytes(back.with_name(back.stem+'.bin').read_bytes())
forgedmeta.write_text(json.dumps(meta))
rows.append(rejected('metadata redirects the consumed canonical table',lambda:run(inp,labels,forgedmeta)))
print(json.dumps(dict(status='PASS',forged_proofs_rejected=rows)),flush=True)

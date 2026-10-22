"""Reconstruct all69b4 auxiliary Pareto upper points and verify every trace."""
import argparse
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
from curve_constructor import run,ROOT

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo',type=Path,default=ROOT)
    p.add_argument('--out',type=Path,default=HERE/'generated');a=p.parse_args()
    result=run(a.repo,a.out)
    import json
    print(json.dumps(dict(status=result['status'],points=len(result['rows']),seconds=result['seconds'],negative_controls=result['negative_controls'],original_budget_replays=[r['cap_units'] for r in result['rows'] if 'original_budget_replay' in r],zero_work_cap_units=result['rows'][-1]['cap_units'])),flush=True)

if __name__=='__main__':main()

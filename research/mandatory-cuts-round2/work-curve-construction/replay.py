"""Reconstruct and verify all29 auxiliary two-block Pareto upper points."""
import argparse,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
from b2_curve_constructor import run,ROOT

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repo',type=Path,default=ROOT);p.add_argument('--out',type=Path,default=HERE/'generated');a=p.parse_args()
    result=run(a.repo,a.out)
    print(json.dumps(dict(status=result['status'],points=len(result['rows']),seconds=result['seconds'],negative_controls=result['negative_controls'],original_budget_replays=[r['original_budget_replays'] for r in result['rows'] if 'original_budget_replays' in r],zero_work_cap_units=result['rows'][-1]['cap_units'])),flush=True)

if __name__=='__main__':main()

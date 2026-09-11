"""Fallback empirical validation when the authoritative confidence cutoff is unavailable.

Rule:
1) infer ONE cutoff from TRAIN candidate confidences to hit the published train count;
2) freeze it;
3) apply exactly the same cutoff to TEST, without tuning;
4) report whether the independently resulting test count is compatible with Zhu's 7,805.

This is deliberately weaker than recovering the authors' exact rule, but much stronger
than fitting train and test counts independently.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np
from herrmann_data import load_manifest
from paper_targets import ZHU_PROTOCOL


def vals(path):
    recs=load_manifest(path)
    a=np.asarray([r.median_confidence for r in recs],dtype=object)
    if any(x is None for x in a):
        raise SystemExit(f'{path}: every candidate must contain median_confidence')
    return np.asarray(a,dtype=np.float64)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--train-candidates',required=True)
    ap.add_argument('--test-candidates',required=True)
    ap.add_argument('--out')
    ap.add_argument('--test-count-tolerance',type=int,default=0,
                    help='0 requires exact independent reproduction of 7805')
    args=ap.parse_args()
    tr=vals(args.train_candidates); te=vals(args.test_candidates)
    nt=ZHU_PROTOCOL['train_stack_patches']; expected_test=ZHU_PROTOCOL['test_stack_patches']
    if len(tr)<nt: raise SystemExit('not enough train candidates')
    s=np.sort(tr)[::-1]
    cutoff=float(s[nt-1])
    train_ge=int((tr>=cutoff).sum()); train_gt=int((tr>cutoff).sum())
    test_ge=int((te>=cutoff).sum()); test_gt=int((te>cutoff).sum())
    candidates=[]
    for op,train_count,test_count in [('>=',train_ge,test_ge),('>',train_gt,test_gt)]:
        candidates.append({
            'operator':op,'cutoff':cutoff,
            'train_count':train_count,'train_target':nt,'train_exact':train_count==nt,
            'test_count':test_count,'test_target':expected_test,
            'test_abs_error':abs(test_count-expected_test),
            'test_pass':abs(test_count-expected_test)<=args.test_count_tolerance,
        })
    out={
        'method':'train-derived single frozen threshold; independent test cross-check',
        'train_candidate_count':len(tr),'test_candidate_count':len(te),
        'cutoff_at_train_target_rank':cutoff,
        'results':candidates,
        'interpretation':'EMPIRICAL_ONLY; does not replace authoritative protocol provenance',
        'pass':any(x['train_exact'] and x['test_pass'] for x in candidates),
    }
    text=json.dumps(out,indent=2); print(text)
    if args.out: Path(args.out).write_text(text+'\n')
    if not out['pass']: raise SystemExit(2)

if __name__=='__main__': main()

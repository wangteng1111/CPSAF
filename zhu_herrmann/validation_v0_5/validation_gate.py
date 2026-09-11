from __future__ import annotations
import argparse, json, subprocess, sys
from pathlib import Path
from herrmann_data import load_manifest
from paper_targets import ZHU_PROTOCOL, ZHU_RELATIVE_LABEL_SINGLE_STEP

DEFAULT_TOL = {
    'exact':0.02, 'within1':0.02, 'within2':0.02, 'within4':0.02,
    'MAE':0.10, 'RMSE':0.20,
}

def manifest_gate(path, expected, require_conf=True):
    recs=load_manifest(path); conf=[r.median_confidence for r in recs]
    coverage=sum(x is not None for x in conf)/max(1,len(recs))
    return {
        'count':len(recs), 'expected':expected,
        'count_pass':len(recs)==expected,
        'confidence_coverage':coverage,
        'confidence_pass':(coverage==1.0) if require_conf else True,
    }

def metrics_gate(path, tol):
    d=json.loads(Path(path).read_text())
    m=d.get('metrics',d)
    aliases={'exact':'exact','within1':'within1','within2':'within2','within4':'within4','MAE':'MAE','RMSE':'RMSE'}
    rows={}; ok=True
    for k,tgt in ZHU_RELATIVE_LABEL_SINGLE_STEP.items():
        val=float(m[aliases[k]])
        err=abs(val-tgt); p=err<=tol[k]; ok &= p
        rows[k]={'value':val,'target':tgt,'abs_error':err,'tolerance':tol[k],'pass':p}
    return {'pass':bool(ok),'rows':rows}

def main():
    ap=argparse.ArgumentParser(description='Strict pre-CPSAF validation gate')
    ap.add_argument('--train-manifest')
    ap.add_argument('--test-manifest')
    ap.add_argument('--eval-json')
    ap.add_argument('--allow-missing-data', action='store_true')
    ap.add_argument('--out')
    args=ap.parse_args()
    out={'protocol':'Zhu/Herrmann stage-1 scientific validation','gates':{}}
    here=Path(__file__).parent
    tests=[]
    for f in ['test_v02.py','test_v03.py','test_v04.py']:
        r=subprocess.run([sys.executable,str(here/f)],cwd=here,capture_output=True,text=True)
        tests.append({'script':f,'returncode':r.returncode,'stdout':r.stdout.strip(),'stderr':r.stderr.strip(),'pass':r.returncode==0})
    out['gates']['protocol_unit_tests']={'pass':all(x['pass'] for x in tests),'details':tests}
    if args.train_manifest:
        out['gates']['train_manifest']=manifest_gate(args.train_manifest,ZHU_PROTOCOL['train_stack_patches'])
    else:
        out['gates']['train_manifest']={'pass':False,'status':'MISSING'}
    if args.test_manifest:
        out['gates']['test_manifest']=manifest_gate(args.test_manifest,ZHU_PROTOCOL['test_stack_patches'])
    else:
        out['gates']['test_manifest']={'pass':False,'status':'MISSING'}
    for k in ['train_manifest','test_manifest']:
        g=out['gates'][k]
        if 'count_pass' in g: g['pass']=bool(g['count_pass'] and g['confidence_pass'])
    if args.eval_json:
        out['gates']['published_metric_reproduction']=metrics_gate(args.eval_json,DEFAULT_TOL)
    else:
        out['gates']['published_metric_reproduction']={'pass':False,'status':'MISSING'}
    required=list(out['gates'].values())
    out['scientifically_validated']=all(g.get('pass',False) for g in required)
    out['status']='PASS' if out['scientifically_validated'] else ('BLOCKED' if args.allow_missing_data else 'FAIL')
    text=json.dumps(out,indent=2)
    print(text)
    if args.out: Path(args.out).write_text(text+'\n')
    if not out['scientifically_validated'] and not args.allow_missing_data:
        raise SystemExit(2)

if __name__=='__main__': main()

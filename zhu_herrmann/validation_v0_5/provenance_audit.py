from __future__ import annotations
import argparse, json, math
from pathlib import Path
from source_provenance import SOURCES


def grid_count(H,W,ph,pw,stride):
    if H<ph or W<pw: return 0
    return (math.floor((H-ph)/stride)+1)*(math.floor((W-pw)/stride)+1)


def pct(a,b):
    return float(a/b) if b else None


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--json-out', default=None)
    args=ap.parse_args()
    H,W=SOURCES['learnaf_public_readme']['facts']['raw_up_pd_hw']
    ph,pw=SOURCES['zhu_paper']['facts']['patch_hw']
    n40=grid_count(H,W,ph,pw,40)
    n96=grid_count(H,W,ph,pw,96)
    hp=SOURCES['herrmann_paper']['facts']; zp=SOURCES['zhu_paper']['facts']; rp=SOURCES['learnaf_public_readme']['facts']
    out={
        'source_image_hw':[H,W],
        'fully_contained_grid':{
            'stride40_per_stack':n40,
            'stride96_per_stack':n96,
        },
        'herrmann_paper_split':{
            'train_candidates_stride40':hp['paper_train_stacks']*n40,
            'test_candidates_stride40':hp['paper_test_stacks']*n40,
            'train_retention_fraction':pct(hp['paper_train_patches'],hp['paper_train_stacks']*n40),
            'test_retention_fraction':pct(hp['paper_test_patches'],hp['paper_test_stacks']*n40),
        },
        'zhu_counts_if_paper_510_stacks':{
            'train_candidates_stride96':hp['paper_train_stacks']*n96,
            'test_candidates_stride96':hp['paper_test_stacks']*n96,
            'train_retention_fraction':pct(zp['train_spatial_patches'],hp['paper_train_stacks']*n96),
            'test_retention_fraction':pct(zp['test_spatial_patches'],hp['paper_test_stacks']*n96),
            'overall_retention_fraction':pct(zp['train_spatial_patches']+zp['test_spatial_patches'],(hp['paper_train_stacks']+hp['paper_test_stacks'])*n96),
        },
        'zhu_counts_if_public_release_398_stacks':{
            'train_candidates_stride96':rp['public_train_sweeps']*n96,
            'test_candidates_stride96':rp['public_test_sweeps']*n96,
            'train_required_retention_fraction':pct(zp['train_spatial_patches'],rp['public_train_sweeps']*n96),
            'test_required_retention_fraction':pct(zp['test_spatial_patches'],rp['public_test_sweeps']*n96),
            'overall_required_retention_fraction':pct(zp['train_spatial_patches']+zp['test_spatial_patches'],(rp['public_train_sweeps']+rp['public_test_sweeps'])*n96),
        },
        'blockers':[
            'Paper says 460/50 stacks, official public README says 351/47 sweeps.',
            'Authoritative indexed text confirms confidence filtering but not the numeric threshold.',
            'Therefore a public-release manifest matching 68187/7805 is not by itself proof of protocol fidelity.',
        ],
    }
    txt=json.dumps(out,indent=2)
    print(txt)
    if args.json_out: Path(args.json_out).write_text(txt+'\n')

if __name__=='__main__': main()

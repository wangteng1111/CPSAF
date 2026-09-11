from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

import cv2

from herrmann_data import discover_captures, _find_conf, _find_depth_png
from source_provenance import SOURCES


def slice_count(side_base: Path, capture: str) -> int:
    p = side_base / capture
    if not p.exists():
        return 0
    return sum(1 for d in p.iterdir() if d.is_dir() and d.name.startswith('slice_'))


def first_png(side_base: Path, capture: str) -> Optional[Path]:
    d = side_base / capture / 'slice_00'
    if not d.exists():
        return None
    xs = sorted(d.glob('*.png'))
    return xs[0] if xs else None


def classify_count(split: str, n: int) -> str:
    hp = SOURCES['herrmann_paper']['facts']
    rp = SOURCES['learnaf_public_readme']['facts']
    paper = hp[f'paper_{split}_stacks']
    public = rp[f'public_{split}_sweeps']
    if n == paper:
        return 'MATCHES_PAPER_SPLIT'
    if n == public:
        return 'MATCHES_CURRENT_PUBLIC_RELEASE'
    return 'OTHER_OR_INCOMPLETE'


def audit(root: Path, split: str, full: bool = True) -> dict:
    use_up = (root / 'raw_up_left_pd').exists() and (root / 'raw_up_right_pd').exists()
    lbase = root / ('raw_up_left_pd' if use_up else 'raw_left_pd')
    rbase = root / ('raw_up_right_pd' if use_up else 'raw_right_pd')
    captures = discover_captures(root, use_upsampled=use_up)
    expected_hw = tuple(SOURCES['learnaf_public_readme']['facts']['raw_up_pd_hw' if use_up else 'raw_pd_hw'])

    capture_rows = []
    n_missing_depth = n_missing_conf = n_bad_slice = n_bad_hw = 0
    to_check = captures if full else captures[: min(10, len(captures))]
    for cap in to_check:
        nl = slice_count(lbase, cap)
        nr = slice_count(rbase, cap)
        bad_slice = nl != 49 or nr != 49
        n_bad_slice += int(bad_slice)

        depth_ok = True
        try:
            _find_depth_png(root, cap)
        except Exception:
            depth_ok = False
            n_missing_depth += 1

        conf_ok = _find_conf(root, cap) is not None
        n_missing_conf += int(not conf_ok)

        p = first_png(lbase, cap)
        hw = None
        hw_ok = False
        if p is not None:
            im = cv2.imread(str(p), cv2.IMREAD_UNCHANGED)
            if im is not None:
                hw = list(map(int, im.shape[:2]))
                hw_ok = tuple(hw) == expected_hw
        n_bad_hw += int(not hw_ok)

        capture_rows.append({
            'capture': cap,
            'left_slices': nl,
            'right_slices': nr,
            'slice49_pass': not bad_slice,
            'depth_present': depth_ok,
            'confidence_present': conf_ok,
            'representative_hw': hw,
            'expected_hw': list(expected_hw),
            'hw_pass': hw_ok,
        })

    profile = classify_count(split, len(captures))
    clean = (len(captures) > 0 and n_bad_slice == 0 and n_missing_depth == 0 and
             n_missing_conf == 0 and n_bad_hw == 0)
    paper_match = profile == 'MATCHES_PAPER_SPLIT'
    public_match = profile == 'MATCHES_CURRENT_PUBLIC_RELEASE'

    return {
        'root': str(root),
        'split': split,
        'using_upsampled_dp': use_up,
        'capture_count': len(captures),
        'capture_count_profile': profile,
        'paper_expected': SOURCES['herrmann_paper']['facts'][f'paper_{split}_stacks'],
        'public_release_expected': SOURCES['learnaf_public_readme']['facts'][f'public_{split}_sweeps'],
        'checked_capture_count': len(to_check),
        'missing_depth_count': n_missing_depth,
        'missing_confidence_count': n_missing_conf,
        'bad_49_slice_count': n_bad_slice,
        'bad_resolution_count': n_bad_hw,
        'structural_integrity_pass': clean,
        'paper_split_pass': paper_match,
        'public_release_match': public_match,
        'canonical_reproduction_ready': bool(clean and paper_match),
        'interpretation': (
            'Canonical Zhu/Herrmann reproduction can proceed to unfiltered manifest construction.'
            if clean and paper_match else
            'Dataset is structurally valid but matches the smaller public release; do not silently treat it as the 460/50 paper split.'
            if clean and public_match else
            'Dataset is incomplete, structurally inconsistent, or from an unrecognized split.'
        ),
        'captures': capture_rows,
    }


def main():
    ap = argparse.ArgumentParser(description='Audit mounted LearnAF data before manifest generation')
    ap.add_argument('--root', required=True)
    ap.add_argument('--split', choices=['train', 'test'], required=True)
    ap.add_argument('--sample-only', action='store_true', help='inspect at most ten captures')
    ap.add_argument('--out')
    ap.add_argument('--require-paper-split', action='store_true')
    args = ap.parse_args()

    r = audit(Path(args.root), args.split, full=not args.sample_only)
    text = json.dumps(r, indent=2)
    print(text)
    if args.out:
        Path(args.out).write_text(text + '\n', encoding='utf-8')
    if not r['structural_integrity_pass']:
        raise SystemExit(2)
    if args.require_paper_split and not r['paper_split_pass']:
        raise SystemExit(3)


if __name__ == '__main__':
    main()

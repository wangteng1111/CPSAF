# Current validation status — 2026-09-11

## Passed

- 49-state formulation and exact published sample-count arithmetic.
- Relative action `gt-current`, `[-48,+48]`, 97 classes.
- 5-channel AFPE plumbing.
- RoI-PE / Lens-PE conventions currently frozen in v0.4.
- SORD squared ordinal distance, coefficient 1.
- MobileNetV2 5-channel / 97-class parameter count = 2,348,705.
- Zhu stride 96 and all-49-start expansion.
- Training and evaluation pipeline smoke test.
- Strict preflight gate implementation.

## Newly established provenance facts

- Herrmann paper: 510 stacks total, 460 train / 50 test.
- Current official LearnAF README: 351 train / 47 test focal sweeps.
- This mismatch is authoritative and must not be silently ignored.
- Choi supplementary confirms valid-patch filtering by MVS confidence threshold but indexed authoritative text does not expose the numeric threshold.
- Zhu's published 68,187 / 7,805 spatial counts imply ~49.4% / 52.0% retention if applied to the paper's 460/50 stacks, which is internally plausible.

## Blocked

- Official-data manifest construction in the current sandbox (hundreds of GB are not present).
- Recovery of the exact author confidence threshold/filter rule.
- Numerical reproduction of Zhu's relative-label table.

## Next executable gate on a machine holding LearnAF

```bash
python build_manifest_v04.py --root /data/learnaf/train --out train_candidates.jsonl --protocol zhu
python build_manifest_v04.py --root /data/learnaf/test  --out test_candidates.jsonl  --protocol zhu

# Gold path: apply an authoritatively recovered threshold and verify counts.
# Fallback B: derive ONE threshold on train only and cross-check test independently.
python frozen_threshold_crosscheck.py \
  --train-candidates train_candidates.jsonl \
  --test-candidates test_candidates.jsonl
```

Only after manifest provenance passes should the 10k MobileNetV2 run be launched.

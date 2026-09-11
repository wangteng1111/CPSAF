# Zhu/Herrmann Autofocus Environment v0.5 Validation

This directory contains the strict validation layer for the Zhu/Herrmann autofocus simulator used by CPSAF.

## Stage-1 goal

The simulator is not considered scientifically validated merely because the code runs. Validation requires:

1. protocol invariants to match Herrmann/Choi/Zhu;
2. the mounted LearnAF data release to be audited;
3. the published spatial-patch counts to be reproduced or an authoritative discrepancy documented;
4. Zhu's published relative-label metrics to be reproduced within frozen tolerances.

## Frozen protocol

- 49 discrete focal positions.
- 128x128 patches, stride 96.
- all 49 initial lens states per spatial patch.
- relative action `GT-current`, range `[-48,+48]`, 97 classes.
- AFPE `[L,R,f,x,y]`.
- RoI-PE normalized to `[-1,1]`.
- Lens-PE `(index+1)/49`.
- SORD `q_i ∝ exp(-(i-y)^2)` with coefficient/T = 1.
- MobileNetV2 width 1.0, 2,348,705 parameters with the 97-class head.
- Adam 1e-3, betas (0.5,0.999), batch 128, cosine LR, 10k iterations.

## Published count gate

Zhu reports:

```text
train examples = 3,341,163 = 68,187 spatial patches x 49 starts
test examples  =   382,445 =  7,805 spatial patches x 49 starts
```

A numerical reproduction must not proceed to model tuning until the manifests reproduce these counts, or the discrepancy is explicitly and authoritatively explained.

## Data provenance issue

Herrmann 2020 describes 510 stacks total, split as 460 train / 50 test. The current official LearnAF README describes a smaller downloadable release with 351 train / 47 test focal sweeps. This mismatch is treated as a first-class provenance issue and must not be silently ignored.

At stride 96 on 1512x2016 images, each stack yields 300 candidate spatial patches. Zhu's 68,187 / 7,805 counts imply retention rates of about 49.4% / 52.0% if applied to the 460/50 paper split, versus about 64.8% / 55.4% on the 351/47 public release.

## Validation workflow

```bash
python data_mount_audit.py --root /data/learnaf/train --split train --require-paper-split
python data_mount_audit.py --root /data/learnaf/test  --split test  --require-paper-split

python build_manifest_v04.py --root /data/learnaf/train --out train_candidates.jsonl --protocol zhu
python build_manifest_v04.py --root /data/learnaf/test  --out test_candidates.jsonl  --protocol zhu

# If the authoritative confidence threshold is recovered, use it directly.
# Otherwise the only allowed empirical fallback is train-only inference + frozen test cross-check.
python frozen_threshold_crosscheck.py \
  --train-candidates train_candidates.jsonl \
  --test-candidates test_candidates.jsonl
```

Only after the data-level gate passes should the 10k MobileNetV2 run be launched and compared against the published target:

```text
exact 0.330
<=1   0.698
<=2   0.826
<=4   0.907
MAE   2.342
RMSE  6.339
```

## Current status

**Protocol-validated + provenance-audited; data-level validation pending.**

See `CURRENT_VALIDATION_STATUS.md`, `VALIDATION_POLICY.md`, `DATA_PROVENANCE.md`, and `REPRODUCTION_CHECKLIST.md` for the frozen acceptance rules.
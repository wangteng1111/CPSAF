# Stage-1 provenance audit

## Canonical source hierarchy

1. **Zhu et al., CVPR 2025** defines the reproduction target: 128×128, stride 96, 49 focal depths, 3,341,163 train examples and 382,445 test examples. Dividing by 49 gives 68,187 / 7,805 spatial focal-stack patches.
2. **Herrmann et al., CVPR 2020** defines the original L2A/LearnAF dataset construction: 51 scenes × 10 stacks = 510; 460 train / 50 test; 128×128, stride 40; GT from median depth then closest inverse-depth focal index; patches filtered by median MVS confidence.
3. **Official LearnAF Dataset Readme (2020-11-02)** describes the currently public release as 351 train focal sweeps + 47 test focal sweeps, with raw PD 756×2016 and upsampled PD 1512×2016.
4. **Choi et al., ICCV 2023 supplementary** independently states that training/evaluation uses only valid L2A patches whose MVS confidence is above a threshold, and notes remaining label errors in low-texture / focal-breathing regions.

## Important new finding: paper split vs public release

The paper-side 510-stack dataset and current public 398-sweep release are not the same size. This is an **authoritative provenance mismatch**, not a coding issue.

For 1512×2016 inputs, 128×128 fully-contained crops yield:

- stride 40: 35×48 = 1,680 candidate patches/stack;
- stride 96: 15×20 = 300 candidate patches/stack.

If Zhu used the paper-side 460/50 split, its published spatial counts imply retention fractions of roughly 49.4% train and 52.0% test. Overall: ~49.7%.

If the same published counts are forced onto the current 351/47 public release, the implied retention fractions become roughly 64.8% train and 55.4% test. Overall: ~63.6%.

This does **not prove** which capture set Zhu used, but the paper-side 510-stack interpretation is substantially more consistent with the approximate 50% retention suggested by Herrmann's original training set after confidence filtering.

## Confidence threshold status

Authoritative indexed sources confirm that a confidence threshold/filter exists. The exact numeric threshold has not yet been recovered from an authoritative Herrmann/Zhu source in this environment. Third-party values such as 0.95 or 0.98 are retained only as diagnostics and must **not** be frozen into the canonical pipeline.

## Consequence

A manifest that happens to contain exactly 68,187 / 7,805 patches is **necessary but not sufficient** for scientific reproduction. The validation gate additionally requires provenance of the capture split / filter rule and numerical reproduction of Zhu's published metrics.

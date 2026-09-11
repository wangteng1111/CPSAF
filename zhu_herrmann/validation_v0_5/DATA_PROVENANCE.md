# LearnAF / Zhu reproduction data provenance (v0.5)

## Sources kept separate

1. **Herrmann et al., CVPR 2020 paper**: 51 scenes, 10 stacks per scene = 510 stacks; 5 scenes / 50 stacks test and 460 stacks train. Original patch protocol: 128x128, stride 40, median depth label in inverse-depth space, filtered by median depth confidence.
2. **Public LearnAF archive README (updated 2020-11-02)**: says the downloadable release contains 351 focal sweeps in `train` and 47 in `test`. It documents 49 slices per sweep and the raw / upsampled DP layouts.
3. **Zhu et al., CVPR 2025**: re-extracts 128x128 patches at stride 96 and reports 3,341,163 training and 382,445 test samples. Because each spatial position is represented at all 49 focal depths, these correspond exactly to 68,187 and 7,805 spatial stacks.

The 351/47 public-release counts do **not** equal the 460/50 counts stated in the 2020 paper. v0.5 treats this as a provenance discrepancy to audit, not something to silently "fix". A scientific reproduction should record the actual archive contents used and require the final spatial-patch counts to match Zhu before accepting the data protocol.

## What is authoritative in v0.5

- 49 lens states and official focus-distance table: LearnAF README.
- Patch label: median depth, nearest focus in inverse-depth space: Herrmann main paper.
- Zhu patch size/stride and all-49-start expansion: Zhu main paper.
- AFPE `[L,R,f,x,y]`, RoI-PE in `[-1,1]`, lens-PE `f=k/n`: Choi main paper.
- SORD target `exp(-(rank difference)^2/T)` and `T=1` for single slice: Choi main paper, consistent with Herrmann's L2 cost coefficient 1.
- Relative action range `[-48,+48]`, physical-boundary clipping: Zhu main paper.

## Still unresolved without Zhu supplementary / author code

- Exact labeling/filtering details referred to as supplementary Sec. 6 by Zhu, especially the confidence cutoff and any extra validity filtering.
- Exact random seed / shuffle details.
- Whether any preprocessing beyond the public raw linear DP normalization was used.

These are surfaced as reproduction assumptions rather than hidden defaults.

## Frozen fallback rule

If the authoritative confidence threshold cannot be recovered, only one empirical fallback is permitted: infer a single threshold using the **training** target count 68,187, freeze it, and apply it unchanged to test. The test count 7,805 must then emerge independently. Train/test-specific threshold tuning is prohibited.
# Zhu single-step reproduction checklist

1. [x] 49-state focal-stack environment.
2. [x] Relative action `GT-current`, range `[-48,+48]`.
3. [x] Physical action clipping to `[0,48]`.
4. [x] Choi 5-channel AFPE `[L,R,f,x,y]`.
5. [x] RoI-PE centered and normalized to `[-1,1]`.
6. [x] Lens-PE paper-literal `f=k/n` mapping.
7. [x] SORD squared ordinal-distance target, coefficient/T = 1 for D1.
8. [x] MobileNetV2 width 1.0, 2,348,705 parameters with 97-class head.
9. [x] Zhu crops 128x128, stride 96.
10. [x] 49 initial lens states enumerated per spatial patch.
11. [x] Adam 1e-3, betas .5/.999, batch 128, cosine, 10k steps.
12. [x] 49-start metrics and per-start CSV.
13. [x] Official archive downloader and structural auditor.
14. [ ] Recover/validate the exact Zhu/Herrmann confidence-filter / label-selection rule from authoritative supplementary material or author clarification.
14b. [x] Implement a non-cheating fallback: infer one cutoff from train count only, freeze it, and independently cross-check test count.
15. [ ] Obtain and audit official Herrmann train/test archives.
16. [ ] Reproduce 68,187 train and 7,805 test spatial patches, or document an authoritative reason for count mismatch.
17. [ ] Run full 10k single-step training on official data.
18. [ ] Compare against Zhu relative-label Table target (.330/.698/.826/.907, MAE 2.342, RMSE 6.339).
19. [ ] Repeat seeds / estimate variance if needed.
20. [ ] Only then implement PPO + 6M expert-trajectory regularization.
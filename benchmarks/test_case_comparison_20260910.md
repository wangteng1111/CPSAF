# CPSAF vs Zhu/Choi/Herrmann — test-case comparison (2026-09-10)

## Rule of comparison

Published Zhu/Choi/Herrmann numbers and current CPSAF dynamic numbers are **not the same benchmark**. Zhu uses static, pre-recorded Herrmann focal stacks with 49 discrete lens positions. Current CPSAF tests use a continuous-time second-order actuator proxy, synthetic phase/analog-DP sensing, and moving/step targets. Cross-column claims of numerical superiority are therefore prohibited until a bridge benchmark is run.

## Published static focal-stack benchmark

See `zhu_published_static.csv`. The relevant published progression is:

- Herrmann (2020): one-step MAE 3.249, RMSE 7.619.
- Choi RoI-PE + Lens-PE (2023): one-step MAE 2.839, RMSE 6.880.
- Choi architecture + Zhu relative label: one-step MAE 2.342, RMSE 6.339.
- Zhu Expert-Trajectory DRL: one-step MAE 2.146, RMSE 5.827; at 4 steps MAE 1.694, RMSE 5.479, FH 0.178.

The current analog CPSAF MLP has not yet been evaluated on the official Herrmann static test set, so this table must contain `N/A` for CPSAF until that bridge test is implemented.

## Current dynamic CPSAF benchmark

See `cpsaf_dynamic_5khz.csv`. The main 5-kHz/80-Hz-plant results are:

- State-7 MLP: 10-Hz RMSE 0.976, 20-Hz RMSE 1.969, step settling 6.09 ms.
- Raw-tap-8 MLP: 1.182 / 2.357, step 6.69 ms.
- Analog Ordinal MLP: 1.159 / 2.306, step 7.975 ms, 100% success in its v0.5 harness.
- Tracking-oriented Analog Logit branch: about 0.899 / 0.911, but ~33 ms / 12.5% success on the large step; it is not a balanced controller.

Zhu/Choi/Herrmann do not report 10/20-Hz target tracking RMSE, physical millisecond settling through an actuator plant, Hall/command jitter, or the same confidence-dropout test; entries are therefore `N/A`, not zero or worse.

## Bridge tests required for a defensible paper comparison

1. **Static Herrmann bridge:** feed official Herrmann DP patches to the current MLP (or an input adapter) and report exact/within-1/2/4, MAE, RMSE for all 49 initial positions. This is the only direct way to compare to Zhu Table 3/1.
2. **Dynamic Zhu bridge:** insert Zhu/Choi policies into the same CPSAF continuous-time plant and sensor timing model, then report 10/20-Hz tracking, 8→40 settling, hunting/jitter, and dropout. This isolates controller topology from dataset accuracy.
3. **Real Canon DP bridge:** replace the synthetic analog A/B generator with measured Canon-style DP A/B readout and repeat phase-observability + dynamic control tests.

## Capacity note

Zhu's architecture ablation is suggestive for planned MLP scaling: with relative labels, ResNet50 (~23.71M params) improves MAE/RMSE and within-1/2/4 compared with MobileNetV2 (~2.35M), although exact-index accuracy is slightly lower (0.326 vs 0.330). This supports testing capacity systematically, but does not prove that larger networks monotonically improve every AF metric.

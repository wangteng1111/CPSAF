# Validation policy before CPSAF training

The Zhu/Herrmann environment may be called **scientifically validated** only when all gates pass:

1. protocol unit tests pass;
2. authoritative data provenance is documented;
3. train spatial manifest = 68,187 and test = 7,805, with confidence metadata present;
4. no threshold is chosen merely to force those counts;
5. 10k-step relative-label MobileNetV2 reproduction matches Zhu within predeclared tolerances:
   - exact / <=1 / <=2 / <=4: ±0.02 absolute;
   - MAE: ±0.10;
   - RMSE: ±0.20.

Until then, CPSAF training results are exploratory only and must not be compared as if the simulator were validated.

## Fallback B if the author threshold remains unavailable

A weaker **empirical validation** may be attempted, but it cannot be called authoritative protocol recovery:

1. Build unfiltered train and test candidate manifests with median confidence retained for every patch.
2. Infer exactly one cutoff from the **training set only**, using the published 68,187 train spatial-patch count.
3. Freeze that cutoff and comparison operator.
4. Apply it unchanged to the test set. Do **not** tune on the test count.
5. Require the independent test count to reproduce 7,805 (or a predeclared tiny tolerance if file/capture provenance justifies it).
6. Train/evaluate once using the frozen rule and require the predeclared Zhu metric tolerances.

If train count, independent test count, and Zhu metrics all agree, the environment may be described as **empirically benchmark-validated with unresolved threshold provenance**, not as an exact author-code reproduction.

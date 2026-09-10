# CPSAF

Continuous / phase-sensing autofocus research enabled by HCM crossbar neural control.

This repository archives the simulation environments, controller prototypes, evaluation reports, and trained checkpoints produced during the September 2026 CPSAF study.

## Repository layout

- `archive/` — versioned research snapshots and reconstruction instructions.
- `zhu_herrmann/` — Zhu 2025 / Herrmann 2020 reproduction notes and protocol status.
- `benchmarks/` — quantitative test-case comparisons against published autofocus baselines.
- `artifacts/` — key machine-readable metrics/checkpoint metadata.

## Current hardware-oriented direction

The target deployment topology is a **single fixed feed-forward crossbar MLP** driven by Canon-style dual-pixel A/B analog phase signals plus lens-state history. Runtime inference must not rely on explicit Acquire/Track/Hold state switching, argmin disparity decoding, or digital strategy selection.

## Reproduction status

The Zhu/Herrmann software/protocol environment has been developed through v0.4. Full numerical reproduction of Zhu 2025 on the official Herrmann dataset is still gated by the very large official dataset and exact data-filtering protocol. Mock/synthetic results are explicitly labeled and must not be confused with published-data reproduction.

## Archive policy

The core archive preserves all source code, reports, CSV/JSON results, and trained checkpoints available in the session. Python bytecode is excluded. A few large synthetic intermediate arrays that are reproducible from retained scripts are listed explicitly in the archive notes rather than duplicated into GitHub.

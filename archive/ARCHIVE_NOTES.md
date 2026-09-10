# Archive notes — 2026-09-10

This repository snapshot preserves the source code, reports, and machine-readable result files available from the CPSAF simulation work completed in the current research session.

## Preserved in browsable form

- Zhu/Herrmann reproduction environment through v0.4 (source, tests, README/status, official-data scripts).
- Initial latency/actuator CPSAF meta-test v0.1 (source and all CSV results).
- Acquire–Track–Hold teacher v0.2 (source and all focused result CSVs).
- Fixed crossbar MLP v0.3 (training/evaluation source, report, key JSON/CSV metrics).
- Analog-PDAF v0.5 summary metrics and checkpoint manifest.

## Binary/intermediate-data policy

Large synthetic `.npz` replay datasets and Python bytecode are intentionally excluded because they are regenerable and not primary scientific results. Selected trained `.pt` checkpoints are tracked by a manifest (file size, SHA-256, architecture/state-dict metadata). The ChatGPT GitHub connector available in this session exposes UTF-8 file operations but no direct local-binary upload action; exact checkpoint bytes remain in the session artifacts and should be uploaded with Git/LFS from a local checkout if long-term binary preservation is required.

## Numerical-reproduction caveat

The full official Herrmann dataset is not included. Zhu/Herrmann protocol reconstruction is implemented, but official-data numerical reproduction remains pending.

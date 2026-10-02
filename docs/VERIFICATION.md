# Verification record

Created October 2, 2026. This record describes tested implementations and explicit outstanding scope, not historical completion evidence.

## Local checks

`python3 scripts/check.py` completed successfully:

- **26 Java checks**: trade acceptance/rejection, indexed salary formula, triggered/existing hard caps, roster overflow, eligibility, duplicate/malformed input, seed repeatability, race-time distributions, pit-loss sensitivity.
- **18 Python/HTTP tests**: feature validation, outcome exclusion, separated seasons/games, dataset hash, generated-data repeatability, recommendation reproducibility/intervals, import filtering, real Java-backed API calls, and restricted static-file serving.
- **2 PyTorch tests** require PyTorch and run in the machine-learning CI job; they were skipped in the local environment because PyTorch was absent.
- JavaScript passed Node syntax checking.

## Confirmed GitHub Actions results

[Complete verification run](https://github.com/hfjkdbfjk45/Projects/actions/runs/37023996842) completed successfully for commit `a8267c1fa5d887449e69b0f7e199ffa38fb9869f`. All five jobs passed.

| Job | Observed result |
| --- | --- |
| Core | 26 Java checks and 18 Python/HTTP tests passed; two optional PyTorch tests skipped in this job |
| .NET | Both projects built with zero errors; fixture importer accepted four timed laps and dropped one; live Java-to-C# request chain passed |
| Machine learning | All 20 Python tests passed with PyTorch installed; causal masking/gradient checks passed; a two-epoch Transformer smoke-training run completed |
| Browser | React production build passed; valid/invalid NBA trades, F1, NFL, mobile layout, and React-to-Flask flows passed without page errors |
| Containers | All Docker images built and services started; Java/C# and React/Flask endpoints passed; PostgreSQL ETL loaded 3,840 plays twice and retained exactly 3,840 unique rows |

The actual CI screenshots are committed under `docs/screenshots/`. The [two-epoch Transformer metadata](transformer-demo-metrics.json) is preserved from the [initial implementation run](https://github.com/hfjkdbfjk45/Projects/actions/runs/37022461116). Its synthetic test accuracy was 60.83%; this short run verifies the training workflow and is not a real NFL performance benchmark.

MATLAB execution, historical imports, live-provider access, and AWS deployment remain outside the completed verification.

## Measured demo evaluation

Source: `projects/nfl-play-predictor/models/baseline_metrics.json`.

| Measure | Result |
| --- | --- |
| Dataset | Synthetic, generated with seed 42 |
| Dataset rows | 3,840 |
| Training | 2,880 plays / 72 games / demo seasons 2018–2023 |
| Validation | 480 plays / 12 games / demo season 2024 |
| Test | 480 plays / 12 games / demo season 2025 |
| Test accuracy | 65.42% |
| Majority baseline accuracy | 54.79% |
| Test F1 | 0.5389 |
| Test balanced accuracy | 0.6360 |
| Test Brier score | 0.2148 |

This evaluation measures the synthetic demo distribution. It cannot be used to claim 65.42% or 78% accuracy on actual NFL games.

## Resume claim status

| Resume statement | Evidence in this repository |
| --- | --- |
| NBA Java engine, C# middleware, JS interface | Implementations plus regression/integration checks |
| 50+ historical trades / 92% accuracy | Not measured; synthetic tests are not historical trades |
| F1 Java Monte Carlo engine | Runnable; default 1,000 scenarios per strategy |
| 10K+ OpenF1 records per race | Importer reports actual row counts; scale not established |
| 53% F1 runtime reduction | No before/after benchmark supplied |
| NFL PyTorch Transformer | Causal model and temporal training/evaluation workflow |
| 10+ years of real NFL training / 78% accuracy / +9% comparison | Import workflow supplied; real training and comparison not completed |
| Flask/React/PostgreSQL/Docker | Implementations and automated checks where applicable |
| Live NFL feed / AWS deployment / 2M+ records | Optional configuration and deployment/ETL paths; not completed or measured |

To substantiate a numeric claim, retain the exact dataset/version, train/validation/test split, benchmark code, hardware, raw outputs, and independently reviewed baseline. Commit actual measurements without backdating history.

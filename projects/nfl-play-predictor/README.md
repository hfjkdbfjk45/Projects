# NFL Play Predictor & Strategy Optimizer

Run/pass prediction from pre-snap context, causal sequence-model training, and simplified Monte Carlo fourth-down comparisons. Includes a Flask API, React frontend, PostgreSQL schema/ETL, and Docker deployment.

## Start with the working demo

Run `python3 launch.py` from the root and select NFL. The bundled logistic baseline was trained on **3,840 synthetic plays**, not real NFL games. Earlier seasons are used for training, 2024 demo games for validation, and 2025 demo games for testing. Its measured synthetic holdout accuracy is **65.4%**; the majority baseline is **54.8%**. These are demo-distribution results, not NFL accuracy.

```bash
python3 projects/nfl-play-predictor/scripts/train_baseline.py --generate-demo
```

Predictions use down, distance, field position, remaining game time, score difference, quarter, and the preceding offensive run/pass call. Outcome fields, EPA, and play descriptions never enter prediction features. A sequence uses only current and preceding pre-snap contexts from the same game/offense.

## Flask and React

Install Python dependencies in a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r projects/nfl-play-predictor/requirements.txt
python3 projects/nfl-play-predictor/api.py
```

On Windows, activate with `.venv\Scripts\activate` instead. In a second terminal, with Node 22.12+:

```bash
cd projects/nfl-play-predictor/frontend
npm install
npm run dev
```

Open http://127.0.0.1:5173. Development requests proxy to Flask on port 5000. `npm run build` produces `frontend/dist`, which Flask serves at http://127.0.0.1:5000.

| Endpoint | Behavior |
| --- | --- |
| `GET /health` | Active model and source |
| `POST /api/predict` | Run/pass probabilities |
| `POST /api/recommend` | Fourth-down estimates, seed, sampling intervals |
| `GET /api/metrics` | Baseline evaluation and dataset hash |
| `GET /api/live` | Opt-in normalized external provider adapter; 503 until configured |

## Train the PyTorch Transformer

```bash
pip install -r projects/nfl-play-predictor/requirements-ml.txt --index-url https://download.pytorch.org/whl/cpu
python3 projects/nfl-play-predictor/scripts/train_transformer.py --epochs 15
```

The model uses an 8-context causal Transformer, positional embeddings, padding masks, and a binary classifier. Training and validation are separated by season; validation Brier score selects the checkpoint; the final season is evaluated after selection. A smoke-training run is checked in CI; its metadata is downloadable as an Actions artifact.

To serve your trained checkpoint, set `NFL_TRANSFORMER_MODEL` to its `model.pt` path before starting Flask. Keep `metadata.json` beside the checkpoint. For multi-context predictions, send `{"contexts":[...chronological pre-snap context objects...]}`. For one context, send the standard object. The fourth-down simulator still uses the baseline and its training-only empirical outcome pool; it is a separate model.

## Import real historical plays

```bash
python3 projects/nfl-play-predictor/scripts/import_nflverse.py --seasons 2014 2015 2016 2017 2018 2019 2020 2021 2022 2023 2024 2025
python3 projects/nfl-play-predictor/scripts/train_baseline.py \
  --data projects/nfl-play-predictor/data/raw/nflverse_plays.csv \
  --output output/nfl-real-baseline --data-source "nflverse observed historical play-by-play"
python3 projects/nfl-play-predictor/scripts/train_transformer.py \
  --data projects/nfl-play-predictor/data/raw/nflverse_plays.csv \
  --output output/nfl-real-transformer --data-source "nflverse observed historical play-by-play"
```

The importer downloads public nflverse season CSV.gz files, retains eligible run/pass plays, removes spikes/kneels and incomplete situations, and writes a normalized dataset plus provenance/hash metadata. Downloaded data and model checkpoints are ignored by Git. [nflverse data](https://github.com/nflverse/nflverse-data), [nflreadr documentation](https://nflreadr.nflverse.com/reference/load_pbp.html).

Supply at least three seasons. No real-data download or 10-year training has been performed as part of the bundled demo. Measure accuracy, F1, balanced accuracy, Brier score, sample counts, and the majority baseline using the generated reports before claiming performance.

Set `NFL_BASELINE_MODEL` and `NFL_TRAINING_DATA` to matching real-data artifacts if you want the served baseline and empirical outcomes to use your historical training. Transformer's input feature list excludes outcomes; its current target's run/pass label is used only as the training target, not as context.

## PostgreSQL and Docker

From the root:

```bash
docker compose up --build
docker compose exec nfl python scripts/load_postgres.py
```

The primary key is `(game_id, play_id)`; ETL uses parameterized batched upserts. Run `database/audit.sql` to see actual seasons/row counts and target balance. No two-million-record throughput claim is made. The dashboard currently predicts from supplied context; it does not query PostgreSQL for every request.

## Fourth-down model limits

The simulation bootstraps yards from the training split by run/pass and distance bucket, then rolls out possession changes, simplified drives, kicking assumptions, and clock consumption. It compares go-for-it, field-goal, and punt actions with reproducible seeds and Monte Carlo uncertainty. Ties count as half a win.

This is **uncalibrated**. Clock management, team strengths, game rules at period boundaries, timeouts, penalties, turnovers other than on downs, overtime, and professional kicking models are not fully represented. Intervals describe sampling error, not total model uncertainty.

## Live data

`NFL_LIVE_URL` must identify your licensed provider's endpoint returning the documented normalized context JSON; `NFL_LIVE_TOKEN` is optional bearer authentication. Provider-specific field mapping is your adapter's responsibility. No provider subscription, live ingestion, or AWS deployment has been completed. See [.env.example](../../.env.example) and [AWS_DEPLOYMENT.md](../../docs/AWS_DEPLOYMENT.md).

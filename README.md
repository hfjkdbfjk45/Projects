# ScoreLab — Sports Analytics Portfolio

**Salman Nur** · Electrical & Computer Engineering, The Ohio State University

[![Verify portfolio](https://github.com/hfjkdbfjk45/Projects/actions/workflows/verify.yml/badge.svg)](https://github.com/hfjkdbfjk45/Projects/actions/workflows/verify.yml)

Three runnable sports analytics projects in one repository. Start the combined dashboard with **Python and Java**, or run each project's full stack independently.

| Project | Working features | Implementation |
| --- | --- | --- |
| [NBA Trade Machine](projects/nba-trade-machine/) | Player selection and drag/drop; salary-matching, apron, hard-cap, and roster checks | Java engine, C# REST middleware, JavaScript, XML |
| [F1 Strategy Simulator](projects/f1-strategy-simulator/) | Paired Monte Carlo race-time comparison; tyre/fuel/weather factors; lap charts; historical telemetry normalization | Java, C#/.NET, MATLAB |
| [NFL Play Predictor](projects/nfl-play-predictor/) | Trained run/pass baseline; causal Transformer training; fourth-down simulations; data import and database ETL | Python, PyTorch, Flask, React, PostgreSQL, Docker |

Bundled NBA rosters and NFL plays are **fictional/synthetic demo data**. F1 simulation parameters are illustrative. Actual measurements, limitations, and data provenance are documented in [VERIFICATION.md](docs/VERIFICATION.md) and [DATA_SOURCES.md](docs/DATA_SOURCES.md). The repository was built with AI coding assistance in October 2026; it does not substantiate unmeasured resume statistics.

## Run the combined demo

Install **Python 3.10+** and a **Java 17+ JDK**. No Python packages, API keys, database, or npm installation are needed for this demo.

```bash
git clone https://github.com/hfjkdbfjk45/Projects.git
cd Projects
python3 launch.py
```

Open **http://127.0.0.1:8000**. On Windows, use `py launch.py` if `python3` is unavailable. Press Ctrl+C to stop.

The demo invokes the actual Java NBA and F1 engines. Its NFL page uses the checked-in trained logistic baseline. The full PyTorch and React paths have separate setup instructions below.

## Reproduce the checks

```bash
python3 scripts/check.py
python3 scripts/run_f1.py --runs 1000 --output output/f1
python3 projects/nfl-play-predictor/scripts/train_baseline.py --generate-demo
```

The tests check invalid trades, hard caps, seed reproducibility, pre-snap feature isolation, chronological holdouts, input validation, and HTTP behavior. GitHub Actions additionally checks .NET compilation/integration, PyTorch gradients and training, React builds, and browser flows. Browser screenshots and Transformer evaluation metadata are downloadable from each Actions run.

## Run the full stacks

Read each project's README for native commands. For the NFL React/Flask app, PostgreSQL, and the NBA Java/C# services together:

```bash
docker compose up --build
```

| Service | Local address |
| --- | --- |
| NFL React + Flask | http://127.0.0.1:5000 |
| NBA C# API | http://127.0.0.1:5080/api/sample |
| PostgreSQL | localhost:5432 |

```bash
docker compose exec nfl python scripts/load_postgres.py
```

Docker serves the baseline by default. PyTorch training is an optional separate workflow; it is not silently replaced by the baseline. [AWS deployment instructions](docs/AWS_DEPLOYMENT.md) describe how to run the containers on an EC2 instance; no AWS resources have been provisioned.

## Repository map

| Path | Purpose |
| --- | --- |
| `dashboard/` | Combined offline JavaScript UI |
| `projects/nba-trade-machine/` | Java engine, XML snapshot, sample roster, .NET middleware |
| `projects/f1-strategy-simulator/` | Java simulation, .NET OpenF1 importer, MATLAB analysis |
| `projects/nfl-play-predictor/` | Models, training scripts, API, React app, PostgreSQL ETL |
| `tests/`, `scripts/` | Reproducibility and integration checks |
| `docs/` | Data sources, verification, owner guide, deployment notes |

For a short walkthrough and interview preparation, start with [OWNER_GUIDE.md](docs/OWNER_GUIDE.md).

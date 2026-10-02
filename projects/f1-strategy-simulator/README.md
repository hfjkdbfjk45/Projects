# F1 Race Strategy Simulator & Telemetry Dashboard

Java performs paired Monte Carlo comparisons of four pit strategies. A .NET pipeline fetches historical OpenF1 laps/stints/pits/weather and writes normalized telemetry. MATLAB analyzes the Java CSV exports.

## Simulation

From the root:

```bash
python3 launch.py
python3 scripts/run_f1.py --runs 1000 --laps 57 --rain 0.25 --seed 42 --output output/f1
```

Use the F1 dashboard tab or inspect `output/f1/strategy_results.csv`, `lap_trace.csv`, and `simulation.json`. Controls include race length, runs per strategy, rain probability, pit-lane loss, and seed. The default evaluates 4,000 races, 1,000 per strategy.

Each strategy sees the same random weather, global pace uncertainty, lap noise, and pit-loss noise. Modeled lap time includes compound pace, linear tyre degradation, a wear penalty beyond assumed tyre life, decreasing fuel mass, and pit loss. When rain begins, every strategy switches to intermediates and cancels remaining dry stops.

Outputs include mean, 10th/90th percentile, standard deviation, standard error of the mean, and fraction of paired scenarios with the lowest modeled race time. The chart shows a deterministic dry reference; it is not an observed telemetry trace.

**Limitations:** parameters are synthetic, not fitted to real races; rain persists once it begins; pit strategies are a fixed candidate set; no traffic, overtaking, safety cars, retirements, pace differences between drivers, or formal finishing-position model. The lowest-time fraction is not a calibrated probability of winning an actual Grand Prix.

## Historical telemetry pipeline (.NET 8)

First run the offline fixture:

```bash
dotnet run --project projects/f1-strategy-simulator/pipeline -- \
  --fixture projects/f1-strategy-simulator/data/openf1-fixture.json \
  --output output/f1-telemetry
```

For real historical data, supply a session key from [OpenF1's sessions endpoint](https://openf1.org/docs/#sessions):

```bash
dotnet run --project projects/f1-strategy-simulator/pipeline -- \
  --session 9158 --output output/f1-telemetry
```

The importer drops invalid/incomplete timed laps, indexes stints by driver, binary-searches the applicable stint, preserves compound and starting tyre age, joins pit records, and exports CSV plus original endpoint JSON. `lane_duration` is preferred, with `pit_duration` retained only as a compatibility fallback; stationary stop duration is kept separately. These values are not interchangeable with track-relative pit time lost.

Load `laps_normalized.csv` in the dashboard's telemetry section to plot up to four drivers. Files are read locally in the browser. Historical OpenF1 data is available without authentication; real-time access requires a subscription. [Official OpenF1 documentation](https://openf1.org/docs/).

The supplied contract fixture is synthetic. Telemetry import does **not** automatically calibrate the simulation. Record real row counts in the generated `summary.json`; do not assume 10K records per race.

## MATLAB

From the repository root in MATLAB:

```matlab
addpath('projects/f1-strategy-simulator/matlab');
analyze_strategy(fullfile('output','f1'));
```

This plots race-time ranges and lap traces with labeled axes. MATLAB execution requires MATLAB and is not part of the GitHub runner checks.

## Verification

`python3 scripts/check.py` checks seed repeatability, finite/ordered distributions, complete traces, shares summing to one, input limits, and the effect of increased pit loss. The .NET CI test checks fixture normalization, tyre-age boundaries, pit field separation, and invalid-lap removal.

No 53% runtime reduction is claimed. A valid optimization benchmark must compare equivalent before/after implementations with identical inputs and documented hardware.

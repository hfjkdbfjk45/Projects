# Run, review, and present your projects

## Your first walkthrough

1. Clone the repository and open the `Projects` folder in VS Code.
2. Install Python 3.10+ and a Java 17+ JDK, then run `python3 launch.py` in the terminal.
3. Open http://127.0.0.1:8000. Validate the NBA example, then try Marcus Cole for Noah Price to see a rejected trade.
4. Open F1. Compare results at rain probability 0% and 100%, with the same seed. Explain why the assumptions matter.
5. Open NFL. Change score difference or distance. Compare the probability estimates and fourth-down action intervals.
6. Run `python3 scripts/check.py`. Read the output and the source for one check from each project.

## Show evidence to a recruiter

Link the repository in your resume and pin it on your GitHub profile. A strong project demonstration contains the runnable code, a short README, reproducible tests, screenshots, data sources, and a clear explanation of your own contribution.

Record a short screen capture: one valid and invalid NBA trade, one F1 scenario change, and one NFL fourth-down comparison. Add that real recording or your own screenshots after running the app. Use actual test and evaluation outputs when describing results.

## Understand the implementations

| Project | Start reading | Be ready to explain |
| --- | --- | --- |
| NBA | `TradeEngine.java`, `rules.xml` | How matching routes differ; why apron payroll differs from basic payroll; when a hard cap is triggered |
| F1 | `RaceSimulator.java` | Why strategies share random scenarios; how tyre wear, fuel, pit loss, and rain affect totals |
| NFL | `nfl/core.py`, `nfl/transformer.py` | Baseline vs Transformer; pre-snap features; season holdouts; sampling error vs model error |

This version was created with AI coding assistance. Review the code, run it yourself, and describe that assistance accurately. The repository establishes inspectable implementations, not an earlier completion date or personal mastery by itself.

## Make your own next contribution

Choose one concrete improvement, such as adding a reviewed NBA contract exception, fitting F1 tyre degradation from imported laps, or evaluating the NFL model on real held-out seasons. Record why you chose it, how you implemented it, and what the tests showed.

```bash
git checkout -b improve-f1-calibration
# Make and test your change.
git add .
git commit -m "Fit tyre degradation from a documented historical session"
git push -u origin improve-f1-calibration
```

Then open a pull request on GitHub and describe the implemented behavior and validation. Commit dates should reflect when work actually happened.

## Resume wording supported by the current implementation

- NBA: Implemented a Java salary-matching engine with configurable cap/apron rules, C# REST middleware, and a JavaScript player-selection interface; added regression checks for invalid trades and hard-cap constraints.
- F1: Built a Java Monte Carlo simulator comparing 1,000 scenarios per pit strategy with tyre, fuel, and rain assumptions; implemented a .NET historical telemetry importer and MATLAB analysis exports.
- NFL: Implemented a causal PyTorch run/pass training pipeline, Flask/React dashboard, and Monte Carlo fourth-down comparisons; added chronological evaluation and PostgreSQL ETL, with demo results explicitly separated from real-data benchmarks.

Use these descriptions only after reviewing and running the relevant parts yourself. Keep performance percentages out until you have reproducible real-data evidence.

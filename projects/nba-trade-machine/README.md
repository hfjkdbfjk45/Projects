# NBA Trade Machine Simulator

A Java validator with an XML rule snapshot, C# REST middleware, and a JavaScript trade-construction interface. The bundled roster is fictional; all salary figures are integer dollars.

## Try it

From the repository root, run `python3 launch.py`, open http://127.0.0.1:8000, and use the NBA tab. The sample sends Marcus Cole ($18M) for Isaiah Grant ($20M). The first team uses the expanded exception and triggers the modeled first-apron hard cap.

For an invalid example, clear the selection and send Marcus Cole for Noah Price ($9M). The return salary is too high for the receiving team's matching allowance. Players can also be dragged into the opposite team's drop zone.

## Native Java and C# API

```bash
python3 launch.py --check
java -cp build TradeServer serve . 8081
```

In another terminal:

```bash
dotnet run --project projects/nba-trade-machine/api --urls http://127.0.0.1:5080
```

The API exposes `GET /health`, `GET /api/sample`, and `POST /api/validate`. It forwards JSON to the Java service and returns input errors or an upstream-unavailable response. Set `NBA_ENGINE_URL` to change the upstream address.

Example request from the repository root:

```bash
curl -X POST http://127.0.0.1:5080/api/validate \
  -H "Content-Type: application/json" \
  --data-binary @projects/nba-trade-machine/data/sample-trade.json
```

## Implemented rule scope

The snapshot is **2024–25**, using a $140.588M cap, $178.132M first apron, and $188.931M second apron. It is intentionally frozen, not a claim about today's season. [NBA announcement](https://www.nba.com/news/nba-salary-cap-set-2024-25-season).

For outgoing salary `S`, the expanded incoming limit is:

```text
max(min(2S + 250,000, S + indexed allowance), 1.25S + 250,000)
indexed allowance = floor(7,500,000 × season cap / 2023–24 cap)
```

The code checks cap room, standard and aggregated standard exceptions, the expanded exception, the removal of the $250K allowance above the first apron, transaction-triggered hard caps, supplied pre-existing hard caps, supplied player eligibility, and a 15-player standard-roster maximum. Aggregate standard matching uses the second-apron restriction; expanded matching uses the first-apron restriction.

The input distinguishes `payroll` from `apronPayroll`. The caller must supply correct cap/apron salary data, including omitted players and applicable adjustments. Only traded players are listed in the demo excerpt; the full payroll and roster counts are supplied separately.

**Not implemented:** contract-specific salary transformations (BYC/poison pills/trade bonuses), sign-and-trade details, exceptions carried over from earlier transactions, transaction dates, cash, draft picks/Stepien restrictions, two-way contracts, waiver timing, and offseason next-year apron rules. A passing result means **valid under implemented rules**, not approval of an actual NBA trade.

Sources: [NBPA CBA](https://nbpa.com/cba), Article VII §2(e) and §6(j). See [DATA_SOURCES.md](../../docs/DATA_SOURCES.md).

## Verification

Run `python3 scripts/check.py` from the root. Java regressions cover sample acceptance, first-apron restrictions, existing hard caps, aggregation restrictions, roster overflow, eligibility, duplicate players, invalid numbers, and JSON validation. The .NET CI job compiles both projects and calls the actual middleware-to-Java chain.

No historical-trade accuracy is claimed. To evaluate historical trades, add dated contract/cap inputs and independently reviewed expected results rather than labeling synthetic tests as historical validation.

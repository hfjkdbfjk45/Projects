# Data sources and provenance

| Area | Source | Included data |
| --- | --- | --- |
| NBA cap snapshot | [NBA 2024–25 announcement](https://www.nba.com/news/nba-salary-cap-set-2024-25-season) | Cap/apron figures in XML |
| NBA rule formulas | [NBPA 2023 CBA](https://nbpa.com/cba), Article VII §2(e), §6(j) | Original implementation of a documented subset |
| NBA teams/players | Generated demonstration fixtures | Fictional names, salaries, roster excerpts |
| F1 pace/tyres/fuel | Explicit illustrative model assumptions in `RaceSimulator.java` | Synthetic Monte Carlo outputs |
| F1 telemetry | [OpenF1 official API docs](https://openf1.org/docs/) | Synthetic API-contract fixture; real telemetry fetched only when the user runs the importer |
| NFL demo plays | `make_synthetic`, seed 42 | 3,840 synthetic labeled plays across demo seasons 2018–2025 |
| NFL historical data | [nflverse-data](https://github.com/nflverse/nflverse-data), [nflreadr](https://nflreadr.nflverse.com/reference/load_pbp.html) | Importer only; historical data is not bundled |
| Live NFL context | User-configured provider | No live feed supplied |

These projects are independent portfolio implementations, not official league products. No official logos or player photography are included. Follow each provider's terms, data license, attribution requirements, and rate limits when downloading or redistributing external data.

The OpenF1 importer distinguishes pit-lane duration from stationary pit-stop duration and supports the documented deprecation of `pit_duration`. The NFL importer records source URLs, actual accepted row counts, and SHA-256 hashes. A normalized schema does not establish provenance by itself; retain the generated metadata with evaluations.

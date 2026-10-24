# v2 gate log

Results of the gates in `docs/v2_lineup_plan.md` (tag `v2-plan`), in order. The plan itself is not
edited here; changes to it go in its Amendments section.

| Gate | Date | Result | Evidence |
|---|---|---|---|
| R (rule) | 2026-10-25 | passed | The user approved the v2 prediction-time amendment (plan section 4) in the session, replying "yes to both the decisions". Recorded in CLAUDE.md under the prediction time rule. |
| T (terms) | 2026-10-25 | passed for local research | The user signed up (free plan) and read the terms at sign-up: nothing about AI or model training, storage limits, or a ban on personal research use. The written question to support about public display is still open, so nothing lineup-derived is published. |
| 0 coverage | 2026-10-25 | passed | `scripts.check_api_coverage`: `/leagues?id=39` marks lineups covered for every season 2010-11 to 2026-27 (player statistics from 2014-15, injuries from 2020-21). |
| 0 plan access | 2026-10-25 | blocks backfill | The free plan refuses fixtures for 2015 and 2026 ("Free plans do not have access to this season, try from 2022 to 2024"). The backfill (2015-16 to 2026-27) and the verdict season need a paid plan. |
| 0 timing | | not run | Polling each match's lineup from 90 minutes before kickoff on a matchday (not built yet; needs current-season access). |
| L (leakage, linking) | | not run | |
| D (development) | | not run | |

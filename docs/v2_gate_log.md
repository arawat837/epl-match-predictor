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
| L (leakage, linking) | 2026-10-25 | passed on the data so far; rerun after the backfill | `scripts.check_lineups`: all 1,140 fixtures of 2022-23 to 2024-25 link to `matches.parquet` (100%). 85 lineups fetched (2024-25 rounds 1 to 9; free plan: one request per match, no batch), all complete. Real code flagged on 0 of 50 stratified rebuilds and on none of the targeted samples. Planted leaks caught (random / targeted): bench counted as starters 10/10 and 10/10; previous XI from the next match 9/10 and 10/10; regular XI from later matches 4/10 and 10/10 (`reports/v2_lineup_checks.csv`). |
| D (development) | | not run | |

## v2+EWMA and v2-pre (plan amendment A, committed 2026-10-25 before any injury data was fetched)

| Gate | Date | Result | Evidence |
|---|---|---|---|
| L for EWMA form | 2026-10-25 | passed | `tests/test_ewma_form.py`: the real stratified 50-match sample rebuilds identically; the planted leak (no shift) is caught. |
| I (injury lists) | | waiting for data | `scripts.check_injuries` once the daily fetch has cached the injury lists for 2022-23 to 2024-25 (first run after 00:00 UTC on 2026-10-25). |
| L for v2-pre | | not run | Runs only if Gate I passes. |
| D for v2+EWMA, v2-pre | | not run | |

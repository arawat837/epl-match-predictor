# EPL match outcome predictor

Home, draw and away probabilities for English Premier League matches from free data, tested against the bookmaker.

## Problem

The model predicts the probability of a home win, a draw and an away win for each Premier League match, and the project
tests honestly how close a model built only from free data gets to bookmaker odds. The bookmaker is the benchmark: every
result below is shown next to the bookmaker's own probabilities on the same matches, with the overround removed.

## Data

- **football-data.co.uk**: results, match statistics and Bet365 odds as recorded in those files, one file per season from
  2005-06 on (2005-06 is used only as Elo burn-in).
- **FPL archive** (vaastav/Fantasy-Premier-League), 2016-17 to 2024-25: used only for the availability audit and the availability experiments, never in the final model.
- **Transfermarkt: not used.** Its terms of use, clause 11.1 as recorded in CLAUDE.md, prohibit accessing or copying its content by bots, spiders, screen scraping or other automated processes, and using its content to train AI or machine-learning systems.

## Method

- **Elo ratings**, updated match by match: K = 15, home advantage 50 rating points, carry-over 0.9 toward 1500 at each season change; a team not in the previous season starts at 1450.
- **Compact features** (home minus away): `elo_diff`, `season_ppg_diff`, `points_last10_diff`, `gf_last10_diff`,
  `ga_last10_diff`, `points_venue_last5_diff`, `days_rest_diff`.
- **Model**: multinomial L2 logistic regression, C = 0.03, with a median imputer and a scaler fitted on the training window only.
- **Walk-forward by season**: each test season is predicted by a model trained only on matches before it, from
  2006-07 on.

| Block | Seasons | Used for |
|---|---|---|
| Tuning | 2015-16 to 2019-20 | every modelling choice (Elo grid, C, feature groups) |
| Reporting | 2020-21 to 2024-25 | reported results; examined repeatedly |
| Holdout | 2025-26 | the single unbiased test, run once and now used up |
| Forward test | 2026-27 | live predictions logged before kickoff |

The final configuration is frozen in `config/final_model.json`, committed under the git tag `pre-holdout-config` before
the holdout was evaluated.

## How leakage is prevented

- **Prediction-time rule** (CLAUDE.md): a prediction is made about an hour before kickoff and may use only matches dated
  before the match date, injury or suspension spells that started before it, dated snapshots published before it and the
  squad list as of that date; nothing from the match itself.
- **Features use strictly earlier matches only**: rolling windows are shifted before rolling, Elo ratings are stored before
  each update, and a team returning after a missed season starts a new history.
- **Rebuild tests**: sampled matches have their features rebuilt from earlier rows only, with the match's own rows replaced by impossible values; the rebuilt values must equal the stored ones (sample seed 2026).
- **Planted leaks**: each check makes the leaky code build both the stored table and the rebuild, so a real leak shows up
  as rebuilt values that differ. Counts from `reports/planted_leaks.csv`:

| Stage | Check | Cases checked | Flagged |
|---|---|---|---|
| 4 features | real code: rebuilt from earlier rows, own stats scrambled | 50 | 0 |
| 4 features | real code (planted-leak sample) | 10 | 0 |
| 4 features | real code (planted-leak sample): last match before a missed season | 33 | 0 |
| 4 features | rolling window without shift(1) | 10 | 10 |
| 4 features | days rest measured to the next match | 10 | 10 |
| 4 features | season PPG includes this match | 10 | 8 |
| 4 features | Elo stores post-update ratings | 10 | 10 |
| 4 features | spell break read from the next match | 10 | 0 |
| 4 features | spell break read from the next match: last match before a missed season | 33 | 33 |
| 7 availability | real code: rebuilt from earlier rows, own rows scrambled | 50 | 0 |
| 7 availability | real code (planted-leak sample) | 10 | 0 |
| 7 availability | key players include the match's own minutes | 10 | 10 |
| 7 availability | price snapshot dated after the match | 10 | 10 |
| 7 availability | real rule: injury spell started before the match date (synthetic) | 1 | 0 |
| 7 availability | injury spell starting on the match date counted (synthetic) | 1 | 1 |
| 8 features | real code: rebuilt from earlier rows, own rows scrambled | 50 | 0 |
| 8 features | real code (planted-leak sample) | 10 | 0 |
| 8 features | recent_absence from match t's own minutes | 10 | 10 |
| 8 features | squad value from a snapshot dated after the match | 10 | 10 |

- **Leakage tripwire**: the first rule stopped work whenever any single season's accuracy exceeded 58%. The bookmaker itself crossed that line in several seasons, so the rule flagged ordinary predictable seasons rather than leaks:

| Season | Bookmaker accuracy | Matches |
|---|---|---|
| 2016-17 | 61.1% | 380 |
| 2018-19 | 58.7% | 380 |
| 2021-22 | 58.2% | 380 |
| 2023-24 | 59.7% | 380 |
| pooled | 55.5% | 3800 |

  It was replaced by a pooled rule: stop and audit if pooled accuracy across all test seasons exceeds 58%, or if any model's pooled log loss is lower than the bookmaker's. It has not fired on any reported result.

## Results

### Walk-forward, 2015-16 to 2024-25

All predictors on identical matches; models trained from 2006-07 on. Final model: compact logistic with tuned Elo.
Sources: `reports/model_metrics.csv`, final model from `reports/stage6_per_season.csv` (pooled = mean of the equal-size
seasons). These seasons were used for tuning and reporting and were examined repeatedly; only the holdout below is an
unbiased test.

**Log loss** (lower is better; always home gives zero probability to draws and away wins, so its log loss is undefined)

| Season | Uniform | Always home | Base rate | Elo-only (untuned) | Logistic, all features | XGBoost | Final model | Bookmaker |
|---|---|---|---|---|---|---|---|---|
| 2015-16 | 1.0986 | n/a | 1.0898 | 1.0347 | 1.0522 | 1.0395 | 1.0376 | 1.0352 |
| 2016-17 | 1.0986 | n/a | 1.0447 | 0.9358 | 0.9339 | 0.9269 | 0.9289 | 0.9065 |
| 2017-18 | 1.0986 | n/a | 1.0663 | 0.9612 | 0.9757 | 0.9650 | 0.9631 | 0.9455 |
| 2018-19 | 1.0986 | n/a | 1.0485 | 0.9153 | 0.9092 | 0.9171 | 0.9080 | 0.8929 |
| 2019-20 | 1.0986 | n/a | 1.0653 | 0.9804 | 0.9863 | 0.9828 | 0.9776 | 0.9732 |
| 2020-21 | 1.0986 | n/a | 1.0967 | 1.0491 | 1.0499 | 1.0309 | 1.0478 | 1.0070 |
| 2021-22 | 1.0986 | n/a | 1.0731 | 0.9647 | 0.9521 | 0.9741 | 0.9579 | 0.9372 |
| 2022-23 | 1.0986 | n/a | 1.0487 | 0.9691 | 0.9643 | 0.9727 | 0.9754 | 0.9662 |
| 2023-24 | 1.0986 | n/a | 1.0561 | 0.9349 | 0.9368 | 0.9454 | 0.9295 | 0.9092 |
| 2024-25 | 1.0986 | n/a | 1.0840 | 0.9935 | 1.0002 | 0.9920 | 0.9984 | 0.9708 |
| pooled | 1.0986 | n/a | 1.0673 | 0.9739 | 0.9761 | 0.9746 | 0.9724 | 0.9544 |

**Ranked probability score** (lower is better)

| Season | Uniform | Always home | Base rate | Elo-only (untuned) | Logistic, all features | XGBoost | Final model | Bookmaker |
|---|---|---|---|---|---|---|---|---|
| 2015-16 | 0.2308 | 0.4461 | 0.2290 | 0.2102 | 0.2123 | 0.2111 | 0.2113 | 0.2098 |
| 2016-17 | 0.2409 | 0.3974 | 0.2278 | 0.1897 | 0.1895 | 0.1880 | 0.1878 | 0.1810 |
| 2017-18 | 0.2344 | 0.4145 | 0.2257 | 0.1903 | 0.1913 | 0.1909 | 0.1898 | 0.1862 |
| 2018-19 | 0.2466 | 0.4303 | 0.2380 | 0.1916 | 0.1900 | 0.1927 | 0.1894 | 0.1857 |
| 2019-20 | 0.2374 | 0.4263 | 0.2301 | 0.2013 | 0.2016 | 0.2019 | 0.2003 | 0.1988 |
| 2020-21 | 0.2414 | 0.5118 | 0.2480 | 0.2257 | 0.2253 | 0.2219 | 0.2251 | 0.2137 |
| 2021-22 | 0.2392 | 0.4553 | 0.2359 | 0.1981 | 0.1939 | 0.2002 | 0.1961 | 0.1890 |
| 2022-23 | 0.2396 | 0.4013 | 0.2276 | 0.1997 | 0.1994 | 0.2002 | 0.2019 | 0.1990 |
| 2023-24 | 0.2418 | 0.4316 | 0.2340 | 0.1919 | 0.1900 | 0.1941 | 0.1897 | 0.1839 |
| 2024-25 | 0.2370 | 0.4697 | 0.2365 | 0.2048 | 0.2064 | 0.2013 | 0.2065 | 0.1972 |
| pooled | 0.2389 | 0.4384 | 0.2333 | 0.2003 | 0.2000 | 0.2002 | 0.1998 | 0.1944 |

**Accuracy**

| Season | Uniform | Always home | Base rate | Elo-only (untuned) | Logistic, all features | XGBoost | Final model | Bookmaker | Matches |
|---|---|---|---|---|---|---|---|---|---|
| 2015-16 | 41.3% | 41.3% | 41.3% | 46.8% | 47.6% | 46.6% | 47.4% | 47.4% | 380 |
| 2016-17 | 49.2% | 49.2% | 49.2% | 58.7% | 58.2% | 59.5% | 58.9% | 61.1% | 380 |
| 2017-18 | 45.5% | 45.5% | 45.5% | 55.8% | 53.9% | 54.5% | 56.6% | 55.3% | 380 |
| 2018-19 | 47.6% | 47.6% | 47.6% | 58.7% | 58.2% | 59.2% | 59.2% | 58.7% | 380 |
| 2019-20 | 45.3% | 45.3% | 45.3% | 53.2% | 52.4% | 52.6% | 52.9% | 52.9% | 380 |
| 2020-21 | 37.9% | 37.9% | 37.9% | 49.2% | 48.4% | 48.2% | 49.7% | 51.8% | 380 |
| 2021-22 | 42.9% | 42.9% | 42.9% | 55.0% | 56.8% | 55.5% | 56.6% | 58.2% | 380 |
| 2022-23 | 48.4% | 48.4% | 48.4% | 53.9% | 54.2% | 55.3% | 53.9% | 55.8% | 380 |
| 2023-24 | 46.1% | 46.1% | 46.1% | 57.6% | 57.6% | 57.6% | 57.4% | 59.7% | 380 |
| 2024-25 | 40.8% | 40.8% | 40.8% | 51.6% | 52.1% | 53.4% | 50.5% | 53.9% | 380 |
| pooled | 44.5% | 44.5% | 44.5% | 54.1% | 53.9% | 54.2% | 54.3% | 55.5% | 3800 |

### Holdout, 2025-26 (run once)

Source: `reports/stage10_holdout.csv`.

| Predictor | Matches | Log loss | RPS | Accuracy |
|---|---|---|---|---|
| final model | 380 | 1.0271 | 0.2090 | 48.7% |
| bookmaker | 380 | 1.0185 | 0.2057 | 48.9% |
| base rate | 380 | 1.0820 | 0.2277 | 42.6% |
| Elo-only (original, untuned) | 380 | 1.0278 | 0.2095 | 47.1% |

Paired per-match log loss difference, final model minus reference (negative = model better), as recorded in
`reports/stage10_holdout.md`:

| Final model minus | Difference | Standard error | z |
|---|---|---|---|
| bookmaker | 0.0085 | 0.0081 | 1.0536 |
| Elo-only (original, untuned) | -0.0007 | 0.0033 | -0.2135 |

### Confidence at equal coverage

Accuracy (matches) on each predictor's own subsets; the "most confident" rows compare the two at equal coverage. Pooled columns cover 2016-17 to 2024-25, seasons the model was tuned or reported on; holdout columns cover 2025-26. Cells under 100 matches are marked unreliable. Sources: `reports/stage9_confidence.csv`, `reports/stage10_confidence.csv`.

| Subset | Model, pooled accuracy (matches) | Bookmaker, pooled accuracy (matches) | Model, holdout accuracy (matches) | Bookmaker, holdout accuracy (matches) |
|---|---|---|---|---|
| top probability > 0.45 | 60.4% (2438) | 63.1% (2388) | 52.5% (263) | 53.4% (262) |
| top probability > 0.50 | 63.7% (1960) | 67.3% (1878) | 55.8% (199) | 55.9% (195) |
| top probability > 0.55 | 67.5% (1466) | 69.7% (1527) | 58.3% (139) | 61.4% (140) |
| top probability > 0.60 | 70.9% (1094) | 73.5% (1144) | 64.5% (93) unreliable | 68.9% (90) unreliable |
| top probability > 0.65 | 73.9% (793) | 75.3% (878) | 68.4% (57) unreliable | 71.9% (57) unreliable |
| most confident 10% | 80.4% (342) | 81.0% (342) | 68.4% (38) unreliable | 71.1% (38) unreliable |
| most confident 20% | 73.7% (684) | 76.2% (684) | 67.1% (76) unreliable | 67.1% (76) unreliable |
| most confident 30% | 71.8% (1026) | 75.2% (1026) | 63.2% (114) | 65.8% (114) |

## What did not work

- **XGBoost did not beat Elo-only**: pooled log loss 0.9746 against 0.9739 for logistic regression on the Elo difference alone (`reports/model_metrics.csv`).
- **Stage 6 tuning gains were within noise.** Choices were made on the tuning seasons, then scored once on the reporting seasons, where the original Elo-only model scored 0.9823 (`reports/stage6_vs_original.csv`):

| Model | Reporting log loss | Minus original Elo-only | Standard error | Verdict vs original Elo-only |
|---|---|---|---|---|
| logistic (all), stage 5 | 0.9807 | -0.0016 | 0.0037 | beats, within noise |
| xgboost (all), stage 5 | 0.9830 | +0.0008 | 0.0036 | does not beat |
| elo only, tuned Elo (K=15, home_adv=50, carryover=0.9) | 0.9814 | -0.0008 | 0.0014 | beats, within noise |
| compact logistic (C=0.03) | 0.9818 | -0.0005 | 0.0018 | beats, within noise |
| compact xgboost (depth 2, mcw 20, lr 0.03) | 0.9874 | +0.0051 | 0.0027 | does not beat |

- **Stage 8 availability and form groups were tested and not adopted.** They were added as an offset on the frozen model
  under a pre-registered rule. The groups were proxies: suspensions derived from FPL cards, an FPL price index in place of
  market value, FPL BPS and ICT in place of player ratings, and an injury PROXY built from zero minutes in the previous
  match (`reports/stage8_decisions.csv`, `reports/stage8_differences.csv`):

| Step | Groups (cumulative) | Lambda | Tuning minus base (SE) | Reporting minus base (SE) | Reporting seasons won | Decision |
|---|---|---|---|---|---|---|
| 1 | suspension | 0.1 | +0.0021 (SE 0.0014) | +0.0006 (SE 0.0004) | 0 of 5 | not adopted |
| 2 | suspension + squad_value | 0.1 | +0.0025 (SE 0.0032) | +0.0003 (SE 0.0011) | 3 of 5 | not adopted |
| 3 | suspension + squad_value + form | 0.1 | +0.0021 (SE 0.0037) | +0.0009 (SE 0.0013) | 2 of 5 | not adopted |
| 4 | suspension + squad_value + form + recent_absence | 0.1 | +0.0020 (SE 0.0037) | +0.0006 (SE 0.0014) | 4 of 5 | not adopted |

- **Temperature scaling was dropped**: tuning log loss 0.9444 without scaling against 0.9546 with it; on the reporting seasons 0.9818 against 0.9853 (`reports/stage9_calibration.csv`).

## Limitations

- No injury, suspension or lineup data is used; the injury feature, where tested, was a proxy.
- Draws are never predicted, so every draw counts as wrong: in the holdout confusion matrix the predicted-draw column is 0 for actual home wins, 0 for actual draws and 0 for actual away wins (`reports/stage10_holdout.md`).
- Away wins are under-predicted: in 10 of the 10 away-win reliability deciles the observed rate exceeds the predicted one, by 0.6 to 5.9 points (`reports/stage9_reliability.csv`).
- Newly promoted teams start from a default rating (1450), not from their second-tier form.
- The forward model was fitted once on every match from 2006-07 through 2025-26 and is not refitted during 2026-27.
- The tuning and reporting seasons were examined repeatedly, so only the holdout is unbiased.
- One season is 380 matches, so a single-season accuracy has a standard error of roughly 2.6 points (the square root of p(1-p)/n at the holdout accuracy).
- The holdout was a hard season for both model and bookmaker: the model's holdout log loss was 1.0271 against 0.9818 on the reporting seasons, and the bookmaker's 1.0185 against 0.9581.

## How to run

Windows PowerShell, from the project root:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m pytest
```

Weekly forward test (commit any code changes first, so the logged commit hash matches the code):

```powershell
git status
.venv\Scripts\python -m scripts.predict_upcoming
.venv\Scripts\python -m scripts.score_forward
```

App (offline):

```powershell
.venv\Scripts\streamlit run app/app.py
```

In Windows PowerShell 5.1, write commit messages that contain double quotes to a file and use `git commit -F <file>`; passing them with `-m` mangles the quotes.

## Forward test

`data/forward/predictions_log.csv` is append-only: rows are never edited or deleted, fixtures that have kicked off are refused, and a logged fixture gets a new row only when new results change its inputs. Scoring takes, for each played match, the latest prediction made before its actual kickoff and compares it with the bookmaker's odds in the same results file, with standard errors; below 100 scored matches it reports "too few matches to conclude". Current record (`reports/forward_score.csv`): 0 scored matches, too few matches to conclude.

The first 9 predictions were logged at 2026-10-24 00:53:30Z from the working tree, the code was committed as 84320e1 at 01:01:52Z, both before the first kickoff (11:30Z), and recomputing the 9 predictions from the committed code reproduces them exactly (max difference 0.0).

Kickoff times are stored in UTC and converted from UK local time with the Europe/London time zone.

## Findings

(to be written by the author)

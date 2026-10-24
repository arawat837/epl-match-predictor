# EPL Match Outcome Predictor

Predicts Home / Draw / Away probabilities for English Premier League matches.
These rules apply for the whole project. If a rule blocks something, stop and ask.

## Stack and environment
- Python 3.11+ (use `py -3.12`; `python` is not on PATH on this machine).
- Libraries: numpy, pandas, pyarrow (parquet), scikit-learn, scipy (optimize, Stage 8), xgboost,
  matplotlib, streamlit, pytest. Nothing else without asking.
- Always work in the project venv: `py -3.12 -m venv .venv`, then `.venv\Scripts\Activate.ps1`.
- All dependencies pinned in `requirements.txt`. Add a package there before importing it.

## Commands (from the project root)
- Build data: `.venv\Scripts\python -m scripts.build_dataset` (downloads, writes
  `data/processed/matches.parquet`, prints the quality report, exits 1 if a check fails)
- Score baselines: `.venv\Scripts\python -m scripts.evaluate_baselines` (walk-forward,
  writes `reports/baseline_metrics.csv`, exits 1 if the leakage alarm fires)
- Build features: `.venv\Scripts\python -m scripts.build_features` (evaluation seasons only,
  writes `data/processed/features.parquet`, prints top/bottom Elo). Rebuild after changing feature code.
- Score models: `.venv\Scripts\python -m scripts.evaluate_models` (baselines + three models,
  writes `reports/model_metrics.csv` and `reports/xgb_feature_importance.png/.csv`, exits 1 if
  the leakage tripwire fires)
- Stage 6 tuning: `.venv\Scripts\python -m scripts.tune_models` (tune on 2015-16..2019-20,
  report once on 2020-21..2024-25, writes `reports/stage6_*.csv`, exits 1 if the tripwire fires)
- Availability audit: `.venv\Scripts\python -m scripts.audit_availability` (FPL archive cached in
  `data/raw/fpl/`, coverage report, writes `data/processed/availability.parquet`; audit only)
- Stage 8 evaluation: `.venv\Scripts\python -m scripts.evaluate_availability` (gating check, builds
  `data/processed/availability_features.parquet`, offset-model steps, writes `reports/stage8_*.csv`)
- Stage 9 analysis: `.venv\Scripts\python -m scripts.analyse_final_model` (calibration test,
  reliability, confidence vs bookmaker; writes `reports/stage9_*`)
- Tests: `.venv\Scripts\python -m pytest` (about two minutes; leakage and model fold tests are most of it)

## Data leakage rules (non-negotiable)
- Never use random `train_test_split` or shuffled K-fold. Every split is by date.
- Evaluation is walk-forward by season: for season S, fit on seasons before S only, predict S.
  Hyperparameter tuning happens inside the training seasons only (nested walk-forward).
- Features for a match on date d may use only matches with date strictly before d.
  - Per-team rolling stats are computed on the team's sorted history and shifted by one.
  - League-wide aggregates and ratings (e.g. Elo) are updated only from matches on earlier
    dates, so other games played the same day never leak in.
  - Teams with no history (promoted sides, season starts) get explicit defaults, never backfill:
    Elo 1500 in the first season and 1450 for promoted/returning sides, last-season PPG 1.0,
    rolling stats NaN until 3 earlier matches, days_rest NaN before a team's first match.
- Never use same-match stats as inputs for that match: shots, shots on target, corners, fouls,
  cards, half-time score, full-time score, result. They may only feed features for later matches.
- Scalers, encoders and calibrators are fit on the training fold only.
- Pre-match bookmaker odds are a baseline. Using them as model features needs explicit approval.

## Prediction time rule
- PREDICTION TIME RULE: a prediction is made about 1 hour before kickoff. Features may use only:
  matches dated before the match date; injury/suspension spells that STARTED before the match date;
  dated market-value snapshots published before the match date; squad lists as of that date. Never
  use anything from the match itself (minutes, cards, goals, ratings, BPS, injuries starting during
  it), the FPL xP column (look-ahead bias), or a spell's recorded end date for anything except
  'unavailable at kickoff'.

## Final holdout
- The latest complete season is the final holdout: currently 2025-26.
- Do not load, train on, tune on, evaluate on or plot the holdout until the user says so.
  `splits.py` enforces this and raises unless the holdout is explicitly unlocked.
- Exception: ingestion and the integrity checks in `src/quality.py` (row counts, missing
  values, duplicates, dates) cover every season. Never add outcome or odds statistics there.
- Matches after the holdout (the in-progress 2026-27 season) are also out of bounds for evaluation.

## Evaluation harness
- Walk-forward test seasons: `FIRST_TEST_SEASON` (2015-16) up to, not including, `HOLDOUT_SEASON`
  (both in `src/config.py`). Load data for evaluation only via `splits.load_evaluation_matches`.
- A predictor is `f(train, test) -> DataFrame[H, D, A]` indexed like `test`. It sees the test
  season only through `evaluate.pre_match_view` (goals, result and match stats removed).
- Log loss is not clipped: a 0/1 forecast (always home) scores infinity internally and is
  reported as n/a (judge it on RPS and accuracy). Accuracy ties go to H.

## Features (user's exact spec; don't substitute a different design)
- `src/elo.py`, `EloParams(K=20, home_adv=80, start=1500, promoted_start=1450, carryover=0.75)`.
  Matches in date order; store pre-match elo_home/elo_away/elo_diff, then update with
  delta = K * g * (actual - expected_home), g = 1 / 1.5 / (11+|GD|)/8. At each season change
  last season's teams go to 1500 + carryover * (r - 1500); anyone else starts at promoted_start.
  K and home_adv are not tuned yet.
- `src/features.py`: long table (one row per team per match), groupby team, `shift(1)` before
  `rolling`, `min_periods=3`, windows cross seasons, except that a gap of more than 200 days since
  the team's previous match starts a new spell (rolling restarts, days_rest NaN, last_season_ppg
  1.0). Real gaps: at most 107 days within a run of seasons, at least 384 after a missed season.
  Last 5 and 10: points, gf, ga, shots_for,
  shots_against, sot_for. Last 5 at this venue: points, gf, ga (`*_venue_last5`). `days_rest`
  capped at 14. `season_ppg` = (5 * last_season_ppg + points_so_far) / (5 + games_so_far),
  last_season_ppg 1.0 for promoted teams and the first season.
- 54 features: elo_home/elo_away/elo_diff, then home_X, away_X and X_diff (home minus away).
  `burn_in` flags the first season (kept, not a feature).
- `tests/test_leakage.py` rebuilds 50 random matches from rows dated strictly before them (plus
  the match itself with its own stats scrambled) and requires identical features.

## Models (`src/models.py`, untuned)
- Model table (`src/dataset.py`): evaluation matches joined one-to-one with features.parquet,
  burn-in rows dropped from training and evaluation. Inputs are every non-match column (54);
  goals, results, match stats and odds are never inputs.
- `elo_only`: multinomial LogisticRegression on elo_diff. `LogisticModel`: all features in a
  Pipeline(SimpleImputer(median), StandardScaler, LogisticRegression), fitted per training window.
- `XGBoostModel`: multi:softprob, max_depth 3, lr 0.04, subsample/colsample 0.8, random_state 0;
  early stopping (50 rounds, max 600 trees) on the training window's last season, then refit on
  the whole window with that tree count. Its probabilities are float32.
- `tests/test_models.py` checks every fold: chronology, no burn-in/holdout, imputer and scaler
  statistics from the training window only, early-stopping season, valid probabilities, and
  identical results on a re-run.
- Current result (2015-16 to 2024-25): no model beats the bookmaker (pooled log loss 0.954 vs
  0.974-0.976); XGBoost does not beat Elo-only.

## Tuning protocol (Stage 6, `src/tuning.py`)
- Tuning seasons 2015-16..2019-20 choose every setting; the choice is frozen and scored once on
  the reporting seasons 2020-21..2024-25 (`FIRST_REPORTING_SEASON`). Never evaluate grid
  candidates on reporting seasons. Each season's model still trains only on earlier matches.
- Reporting seasons were already seen in Stage 5, so they are not a clean test; only the
  holdout is.
- Frozen choices: Elo K=15, home_adv=50, carryover=0.9 (grid edge for home_adv and carryover;
  the surface is flat, top 5 within 0.0003). Compact logistic C=0.03 on `COMPACT_FEATURES`.
  These apply via `tuning.with_elo`; features.parquet still holds the default Elo.
- Result on reporting seasons (log loss): original Elo-only 0.9823, tuned Elo-only 0.9814,
  compact logistic 0.9818, compact XGBoost 0.9874, bookmaker 0.9581. No gain beats noise
  (all within 1 standard error of a paired per-match difference).

## Availability data (Stage 7 audit; not in features.parquet or any model)
- Transfermarkt: do not scrape or use. Its terms (clause 11.1) forbid access by bots, spiders,
  screen scraping or other automated processes and forbid using its content to train AI/ML.
  That rules out Transfermarkt market values and injury logs, including third-party copies.
- FPL archive (vaastav/Fantasy-Premier-League): 2016-17 to 2024-25 only (no 2015-16; holdout
  seasons never downloaded). Every match has player rows for both sides. Rows are per match
  (point-in-time); `players_raw.csv` status/news/team are end-of-season snapshots, never use them
  historically. `team` and `position` columns exist only from 2020-21 (team is derived from the
  fixture's sides for every season), `starts` only from 2022-23. Never read `xP`.
- FPL `code` is the persistent player id. FPL team names map to clubs via exact name, then
  `data/manual/fpl_team_names.csv`, then fuzzy match; minutes-weighted link rate 100% (fails <98%).
- FPL live API (bootstrap-static) has status, chance_of_playing_next/this_round, news,
  news_added, removed, team_join_date: current snapshot only, for the future app, never training.
- `src/availability.py` (all from rows dated strictly before the match; squad = FPL listing for
  the fixture, identity only): one-match bans (red, or 5/10/15 yellows by team match 19/32/38),
  top-11 key players over the previous 10 matches, FPL-price squad value, minutes-weighted
  BPS/ICT over the previous 5. Ban check: 89% of red and 93% of yellow bans match a player who
  didn't play; 9 of 10 hand-checked bans right (misses: bans served in cups, rescinded reds).
- No injury source exists; `unavailable_at_kickoff` implements the rule for a future one.

## Availability features (Stage 8; evaluated, none adopted)
- Gating check passed: FPL lists the whole registered squad per fixture (29-39 players per team per
  match, 51-61% with 0 minutes), so the squad list is the fixture listing, identity only
  (`availability.squad_list`). The new features don't use the listing at all.
- `src/availability_features.py`: suspension (banned players' share of last-10 minutes), squad_value
  (key-player FPL price sum / league mean as of the date over the season's teams seen so far; a
  full-season mean would look ahead), form_bps / form_ict, recent_absence (INJURY PROXY: key set over
  t-11..t-2, share of its minutes from players with 0 minutes in t-1; NaN for a team's first 5 matches
  of a season). Each as home_X, away_X, X_diff.
- `src/offset.py`: logits = log p_base + X W (draw column 0), mean log loss + lambda * sum(W**2), L-BFGS;
  X standardised on the training window, NaN -> 0. Base = frozen Stage 6 compact logistic with tuned
  Elo, out-of-sample from 2016-17. Offset trains on 2016-17..S-1; tuning 2017-18..2019-20, reporting
  2020-21..2024-25; lambda from {0.001, 0.003, 0.01, 0.03, 0.1} on tuning seasons only.
- Pre-registered rule (beat base on tuning, on reporting pooled, and in >= 3 of 5 reporting seasons):
  no group adopted. Lambda chose 0.1, the strongest shrinkage, at every step. Robustness B (compact
  logistic with vs without, windows from 2016-17): with is worse. Don't revisit these features using
  reporting results.

## Final model (frozen, Stage 9)
- `config/final_model.json` is the final model, committed under git tag `pre-holdout-config`:
  tuned Elo (15/50/0.9), the 7 compact features, L2 logistic C=0.03, median imputer + scaler per
  training window. `src/final_model.py` builds it; `tests/test_final_model.py` pins it to the code.
  Do not edit the config after the holdout is evaluated.
- Temperature scaling (T fitted on season S-1's out-of-sample forecasts, applied to S) was tested
  and NOT kept: tuning log loss 0.9444 raw vs 0.9546 scaled; reporting 0.9818 vs 0.9853.
- Reliability 2016-17..2024-25: home wins well calibrated; top draw decile over-predicted
  (0.30 vs 0.24); away wins under-predicted by 2-6 points across deciles.
- Confidence (pooled 2016-17..2024-25, 3,420 matches): model's most confident 10% (342 matches)
  80.4% correct vs bookmaker's own most confident 10% 81.0%; 20%: 73.7% vs 76.2%; 30%: 71.8% vs 75.2%.
  Per-season subsets are under 100 matches, so only pooled figures are reliable.

## Metrics and reporting
- Report log loss and ranked probability score (RPS, outcome order H, D, A) first; accuracy second.
- Every result is shown next to baselines on the same matches:
  uniform (1/3 each), base rate (outcome frequencies from training seasons),
  and bookmaker implied probabilities (margin removed).
- Report per season and pooled across the walk-forward seasons.

## Leakage tripwire
- Leakage tripwire: stop and audit if pooled accuracy across all test seasons exceeds 58%, or if
  any model's pooled log loss beats the bookmaker baseline. Single-season accuracy above 58% is
  expected in seasons where the bookmaker itself exceeds it.
- When it fires: do not continue or tune further. Audit for leakage, report findings to the
  user, and wait. `evaluate.leakage_alarms` implements it; scripts exit 1 when it fires.

## Code style
- Small, single-purpose functions with type hints on every signature.
- One module per concern under `src/`, imported as `from src.<module> import ...`; run
  everything from the project root. Notebooks and scripts hold no logic, they only call into `src/`.
- Tests in `tests/` with pytest. Every feature gets a test proving it uses only earlier dates.
- Commit after each stage, with the stage named in the message.

## Stages
0. Rules and layout (this file)
1. Data: environment, download and clean season CSVs into one match table, quality report
2. Evaluation harness: splits, metrics, baselines, walk-forward runner (baselines scored first)
3. Features, first design (superseded by stage 4)
4. Features to the user's spec: Elo with season carry-over, form, rest, season PPG, leakage tests
5. Models: multinomial logistic regression, then XGBoost
6. Honest tuning: Elo grid, compact logistic, compact XGBoost (tune/report split)
7. Availability and form data audit (FPL archive; no modelling)
8. Availability and form features on an offset model (pre-registered rule; none adopted)
9. Freeze the final model, calibration test, reliability, confidence analysis
10. Streamlit app
11. Holdout evaluation (only when the user says so)

## Data
- Source: football-data.co.uk EPL files, `mmz4281/{code}/E0.csv`, 2005-06 to the current season.
- `data/processed/matches.parquet` columns: date, season ("2025-26"), home, away, FTHG, FTAG,
  result (H/D/A), HS, AS, HST, AST, odds_home/draw/away, odds_source.
- Odds: Bet365 first, then Pinnacle, other books, market average. All three prices for a
  match come from one bookmaker; `odds_source` says which.
- Team names: full club names via `TEAM_NAMES` in `src/teams.py`. An unmapped name raises;
  add newly promoted clubs there.

## Layout (planned modules marked *)
```
├── CLAUDE.md
├── requirements.txt           # pinned deps
├── pyproject.toml             # pytest config (puts the project root on the path)
├── config/
│   └── final_model.json       # frozen final model (tag pre-holdout-config)
├── .gitignore
├── data/
│   ├── raw/                   # gitignored: E0_{code}.csv, fpl/ archive, fpl_api/ snapshot
│   ├── processed/             # gitignored: matches, features, availability parquet
│   └── manual/                # tracked: fpl_team_names.csv overrides
├── src/
│   ├── config.py              # paths and constants
│   ├── seasons.py             # season start year / code / label helpers
│   ├── teams.py               # team-name standardisation
│   ├── data.py                # download_epl, cleaning, build matches.parquet
│   ├── quality.py             # integrity checks and the data-quality report
│   ├── elo.py                 # pre-match Elo with season carry-over
│   ├── features.py            # long table, rolling form, rest, season ppg, feature table
│   ├── splits.py              # season folds, walk-forward generator, holdout guard
│   ├── odds.py                # odds -> implied probabilities, margin removal
│   ├── baselines.py           # uniform, always-home, base-rate, bookmaker baselines
│   ├── dataset.py             # matches joined with features, burn-in dropped
│   ├── models.py              # Elo-only, logistic pipeline and XGBoost predictors
│   ├── tuning.py              # Stage 6 tune/report protocol, grids, paired comparison
│   ├── fpl.py                 # FPL archive download/cache and per-season loading (no xP)
│   ├── name_maps.py           # FPL team names -> clubs, FPL rows -> matches, link rate
│   ├── availability.py        # point-in-time bans, key players, squad value, form
│   ├── audit.py               # Stage 7 coverage report, ban check, Stage 8 gating check
│   ├── availability_features.py # Stage 8 suspension, squad value, form, recent absence
│   ├── offset.py              # offset model on frozen base probabilities
│   ├── experiments.py         # Stage 8 protocol: base OOS, folds, lambda, decision rule
│   ├── final_model.py         # loads config/final_model.json, builds the final predictor
│   ├── calibration.py         # temperature scaling fitted on the previous season
│   ├── confidence.py          # reliability deciles, confidence subsets vs bookmaker
│   ├── metrics.py             # log loss, RPS, accuracy
│   ├── evaluate.py            # walk-forward runner, metric tables, leakage tripwire
│   └── plots.py               # report figures (feature importance; calibration later)
├── scripts/                   # thin CLI entry points
│   ├── build_dataset.py
│   ├── evaluate_baselines.py
│   ├── build_features.py
│   ├── evaluate_models.py
│   ├── tune_models.py
│   ├── audit_availability.py
│   ├── evaluate_availability.py
│   └── analyse_final_model.py
├── app/
│   └── streamlit_app.py *     # UI only; calls into src/
├── tests/                     # one test module per src module; conftest.py has synthetic seasons
└── reports/                   # generated tables and figures (tracked)
```

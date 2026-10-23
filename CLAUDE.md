# EPL Match Outcome Predictor

Predicts Home / Draw / Away probabilities for English Premier League matches.
These rules apply for the whole project. If a rule blocks something, stop and ask.

## Stack and environment
- Python 3.11+ (use `py -3.12`; `python` is not on PATH on this machine).
- Libraries: numpy, pandas, pyarrow (parquet), scikit-learn, xgboost, matplotlib, streamlit,
  pytest. Nothing else without asking.
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
- Tests: `.venv\Scripts\python -m pytest` (about a minute; leakage and model fold tests are most of it)

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
6. Reporting: metric tables, calibration and per-season plots
7. Streamlit app
8. Holdout evaluation (only when the user says so)

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
├── .gitignore
├── data/                      # contents gitignored
│   ├── raw/                   # cached per-season CSVs, E0_{code}.csv
│   └── processed/             # matches.parquet, features.parquet
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
│   ├── metrics.py             # log loss, RPS, accuracy
│   ├── evaluate.py            # walk-forward runner, metric tables, leakage tripwire
│   └── plots.py               # report figures (feature importance; calibration later)
├── scripts/                   # thin CLI entry points
│   ├── build_dataset.py
│   ├── evaluate_baselines.py
│   ├── build_features.py
│   └── evaluate_models.py
├── app/
│   └── streamlit_app.py *     # UI only; calls into src/
├── tests/                     # one test module per src module; conftest.py has synthetic seasons
└── reports/                   # generated tables and figures (tracked)
```

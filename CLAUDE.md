# EPL Match Outcome Predictor

Predicts Home / Draw / Away probabilities for English Premier League matches.
These rules apply for the whole project. If a rule blocks something, stop and ask.

## Stack and environment
- Python 3.11+ (use `py -3.12`; `python` is not on PATH on this machine).
- Libraries: pandas, pyarrow (parquet), scikit-learn, xgboost, matplotlib, streamlit, pytest.
  Nothing else without asking.
- Always work in the project venv: `py -3.12 -m venv .venv`, then `.venv\Scripts\Activate.ps1`.
- All dependencies pinned in `requirements.txt`. Add a package there before importing it.

## Commands (from the project root)
- Build data: `.venv\Scripts\python -m scripts.build_dataset` (downloads, writes
  `data/processed/matches.parquet`, prints the quality report, exits 1 if a check fails)
- Tests: `.venv\Scripts\python -m pytest`

## Data leakage rules (non-negotiable)
- Never use random `train_test_split` or shuffled K-fold. Every split is by date.
- Evaluation is walk-forward by season: for season S, fit on seasons before S only, predict S.
  Hyperparameter tuning happens inside the training seasons only (nested walk-forward).
- Features for a match on date d may use only matches with date strictly before d.
  - Per-team rolling stats are computed on the team's sorted history and shifted by one.
  - League-wide aggregates and ratings (e.g. Elo) are updated only from matches on earlier
    dates, so other games played the same day never leak in.
  - Teams with no history (promoted sides, season starts) get explicit defaults, never backfill.
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

## Metrics and reporting
- Report log loss and ranked probability score (RPS, outcome order H, D, A) first; accuracy second.
- Every result is shown next to baselines on the same matches:
  uniform (1/3 each), base rate (outcome frequencies from training seasons),
  and bookmaker implied probabilities (margin removed).
- Report per season and pooled across the walk-forward seasons.

## Leakage alarm
- If accuracy exceeds 58% on any evaluation, stop. Do not continue or tune further.
  Audit for leakage, report findings to the user, and wait.

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
3. Features: rolling form, Elo, leakage tests
4. Models: multinomial logistic regression, then XGBoost
5. Reporting: metric tables, calibration and per-season plots
6. Streamlit app
7. Holdout evaluation (only when the user says so)

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
│   └── processed/             # matches.parquet, later feature tables
├── src/
│   ├── config.py              # paths and constants
│   ├── seasons.py             # season start year / code / label helpers
│   ├── teams.py               # team-name standardisation
│   ├── data.py                # download_epl, cleaning, build matches.parquet
│   ├── quality.py             # integrity checks and the data-quality report
│   ├── rolling.py *           # per-team shifted rolling form stats
│   ├── elo.py *               # date-ordered Elo ratings
│   ├── features.py *          # assembles the pre-match feature matrix
│   ├── splits.py *            # season folds, walk-forward generator, holdout guard
│   ├── odds.py *              # odds -> implied probabilities, margin removal
│   ├── baselines.py *         # uniform, base-rate, bookmaker baselines
│   ├── models.py *            # logistic regression and XGBoost wrappers
│   ├── metrics.py *           # log loss, RPS, accuracy, comparison table
│   ├── evaluate.py *          # walk-forward runner + 58% leakage alarm
│   └── plots.py *             # calibration and per-season metric charts
├── scripts/
│   └── build_dataset.py       # thin CLI entry points
├── app/
│   └── streamlit_app.py *     # UI only; calls into src/
├── tests/                     # one test module per src module; conftest.py has synthetic seasons
└── reports/ *                 # generated tables and figures (tracked)
```

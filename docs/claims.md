# Claims audit for README.md

Every number in README.md, with the file it comes from and how it is read. `tests/test_readme_claims.py`
re-reads each one and checks it equals the README text after the same rounding. Selector syntax is
documented at the top of that test.

Exceptions (not from reports/ or config/), read from CLAUDE.md where they are recorded: the Transfermarkt
clause number, the two rule thresholds (58% tripwire, 100-match cut-off) and the PowerShell version in
the commit-message note.

| # | Claim as written | Source | Selector | Format |
|---|---|---|---|---|
| 1 | 2015-16 | `config/final_model.json` | `key tuning_seasons.0` | `str` |
| 2 | 2019-20 | `config/final_model.json` | `key tuning_seasons.4` | `str` |
| 3 | 2020-21 | `config/final_model.json` | `key reporting_seasons.0` | `str` |
| 4 | 2024-25 | `config/final_model.json` | `key reporting_seasons.4` | `str` |
| 5 | 2025-26 | `config/final_model.json` | `key holdout_season` | `str` |
| 6 | 2026-27 | `reports/forward_provenance.json` | `key forward_season` | `str` |
| 7 | 2005-06 | `config/final_model.json` | `key training.burn_in_season_excluded` | `str` |
| 8 | 2006-07 | `config/final_model.json` | `key training.first_training_season` | `str` |
| 9 | 380 | `reports/stage10_holdout.csv` | `predictor=final model -> matches` | `d` |
| 10 | 1.0271 | `reports/stage10_holdout.csv` | `predictor=final model -> log_loss` | `.4f` |
| 11 | 0.2090 | `reports/stage10_holdout.csv` | `predictor=final model -> rps` | `.4f` |
| 12 | 48.7% | `reports/stage10_holdout.csv` | `predictor=final model -> accuracy` | `.1%` |
| 13 | 380 | `reports/stage10_holdout.csv` | `predictor=bookmaker -> matches` | `d` |
| 14 | 1.0185 | `reports/stage10_holdout.csv` | `predictor=bookmaker -> log_loss` | `.4f` |
| 15 | 0.2057 | `reports/stage10_holdout.csv` | `predictor=bookmaker -> rps` | `.4f` |
| 16 | 48.9% | `reports/stage10_holdout.csv` | `predictor=bookmaker -> accuracy` | `.1%` |
| 17 | 380 | `reports/stage10_holdout.csv` | `predictor=base rate -> matches` | `d` |
| 18 | 1.0820 | `reports/stage10_holdout.csv` | `predictor=base rate -> log_loss` | `.4f` |
| 19 | 0.2277 | `reports/stage10_holdout.csv` | `predictor=base rate -> rps` | `.4f` |
| 20 | 42.6% | `reports/stage10_holdout.csv` | `predictor=base rate -> accuracy` | `.1%` |
| 21 | 380 | `reports/stage10_holdout.csv` | `predictor=Elo-only (original, untuned) -> matches` | `d` |
| 22 | 1.0278 | `reports/stage10_holdout.csv` | `predictor=Elo-only (original, untuned) -> log_loss` | `.4f` |
| 23 | 0.2095 | `reports/stage10_holdout.csv` | `predictor=Elo-only (original, untuned) -> rps` | `.4f` |
| 24 | 47.1% | `reports/stage10_holdout.csv` | `predictor=Elo-only (original, untuned) -> accuracy` | `.1%` |
| 25 | 0.0085 | `reports/stage10_holdout.md` | `md final model minus=bookmaker -> difference` | `str` |
| 26 | 0.0081 | `reports/stage10_holdout.md` | `md final model minus=bookmaker -> standard_error` | `str` |
| 27 | 1.0536 | `reports/stage10_holdout.md` | `md final model minus=bookmaker -> z` | `str` |
| 28 | -0.0007 | `reports/stage10_holdout.md` | `md final model minus=Elo-only (original, untuned) -> difference` | `str` |
| 29 | 0.0033 | `reports/stage10_holdout.md` | `md final model minus=Elo-only (original, untuned) -> standard_error` | `str` |
| 30 | -0.2135 | `reports/stage10_holdout.md` | `md final model minus=Elo-only (original, untuned) -> z` | `str` |
| 31 | 0.45 | `reports/stage9_confidence.csv` | `predictor=final model; subset=top probability > 0.45 -> subset` | `text` |
| 32 | 60.4% | `reports/stage9_confidence.csv` | `predictor=final model; subset=top probability > 0.45 -> accuracy` | `.1%` |
| 33 | 2438 | `reports/stage9_confidence.csv` | `predictor=final model; subset=top probability > 0.45 -> matches` | `d` |
| 34 | 63.1% | `reports/stage9_confidence.csv` | `predictor=bookmaker; subset=top probability > 0.45 -> accuracy` | `.1%` |
| 35 | 2388 | `reports/stage9_confidence.csv` | `predictor=bookmaker; subset=top probability > 0.45 -> matches` | `d` |
| 36 | 52.5% | `reports/stage10_confidence.csv` | `predictor=final model; subset=top probability > 0.45 -> accuracy` | `.1%` |
| 37 | 263 | `reports/stage10_confidence.csv` | `predictor=final model; subset=top probability > 0.45 -> matches` | `d` |
| 38 | 53.4% | `reports/stage10_confidence.csv` | `predictor=bookmaker; subset=top probability > 0.45 -> accuracy` | `.1%` |
| 39 | 262 | `reports/stage10_confidence.csv` | `predictor=bookmaker; subset=top probability > 0.45 -> matches` | `d` |
| 40 | 0.50 | `reports/stage9_confidence.csv` | `predictor=final model; subset=top probability > 0.50 -> subset` | `text` |
| 41 | 63.7% | `reports/stage9_confidence.csv` | `predictor=final model; subset=top probability > 0.50 -> accuracy` | `.1%` |
| 42 | 1960 | `reports/stage9_confidence.csv` | `predictor=final model; subset=top probability > 0.50 -> matches` | `d` |
| 43 | 67.3% | `reports/stage9_confidence.csv` | `predictor=bookmaker; subset=top probability > 0.50 -> accuracy` | `.1%` |
| 44 | 1878 | `reports/stage9_confidence.csv` | `predictor=bookmaker; subset=top probability > 0.50 -> matches` | `d` |
| 45 | 55.8% | `reports/stage10_confidence.csv` | `predictor=final model; subset=top probability > 0.50 -> accuracy` | `.1%` |
| 46 | 199 | `reports/stage10_confidence.csv` | `predictor=final model; subset=top probability > 0.50 -> matches` | `d` |
| 47 | 55.9% | `reports/stage10_confidence.csv` | `predictor=bookmaker; subset=top probability > 0.50 -> accuracy` | `.1%` |
| 48 | 195 | `reports/stage10_confidence.csv` | `predictor=bookmaker; subset=top probability > 0.50 -> matches` | `d` |
| 49 | 0.55 | `reports/stage9_confidence.csv` | `predictor=final model; subset=top probability > 0.55 -> subset` | `text` |
| 50 | 67.5% | `reports/stage9_confidence.csv` | `predictor=final model; subset=top probability > 0.55 -> accuracy` | `.1%` |
| 51 | 1466 | `reports/stage9_confidence.csv` | `predictor=final model; subset=top probability > 0.55 -> matches` | `d` |
| 52 | 69.7% | `reports/stage9_confidence.csv` | `predictor=bookmaker; subset=top probability > 0.55 -> accuracy` | `.1%` |
| 53 | 1527 | `reports/stage9_confidence.csv` | `predictor=bookmaker; subset=top probability > 0.55 -> matches` | `d` |
| 54 | 58.3% | `reports/stage10_confidence.csv` | `predictor=final model; subset=top probability > 0.55 -> accuracy` | `.1%` |
| 55 | 139 | `reports/stage10_confidence.csv` | `predictor=final model; subset=top probability > 0.55 -> matches` | `d` |
| 56 | 61.4% | `reports/stage10_confidence.csv` | `predictor=bookmaker; subset=top probability > 0.55 -> accuracy` | `.1%` |
| 57 | 140 | `reports/stage10_confidence.csv` | `predictor=bookmaker; subset=top probability > 0.55 -> matches` | `d` |
| 58 | 0.60 | `reports/stage9_confidence.csv` | `predictor=final model; subset=top probability > 0.60 -> subset` | `text` |
| 59 | 70.9% | `reports/stage9_confidence.csv` | `predictor=final model; subset=top probability > 0.60 -> accuracy` | `.1%` |
| 60 | 1094 | `reports/stage9_confidence.csv` | `predictor=final model; subset=top probability > 0.60 -> matches` | `d` |
| 61 | 73.5% | `reports/stage9_confidence.csv` | `predictor=bookmaker; subset=top probability > 0.60 -> accuracy` | `.1%` |
| 62 | 1144 | `reports/stage9_confidence.csv` | `predictor=bookmaker; subset=top probability > 0.60 -> matches` | `d` |
| 63 | 64.5% | `reports/stage10_confidence.csv` | `predictor=final model; subset=top probability > 0.60 -> accuracy` | `.1%` |
| 64 | 93 | `reports/stage10_confidence.csv` | `predictor=final model; subset=top probability > 0.60 -> matches` | `d` |
| 65 | 68.9% | `reports/stage10_confidence.csv` | `predictor=bookmaker; subset=top probability > 0.60 -> accuracy` | `.1%` |
| 66 | 90 | `reports/stage10_confidence.csv` | `predictor=bookmaker; subset=top probability > 0.60 -> matches` | `d` |
| 67 | 0.65 | `reports/stage9_confidence.csv` | `predictor=final model; subset=top probability > 0.65 -> subset` | `text` |
| 68 | 73.9% | `reports/stage9_confidence.csv` | `predictor=final model; subset=top probability > 0.65 -> accuracy` | `.1%` |
| 69 | 793 | `reports/stage9_confidence.csv` | `predictor=final model; subset=top probability > 0.65 -> matches` | `d` |
| 70 | 75.3% | `reports/stage9_confidence.csv` | `predictor=bookmaker; subset=top probability > 0.65 -> accuracy` | `.1%` |
| 71 | 878 | `reports/stage9_confidence.csv` | `predictor=bookmaker; subset=top probability > 0.65 -> matches` | `d` |
| 72 | 68.4% | `reports/stage10_confidence.csv` | `predictor=final model; subset=top probability > 0.65 -> accuracy` | `.1%` |
| 73 | 57 | `reports/stage10_confidence.csv` | `predictor=final model; subset=top probability > 0.65 -> matches` | `d` |
| 74 | 71.9% | `reports/stage10_confidence.csv` | `predictor=bookmaker; subset=top probability > 0.65 -> accuracy` | `.1%` |
| 75 | 57 | `reports/stage10_confidence.csv` | `predictor=bookmaker; subset=top probability > 0.65 -> matches` | `d` |
| 76 | 10% | `reports/stage9_confidence.csv` | `predictor=final model; subset=most confident 10% -> subset` | `text` |
| 77 | 80.4% | `reports/stage9_confidence.csv` | `predictor=final model; subset=most confident 10% -> accuracy` | `.1%` |
| 78 | 342 | `reports/stage9_confidence.csv` | `predictor=final model; subset=most confident 10% -> matches` | `d` |
| 79 | 81.0% | `reports/stage9_confidence.csv` | `predictor=bookmaker; subset=most confident 10% -> accuracy` | `.1%` |
| 80 | 342 | `reports/stage9_confidence.csv` | `predictor=bookmaker; subset=most confident 10% -> matches` | `d` |
| 81 | 68.4% | `reports/stage10_confidence.csv` | `predictor=final model; subset=most confident 10% -> accuracy` | `.1%` |
| 82 | 38 | `reports/stage10_confidence.csv` | `predictor=final model; subset=most confident 10% -> matches` | `d` |
| 83 | 71.1% | `reports/stage10_confidence.csv` | `predictor=bookmaker; subset=most confident 10% -> accuracy` | `.1%` |
| 84 | 38 | `reports/stage10_confidence.csv` | `predictor=bookmaker; subset=most confident 10% -> matches` | `d` |
| 85 | 20% | `reports/stage9_confidence.csv` | `predictor=final model; subset=most confident 20% -> subset` | `text` |
| 86 | 73.7% | `reports/stage9_confidence.csv` | `predictor=final model; subset=most confident 20% -> accuracy` | `.1%` |
| 87 | 684 | `reports/stage9_confidence.csv` | `predictor=final model; subset=most confident 20% -> matches` | `d` |
| 88 | 76.2% | `reports/stage9_confidence.csv` | `predictor=bookmaker; subset=most confident 20% -> accuracy` | `.1%` |
| 89 | 684 | `reports/stage9_confidence.csv` | `predictor=bookmaker; subset=most confident 20% -> matches` | `d` |
| 90 | 67.1% | `reports/stage10_confidence.csv` | `predictor=final model; subset=most confident 20% -> accuracy` | `.1%` |
| 91 | 76 | `reports/stage10_confidence.csv` | `predictor=final model; subset=most confident 20% -> matches` | `d` |
| 92 | 67.1% | `reports/stage10_confidence.csv` | `predictor=bookmaker; subset=most confident 20% -> accuracy` | `.1%` |
| 93 | 76 | `reports/stage10_confidence.csv` | `predictor=bookmaker; subset=most confident 20% -> matches` | `d` |
| 94 | 30% | `reports/stage9_confidence.csv` | `predictor=final model; subset=most confident 30% -> subset` | `text` |
| 95 | 71.8% | `reports/stage9_confidence.csv` | `predictor=final model; subset=most confident 30% -> accuracy` | `.1%` |
| 96 | 1026 | `reports/stage9_confidence.csv` | `predictor=final model; subset=most confident 30% -> matches` | `d` |
| 97 | 75.2% | `reports/stage9_confidence.csv` | `predictor=bookmaker; subset=most confident 30% -> accuracy` | `.1%` |
| 98 | 1026 | `reports/stage9_confidence.csv` | `predictor=bookmaker; subset=most confident 30% -> matches` | `d` |
| 99 | 63.2% | `reports/stage10_confidence.csv` | `predictor=final model; subset=most confident 30% -> accuracy` | `.1%` |
| 100 | 114 | `reports/stage10_confidence.csv` | `predictor=final model; subset=most confident 30% -> matches` | `d` |
| 101 | 65.8% | `reports/stage10_confidence.csv` | `predictor=bookmaker; subset=most confident 30% -> accuracy` | `.1%` |
| 102 | 114 | `reports/stage10_confidence.csv` | `predictor=bookmaker; subset=most confident 30% -> matches` | `d` |
| 103 | 50 | `reports/planted_leaks.csv` | `stage=4 features; check=real code: rebuilt from earlier rows, own stats scrambled -> cases_checked` | `d` |
| 104 | 0 | `reports/planted_leaks.csv` | `stage=4 features; check=real code: rebuilt from earlier rows, own stats scrambled -> flagged` | `d` |
| 105 | 10 | `reports/planted_leaks.csv` | `stage=4 features; check=real code (planted-leak sample) -> cases_checked` | `d` |
| 106 | 0 | `reports/planted_leaks.csv` | `stage=4 features; check=real code (planted-leak sample) -> flagged` | `d` |
| 107 | 33 | `reports/planted_leaks.csv` | `stage=4 features; check=real code (planted-leak sample): last match before a missed season -> cases_checked` | `d` |
| 108 | 0 | `reports/planted_leaks.csv` | `stage=4 features; check=real code (planted-leak sample): last match before a missed season -> flagged` | `d` |
| 109 | 10 | `reports/planted_leaks.csv` | `stage=4 features; check=rolling window without shift(1) -> cases_checked` | `d` |
| 110 | 10 | `reports/planted_leaks.csv` | `stage=4 features; check=rolling window without shift(1) -> flagged` | `d` |
| 111 | 10 | `reports/planted_leaks.csv` | `stage=4 features; check=days rest measured to the next match -> cases_checked` | `d` |
| 112 | 10 | `reports/planted_leaks.csv` | `stage=4 features; check=days rest measured to the next match -> flagged` | `d` |
| 113 | 10 | `reports/planted_leaks.csv` | `stage=4 features; check=season PPG includes this match -> cases_checked` | `d` |
| 114 | 8 | `reports/planted_leaks.csv` | `stage=4 features; check=season PPG includes this match -> flagged` | `d` |
| 115 | 10 | `reports/planted_leaks.csv` | `stage=4 features; check=Elo stores post-update ratings -> cases_checked` | `d` |
| 116 | 10 | `reports/planted_leaks.csv` | `stage=4 features; check=Elo stores post-update ratings -> flagged` | `d` |
| 117 | 10 | `reports/planted_leaks.csv` | `stage=4 features; check=spell break read from the next match -> cases_checked` | `d` |
| 118 | 0 | `reports/planted_leaks.csv` | `stage=4 features; check=spell break read from the next match -> flagged` | `d` |
| 119 | 33 | `reports/planted_leaks.csv` | `stage=4 features; check=spell break read from the next match: last match before a missed season -> cases_checked` | `d` |
| 120 | 33 | `reports/planted_leaks.csv` | `stage=4 features; check=spell break read from the next match: last match before a missed season -> flagged` | `d` |
| 121 | 50 | `reports/planted_leaks.csv` | `stage=7 availability; check=real code: rebuilt from earlier rows, own rows scrambled -> cases_checked` | `d` |
| 122 | 0 | `reports/planted_leaks.csv` | `stage=7 availability; check=real code: rebuilt from earlier rows, own rows scrambled -> flagged` | `d` |
| 123 | 10 | `reports/planted_leaks.csv` | `stage=7 availability; check=real code (planted-leak sample) -> cases_checked` | `d` |
| 124 | 0 | `reports/planted_leaks.csv` | `stage=7 availability; check=real code (planted-leak sample) -> flagged` | `d` |
| 125 | 10 | `reports/planted_leaks.csv` | `stage=7 availability; check=key players include the match's own minutes -> cases_checked` | `d` |
| 126 | 10 | `reports/planted_leaks.csv` | `stage=7 availability; check=key players include the match's own minutes -> flagged` | `d` |
| 127 | 10 | `reports/planted_leaks.csv` | `stage=7 availability; check=price snapshot dated after the match -> cases_checked` | `d` |
| 128 | 10 | `reports/planted_leaks.csv` | `stage=7 availability; check=price snapshot dated after the match -> flagged` | `d` |
| 129 | 1 | `reports/planted_leaks.csv` | `stage=7 availability; check=real rule: injury spell started before the match date (synthetic) -> cases_checked` | `d` |
| 130 | 0 | `reports/planted_leaks.csv` | `stage=7 availability; check=real rule: injury spell started before the match date (synthetic) -> flagged` | `d` |
| 131 | 1 | `reports/planted_leaks.csv` | `stage=7 availability; check=injury spell starting on the match date counted (synthetic) -> cases_checked` | `d` |
| 132 | 1 | `reports/planted_leaks.csv` | `stage=7 availability; check=injury spell starting on the match date counted (synthetic) -> flagged` | `d` |
| 133 | 50 | `reports/planted_leaks.csv` | `stage=8 features; check=real code: rebuilt from earlier rows, own rows scrambled -> cases_checked` | `d` |
| 134 | 0 | `reports/planted_leaks.csv` | `stage=8 features; check=real code: rebuilt from earlier rows, own rows scrambled -> flagged` | `d` |
| 135 | 10 | `reports/planted_leaks.csv` | `stage=8 features; check=real code (planted-leak sample) -> cases_checked` | `d` |
| 136 | 0 | `reports/planted_leaks.csv` | `stage=8 features; check=real code (planted-leak sample) -> flagged` | `d` |
| 137 | 10 | `reports/planted_leaks.csv` | `stage=8 features; check=recent_absence from match t's own minutes -> cases_checked` | `d` |
| 138 | 10 | `reports/planted_leaks.csv` | `stage=8 features; check=recent_absence from match t's own minutes -> flagged` | `d` |
| 139 | 10 | `reports/planted_leaks.csv` | `stage=8 features; check=squad value from a snapshot dated after the match -> cases_checked` | `d` |
| 140 | 10 | `reports/planted_leaks.csv` | `stage=8 features; check=squad value from a snapshot dated after the match -> flagged` | `d` |
| 141 | 61.1% | `reports/model_metrics.csv` | `predictor=bookmaker; season=2016-17 -> accuracy` | `.1%` |
| 142 | 380 | `reports/model_metrics.csv` | `predictor=bookmaker; season=2016-17 -> matches` | `d` |
| 143 | 58.7% | `reports/model_metrics.csv` | `predictor=bookmaker; season=2018-19 -> accuracy` | `.1%` |
| 144 | 380 | `reports/model_metrics.csv` | `predictor=bookmaker; season=2018-19 -> matches` | `d` |
| 145 | 58.2% | `reports/model_metrics.csv` | `predictor=bookmaker; season=2021-22 -> accuracy` | `.1%` |
| 146 | 380 | `reports/model_metrics.csv` | `predictor=bookmaker; season=2021-22 -> matches` | `d` |
| 147 | 59.7% | `reports/model_metrics.csv` | `predictor=bookmaker; season=2023-24 -> accuracy` | `.1%` |
| 148 | 380 | `reports/model_metrics.csv` | `predictor=bookmaker; season=2023-24 -> matches` | `d` |
| 149 | 55.5% | `reports/model_metrics.csv` | `predictor=bookmaker; season=average -> accuracy` | `.1%` |
| 150 | 3800 | `reports/model_metrics.csv` | `predictor=bookmaker; season=average -> matches` | `d` |
| 151 | 0.9807 | `reports/stage6_vs_original.csv` | `model=logistic (all), stage 5 -> reporting_log_loss` | `.4f` |
| 152 | -0.0016 | `reports/stage6_vs_original.csv` | `model=logistic (all), stage 5 -> minus_original` | `+.4f` |
| 153 | 0.0037 | `reports/stage6_vs_original.csv` | `model=logistic (all), stage 5 -> standard_error` | `.4f` |
| 154 | 0.9830 | `reports/stage6_vs_original.csv` | `model=xgboost (all), stage 5 -> reporting_log_loss` | `.4f` |
| 155 | +0.0008 | `reports/stage6_vs_original.csv` | `model=xgboost (all), stage 5 -> minus_original` | `+.4f` |
| 156 | 0.0036 | `reports/stage6_vs_original.csv` | `model=xgboost (all), stage 5 -> standard_error` | `.4f` |
| 157 | 0.9814 | `reports/stage6_vs_original.csv` | `model=elo only, tuned Elo (K=15, home_adv=50, carryover=0.9) -> reporting_log_loss` | `.4f` |
| 158 | -0.0008 | `reports/stage6_vs_original.csv` | `model=elo only, tuned Elo (K=15, home_adv=50, carryover=0.9) -> minus_original` | `+.4f` |
| 159 | 0.0014 | `reports/stage6_vs_original.csv` | `model=elo only, tuned Elo (K=15, home_adv=50, carryover=0.9) -> standard_error` | `.4f` |
| 160 | 0.9818 | `reports/stage6_vs_original.csv` | `model=compact logistic (C=0.03) -> reporting_log_loss` | `.4f` |
| 161 | -0.0005 | `reports/stage6_vs_original.csv` | `model=compact logistic (C=0.03) -> minus_original` | `+.4f` |
| 162 | 0.0018 | `reports/stage6_vs_original.csv` | `model=compact logistic (C=0.03) -> standard_error` | `.4f` |
| 163 | 0.9874 | `reports/stage6_vs_original.csv` | `model=compact xgboost (depth 2, mcw 20, lr 0.03) -> reporting_log_loss` | `.4f` |
| 164 | +0.0051 | `reports/stage6_vs_original.csv` | `model=compact xgboost (depth 2, mcw 20, lr 0.03) -> minus_original` | `+.4f` |
| 165 | 0.0027 | `reports/stage6_vs_original.csv` | `model=compact xgboost (depth 2, mcw 20, lr 0.03) -> standard_error` | `.4f` |
| 166 | 1 | `reports/stage8_decisions.csv` | `step=1 -> step` | `d` |
| 167 | 0.1 | `reports/stage8_decisions.csv` | `step=1 -> lambda` | `g` |
| 168 | +0.0021 | `reports/stage8_differences.csv` | `window=tuning; season=pooled; step=1 -> minus_base` | `+.4f` |
| 169 | 0.0014 | `reports/stage8_differences.csv` | `window=tuning; season=pooled; step=1 -> standard_error` | `.4f` |
| 170 | +0.0006 | `reports/stage8_differences.csv` | `window=reporting; season=pooled; step=1 -> minus_base` | `+.4f` |
| 171 | 0.0004 | `reports/stage8_differences.csv` | `window=reporting; season=pooled; step=1 -> standard_error` | `.4f` |
| 172 | 0 of 5 | `reports/stage8_decisions.csv` | `step=1 -> reporting_seasons_won` | `str` |
| 173 | 2 | `reports/stage8_decisions.csv` | `step=2 -> step` | `d` |
| 174 | 0.1 | `reports/stage8_decisions.csv` | `step=2 -> lambda` | `g` |
| 175 | +0.0025 | `reports/stage8_differences.csv` | `window=tuning; season=pooled; step=2 -> minus_base` | `+.4f` |
| 176 | 0.0032 | `reports/stage8_differences.csv` | `window=tuning; season=pooled; step=2 -> standard_error` | `.4f` |
| 177 | +0.0003 | `reports/stage8_differences.csv` | `window=reporting; season=pooled; step=2 -> minus_base` | `+.4f` |
| 178 | 0.0011 | `reports/stage8_differences.csv` | `window=reporting; season=pooled; step=2 -> standard_error` | `.4f` |
| 179 | 3 of 5 | `reports/stage8_decisions.csv` | `step=2 -> reporting_seasons_won` | `str` |
| 180 | 3 | `reports/stage8_decisions.csv` | `step=3 -> step` | `d` |
| 181 | 0.1 | `reports/stage8_decisions.csv` | `step=3 -> lambda` | `g` |
| 182 | +0.0021 | `reports/stage8_differences.csv` | `window=tuning; season=pooled; step=3 -> minus_base` | `+.4f` |
| 183 | 0.0037 | `reports/stage8_differences.csv` | `window=tuning; season=pooled; step=3 -> standard_error` | `.4f` |
| 184 | +0.0009 | `reports/stage8_differences.csv` | `window=reporting; season=pooled; step=3 -> minus_base` | `+.4f` |
| 185 | 0.0013 | `reports/stage8_differences.csv` | `window=reporting; season=pooled; step=3 -> standard_error` | `.4f` |
| 186 | 2 of 5 | `reports/stage8_decisions.csv` | `step=3 -> reporting_seasons_won` | `str` |
| 187 | 4 | `reports/stage8_decisions.csv` | `step=4 -> step` | `d` |
| 188 | 0.1 | `reports/stage8_decisions.csv` | `step=4 -> lambda` | `g` |
| 189 | +0.0020 | `reports/stage8_differences.csv` | `window=tuning; season=pooled; step=4 -> minus_base` | `+.4f` |
| 190 | 0.0037 | `reports/stage8_differences.csv` | `window=tuning; season=pooled; step=4 -> standard_error` | `.4f` |
| 191 | +0.0006 | `reports/stage8_differences.csv` | `window=reporting; season=pooled; step=4 -> minus_base` | `+.4f` |
| 192 | 0.0014 | `reports/stage8_differences.csv` | `window=reporting; season=pooled; step=4 -> standard_error` | `.4f` |
| 193 | 4 of 5 | `reports/stage8_decisions.csv` | `step=4 -> reporting_seasons_won` | `str` |
| 194 | 9 | `reports/forward_provenance.json` | `key first_batch_predictions` | `d` |
| 195 | 2026-10-24 00:53:30Z | `reports/forward_provenance.json` | `key first_logged_at_utc` | `time:%Y-%m-%d %H:%M:%SZ` |
| 196 | 84320e1 | `reports/forward_provenance.json` | `key code_commit` | `str` |
| 197 | 01:01:52Z | `reports/forward_provenance.json` | `key code_committed_at_utc` | `time:%H:%M:%SZ` |
| 198 | 11:30Z | `reports/forward_provenance.json` | `key first_kickoff_utc` | `time:%H:%MZ` |
| 199 | 9 | `reports/forward_provenance.json` | `key recompute_fixtures` | `d` |
| 200 | 0.0 | `reports/forward_provenance.json` | `key recompute_max_abs_difference` | `.1f` |
| 201 | 0 | `reports/forward_score.csv` | `* -> count()` | `d` |
| 202 | 2016-17 | `reports/stage8_squad_listing.csv` | `* -> min(season)` | `str` |
| 203 | 2024-25 | `reports/stage8_squad_listing.csv` | `* -> max(season)` | `str` |
| 204 | 11.1 | `CLAUDE.md` | `contains clause 11.1` | `text` |
| 205 | 15 | `config/final_model.json` | `key elo.K` | `d` |
| 206 | 50 | `config/final_model.json` | `key elo.home_adv` | `d` |
| 207 | 0.9 | `config/final_model.json` | `key elo.carryover` | `.1f` |
| 208 | 1500 | `config/final_model.json` | `key elo.start` | `d` |
| 209 | 1450 | `config/final_model.json` | `key elo.promoted_start` | `d` |
| 210 | 0.03 | `config/final_model.json` | `key model.C` | `g` |
| 211 | 2026 | `config/final_model.json` | `key random_seeds.leakage_test_sample` | `d` |
| 212 | 58% | `CLAUDE.md` | `contains above 58%` | `text` |
| 213 | 58% | `CLAUDE.md` | `contains exceeds 58%` | `text` |
| 214 | 1.0986 | `reports/model_metrics.csv` | `predictor=uniform; season=2015-16 -> log_loss` | `.4f` |
| 215 | 1.0898 | `reports/model_metrics.csv` | `predictor=base rate; season=2015-16 -> log_loss` | `.4f` |
| 216 | 1.0347 | `reports/model_metrics.csv` | `predictor=elo only; season=2015-16 -> log_loss` | `.4f` |
| 217 | 1.0522 | `reports/model_metrics.csv` | `predictor=logistic (all); season=2015-16 -> log_loss` | `.4f` |
| 218 | 1.0395 | `reports/model_metrics.csv` | `predictor=xgboost; season=2015-16 -> log_loss` | `.4f` |
| 219 | 1.0376 | `reports/stage6_per_season.csv` | `predictor=compact logistic (C=0.03); season=2015-16 -> log_loss` | `.4f` |
| 220 | 1.0352 | `reports/model_metrics.csv` | `predictor=bookmaker; season=2015-16 -> log_loss` | `.4f` |
| 221 | 1.0986 | `reports/model_metrics.csv` | `predictor=uniform; season=2016-17 -> log_loss` | `.4f` |
| 222 | 1.0447 | `reports/model_metrics.csv` | `predictor=base rate; season=2016-17 -> log_loss` | `.4f` |
| 223 | 0.9358 | `reports/model_metrics.csv` | `predictor=elo only; season=2016-17 -> log_loss` | `.4f` |
| 224 | 0.9339 | `reports/model_metrics.csv` | `predictor=logistic (all); season=2016-17 -> log_loss` | `.4f` |
| 225 | 0.9269 | `reports/model_metrics.csv` | `predictor=xgboost; season=2016-17 -> log_loss` | `.4f` |
| 226 | 0.9289 | `reports/stage6_per_season.csv` | `predictor=compact logistic (C=0.03); season=2016-17 -> log_loss` | `.4f` |
| 227 | 0.9065 | `reports/model_metrics.csv` | `predictor=bookmaker; season=2016-17 -> log_loss` | `.4f` |
| 228 | 1.0986 | `reports/model_metrics.csv` | `predictor=uniform; season=2017-18 -> log_loss` | `.4f` |
| 229 | 1.0663 | `reports/model_metrics.csv` | `predictor=base rate; season=2017-18 -> log_loss` | `.4f` |
| 230 | 0.9612 | `reports/model_metrics.csv` | `predictor=elo only; season=2017-18 -> log_loss` | `.4f` |
| 231 | 0.9757 | `reports/model_metrics.csv` | `predictor=logistic (all); season=2017-18 -> log_loss` | `.4f` |
| 232 | 0.9650 | `reports/model_metrics.csv` | `predictor=xgboost; season=2017-18 -> log_loss` | `.4f` |
| 233 | 0.9631 | `reports/stage6_per_season.csv` | `predictor=compact logistic (C=0.03); season=2017-18 -> log_loss` | `.4f` |
| 234 | 0.9455 | `reports/model_metrics.csv` | `predictor=bookmaker; season=2017-18 -> log_loss` | `.4f` |
| 235 | 1.0986 | `reports/model_metrics.csv` | `predictor=uniform; season=2018-19 -> log_loss` | `.4f` |
| 236 | 1.0485 | `reports/model_metrics.csv` | `predictor=base rate; season=2018-19 -> log_loss` | `.4f` |
| 237 | 0.9153 | `reports/model_metrics.csv` | `predictor=elo only; season=2018-19 -> log_loss` | `.4f` |
| 238 | 0.9092 | `reports/model_metrics.csv` | `predictor=logistic (all); season=2018-19 -> log_loss` | `.4f` |
| 239 | 0.9171 | `reports/model_metrics.csv` | `predictor=xgboost; season=2018-19 -> log_loss` | `.4f` |
| 240 | 0.9080 | `reports/stage6_per_season.csv` | `predictor=compact logistic (C=0.03); season=2018-19 -> log_loss` | `.4f` |
| 241 | 0.8929 | `reports/model_metrics.csv` | `predictor=bookmaker; season=2018-19 -> log_loss` | `.4f` |
| 242 | 1.0986 | `reports/model_metrics.csv` | `predictor=uniform; season=2019-20 -> log_loss` | `.4f` |
| 243 | 1.0653 | `reports/model_metrics.csv` | `predictor=base rate; season=2019-20 -> log_loss` | `.4f` |
| 244 | 0.9804 | `reports/model_metrics.csv` | `predictor=elo only; season=2019-20 -> log_loss` | `.4f` |
| 245 | 0.9863 | `reports/model_metrics.csv` | `predictor=logistic (all); season=2019-20 -> log_loss` | `.4f` |
| 246 | 0.9828 | `reports/model_metrics.csv` | `predictor=xgboost; season=2019-20 -> log_loss` | `.4f` |
| 247 | 0.9776 | `reports/stage6_per_season.csv` | `predictor=compact logistic (C=0.03); season=2019-20 -> log_loss` | `.4f` |
| 248 | 0.9732 | `reports/model_metrics.csv` | `predictor=bookmaker; season=2019-20 -> log_loss` | `.4f` |
| 249 | 1.0986 | `reports/model_metrics.csv` | `predictor=uniform; season=2020-21 -> log_loss` | `.4f` |
| 250 | 1.0967 | `reports/model_metrics.csv` | `predictor=base rate; season=2020-21 -> log_loss` | `.4f` |
| 251 | 1.0491 | `reports/model_metrics.csv` | `predictor=elo only; season=2020-21 -> log_loss` | `.4f` |
| 252 | 1.0499 | `reports/model_metrics.csv` | `predictor=logistic (all); season=2020-21 -> log_loss` | `.4f` |
| 253 | 1.0309 | `reports/model_metrics.csv` | `predictor=xgboost; season=2020-21 -> log_loss` | `.4f` |
| 254 | 1.0478 | `reports/stage6_per_season.csv` | `predictor=compact logistic (C=0.03); season=2020-21 -> log_loss` | `.4f` |
| 255 | 1.0070 | `reports/model_metrics.csv` | `predictor=bookmaker; season=2020-21 -> log_loss` | `.4f` |
| 256 | 1.0986 | `reports/model_metrics.csv` | `predictor=uniform; season=2021-22 -> log_loss` | `.4f` |
| 257 | 1.0731 | `reports/model_metrics.csv` | `predictor=base rate; season=2021-22 -> log_loss` | `.4f` |
| 258 | 0.9647 | `reports/model_metrics.csv` | `predictor=elo only; season=2021-22 -> log_loss` | `.4f` |
| 259 | 0.9521 | `reports/model_metrics.csv` | `predictor=logistic (all); season=2021-22 -> log_loss` | `.4f` |
| 260 | 0.9741 | `reports/model_metrics.csv` | `predictor=xgboost; season=2021-22 -> log_loss` | `.4f` |
| 261 | 0.9579 | `reports/stage6_per_season.csv` | `predictor=compact logistic (C=0.03); season=2021-22 -> log_loss` | `.4f` |
| 262 | 0.9372 | `reports/model_metrics.csv` | `predictor=bookmaker; season=2021-22 -> log_loss` | `.4f` |
| 263 | 1.0986 | `reports/model_metrics.csv` | `predictor=uniform; season=2022-23 -> log_loss` | `.4f` |
| 264 | 1.0487 | `reports/model_metrics.csv` | `predictor=base rate; season=2022-23 -> log_loss` | `.4f` |
| 265 | 0.9691 | `reports/model_metrics.csv` | `predictor=elo only; season=2022-23 -> log_loss` | `.4f` |
| 266 | 0.9643 | `reports/model_metrics.csv` | `predictor=logistic (all); season=2022-23 -> log_loss` | `.4f` |
| 267 | 0.9727 | `reports/model_metrics.csv` | `predictor=xgboost; season=2022-23 -> log_loss` | `.4f` |
| 268 | 0.9754 | `reports/stage6_per_season.csv` | `predictor=compact logistic (C=0.03); season=2022-23 -> log_loss` | `.4f` |
| 269 | 0.9662 | `reports/model_metrics.csv` | `predictor=bookmaker; season=2022-23 -> log_loss` | `.4f` |
| 270 | 1.0986 | `reports/model_metrics.csv` | `predictor=uniform; season=2023-24 -> log_loss` | `.4f` |
| 271 | 1.0561 | `reports/model_metrics.csv` | `predictor=base rate; season=2023-24 -> log_loss` | `.4f` |
| 272 | 0.9349 | `reports/model_metrics.csv` | `predictor=elo only; season=2023-24 -> log_loss` | `.4f` |
| 273 | 0.9368 | `reports/model_metrics.csv` | `predictor=logistic (all); season=2023-24 -> log_loss` | `.4f` |
| 274 | 0.9454 | `reports/model_metrics.csv` | `predictor=xgboost; season=2023-24 -> log_loss` | `.4f` |
| 275 | 0.9295 | `reports/stage6_per_season.csv` | `predictor=compact logistic (C=0.03); season=2023-24 -> log_loss` | `.4f` |
| 276 | 0.9092 | `reports/model_metrics.csv` | `predictor=bookmaker; season=2023-24 -> log_loss` | `.4f` |
| 277 | 1.0986 | `reports/model_metrics.csv` | `predictor=uniform; season=2024-25 -> log_loss` | `.4f` |
| 278 | 1.0840 | `reports/model_metrics.csv` | `predictor=base rate; season=2024-25 -> log_loss` | `.4f` |
| 279 | 0.9935 | `reports/model_metrics.csv` | `predictor=elo only; season=2024-25 -> log_loss` | `.4f` |
| 280 | 1.0002 | `reports/model_metrics.csv` | `predictor=logistic (all); season=2024-25 -> log_loss` | `.4f` |
| 281 | 0.9920 | `reports/model_metrics.csv` | `predictor=xgboost; season=2024-25 -> log_loss` | `.4f` |
| 282 | 0.9984 | `reports/stage6_per_season.csv` | `predictor=compact logistic (C=0.03); season=2024-25 -> log_loss` | `.4f` |
| 283 | 0.9708 | `reports/model_metrics.csv` | `predictor=bookmaker; season=2024-25 -> log_loss` | `.4f` |
| 284 | 1.0986 | `reports/model_metrics.csv` | `predictor=uniform; season=average -> log_loss` | `.4f` |
| 285 | 1.0673 | `reports/model_metrics.csv` | `predictor=base rate; season=average -> log_loss` | `.4f` |
| 286 | 0.9739 | `reports/model_metrics.csv` | `predictor=elo only; season=average -> log_loss` | `.4f` |
| 287 | 0.9761 | `reports/model_metrics.csv` | `predictor=logistic (all); season=average -> log_loss` | `.4f` |
| 288 | 0.9746 | `reports/model_metrics.csv` | `predictor=xgboost; season=average -> log_loss` | `.4f` |
| 289 | 0.9724 | `reports/stage6_per_season.csv` | `predictor=compact logistic (C=0.03) -> mean(log_loss)` | `.4f` |
| 290 | 0.9544 | `reports/model_metrics.csv` | `predictor=bookmaker; season=average -> log_loss` | `.4f` |
| 291 | 0.2308 | `reports/model_metrics.csv` | `predictor=uniform; season=2015-16 -> rps` | `.4f` |
| 292 | 0.4461 | `reports/model_metrics.csv` | `predictor=always home; season=2015-16 -> rps` | `.4f` |
| 293 | 0.2290 | `reports/model_metrics.csv` | `predictor=base rate; season=2015-16 -> rps` | `.4f` |
| 294 | 0.2102 | `reports/model_metrics.csv` | `predictor=elo only; season=2015-16 -> rps` | `.4f` |
| 295 | 0.2123 | `reports/model_metrics.csv` | `predictor=logistic (all); season=2015-16 -> rps` | `.4f` |
| 296 | 0.2111 | `reports/model_metrics.csv` | `predictor=xgboost; season=2015-16 -> rps` | `.4f` |
| 297 | 0.2113 | `reports/stage6_per_season.csv` | `predictor=compact logistic (C=0.03); season=2015-16 -> rps` | `.4f` |
| 298 | 0.2098 | `reports/model_metrics.csv` | `predictor=bookmaker; season=2015-16 -> rps` | `.4f` |
| 299 | 0.2409 | `reports/model_metrics.csv` | `predictor=uniform; season=2016-17 -> rps` | `.4f` |
| 300 | 0.3974 | `reports/model_metrics.csv` | `predictor=always home; season=2016-17 -> rps` | `.4f` |
| 301 | 0.2278 | `reports/model_metrics.csv` | `predictor=base rate; season=2016-17 -> rps` | `.4f` |
| 302 | 0.1897 | `reports/model_metrics.csv` | `predictor=elo only; season=2016-17 -> rps` | `.4f` |
| 303 | 0.1895 | `reports/model_metrics.csv` | `predictor=logistic (all); season=2016-17 -> rps` | `.4f` |
| 304 | 0.1880 | `reports/model_metrics.csv` | `predictor=xgboost; season=2016-17 -> rps` | `.4f` |
| 305 | 0.1878 | `reports/stage6_per_season.csv` | `predictor=compact logistic (C=0.03); season=2016-17 -> rps` | `.4f` |
| 306 | 0.1810 | `reports/model_metrics.csv` | `predictor=bookmaker; season=2016-17 -> rps` | `.4f` |
| 307 | 0.2344 | `reports/model_metrics.csv` | `predictor=uniform; season=2017-18 -> rps` | `.4f` |
| 308 | 0.4145 | `reports/model_metrics.csv` | `predictor=always home; season=2017-18 -> rps` | `.4f` |
| 309 | 0.2257 | `reports/model_metrics.csv` | `predictor=base rate; season=2017-18 -> rps` | `.4f` |
| 310 | 0.1903 | `reports/model_metrics.csv` | `predictor=elo only; season=2017-18 -> rps` | `.4f` |
| 311 | 0.1913 | `reports/model_metrics.csv` | `predictor=logistic (all); season=2017-18 -> rps` | `.4f` |
| 312 | 0.1909 | `reports/model_metrics.csv` | `predictor=xgboost; season=2017-18 -> rps` | `.4f` |
| 313 | 0.1898 | `reports/stage6_per_season.csv` | `predictor=compact logistic (C=0.03); season=2017-18 -> rps` | `.4f` |
| 314 | 0.1862 | `reports/model_metrics.csv` | `predictor=bookmaker; season=2017-18 -> rps` | `.4f` |
| 315 | 0.2466 | `reports/model_metrics.csv` | `predictor=uniform; season=2018-19 -> rps` | `.4f` |
| 316 | 0.4303 | `reports/model_metrics.csv` | `predictor=always home; season=2018-19 -> rps` | `.4f` |
| 317 | 0.2380 | `reports/model_metrics.csv` | `predictor=base rate; season=2018-19 -> rps` | `.4f` |
| 318 | 0.1916 | `reports/model_metrics.csv` | `predictor=elo only; season=2018-19 -> rps` | `.4f` |
| 319 | 0.1900 | `reports/model_metrics.csv` | `predictor=logistic (all); season=2018-19 -> rps` | `.4f` |
| 320 | 0.1927 | `reports/model_metrics.csv` | `predictor=xgboost; season=2018-19 -> rps` | `.4f` |
| 321 | 0.1894 | `reports/stage6_per_season.csv` | `predictor=compact logistic (C=0.03); season=2018-19 -> rps` | `.4f` |
| 322 | 0.1857 | `reports/model_metrics.csv` | `predictor=bookmaker; season=2018-19 -> rps` | `.4f` |
| 323 | 0.2374 | `reports/model_metrics.csv` | `predictor=uniform; season=2019-20 -> rps` | `.4f` |
| 324 | 0.4263 | `reports/model_metrics.csv` | `predictor=always home; season=2019-20 -> rps` | `.4f` |
| 325 | 0.2301 | `reports/model_metrics.csv` | `predictor=base rate; season=2019-20 -> rps` | `.4f` |
| 326 | 0.2013 | `reports/model_metrics.csv` | `predictor=elo only; season=2019-20 -> rps` | `.4f` |
| 327 | 0.2016 | `reports/model_metrics.csv` | `predictor=logistic (all); season=2019-20 -> rps` | `.4f` |
| 328 | 0.2019 | `reports/model_metrics.csv` | `predictor=xgboost; season=2019-20 -> rps` | `.4f` |
| 329 | 0.2003 | `reports/stage6_per_season.csv` | `predictor=compact logistic (C=0.03); season=2019-20 -> rps` | `.4f` |
| 330 | 0.1988 | `reports/model_metrics.csv` | `predictor=bookmaker; season=2019-20 -> rps` | `.4f` |
| 331 | 0.2414 | `reports/model_metrics.csv` | `predictor=uniform; season=2020-21 -> rps` | `.4f` |
| 332 | 0.5118 | `reports/model_metrics.csv` | `predictor=always home; season=2020-21 -> rps` | `.4f` |
| 333 | 0.2480 | `reports/model_metrics.csv` | `predictor=base rate; season=2020-21 -> rps` | `.4f` |
| 334 | 0.2257 | `reports/model_metrics.csv` | `predictor=elo only; season=2020-21 -> rps` | `.4f` |
| 335 | 0.2253 | `reports/model_metrics.csv` | `predictor=logistic (all); season=2020-21 -> rps` | `.4f` |
| 336 | 0.2219 | `reports/model_metrics.csv` | `predictor=xgboost; season=2020-21 -> rps` | `.4f` |
| 337 | 0.2251 | `reports/stage6_per_season.csv` | `predictor=compact logistic (C=0.03); season=2020-21 -> rps` | `.4f` |
| 338 | 0.2137 | `reports/model_metrics.csv` | `predictor=bookmaker; season=2020-21 -> rps` | `.4f` |
| 339 | 0.2392 | `reports/model_metrics.csv` | `predictor=uniform; season=2021-22 -> rps` | `.4f` |
| 340 | 0.4553 | `reports/model_metrics.csv` | `predictor=always home; season=2021-22 -> rps` | `.4f` |
| 341 | 0.2359 | `reports/model_metrics.csv` | `predictor=base rate; season=2021-22 -> rps` | `.4f` |
| 342 | 0.1981 | `reports/model_metrics.csv` | `predictor=elo only; season=2021-22 -> rps` | `.4f` |
| 343 | 0.1939 | `reports/model_metrics.csv` | `predictor=logistic (all); season=2021-22 -> rps` | `.4f` |
| 344 | 0.2002 | `reports/model_metrics.csv` | `predictor=xgboost; season=2021-22 -> rps` | `.4f` |
| 345 | 0.1961 | `reports/stage6_per_season.csv` | `predictor=compact logistic (C=0.03); season=2021-22 -> rps` | `.4f` |
| 346 | 0.1890 | `reports/model_metrics.csv` | `predictor=bookmaker; season=2021-22 -> rps` | `.4f` |
| 347 | 0.2396 | `reports/model_metrics.csv` | `predictor=uniform; season=2022-23 -> rps` | `.4f` |
| 348 | 0.4013 | `reports/model_metrics.csv` | `predictor=always home; season=2022-23 -> rps` | `.4f` |
| 349 | 0.2276 | `reports/model_metrics.csv` | `predictor=base rate; season=2022-23 -> rps` | `.4f` |
| 350 | 0.1997 | `reports/model_metrics.csv` | `predictor=elo only; season=2022-23 -> rps` | `.4f` |
| 351 | 0.1994 | `reports/model_metrics.csv` | `predictor=logistic (all); season=2022-23 -> rps` | `.4f` |
| 352 | 0.2002 | `reports/model_metrics.csv` | `predictor=xgboost; season=2022-23 -> rps` | `.4f` |
| 353 | 0.2019 | `reports/stage6_per_season.csv` | `predictor=compact logistic (C=0.03); season=2022-23 -> rps` | `.4f` |
| 354 | 0.1990 | `reports/model_metrics.csv` | `predictor=bookmaker; season=2022-23 -> rps` | `.4f` |
| 355 | 0.2418 | `reports/model_metrics.csv` | `predictor=uniform; season=2023-24 -> rps` | `.4f` |
| 356 | 0.4316 | `reports/model_metrics.csv` | `predictor=always home; season=2023-24 -> rps` | `.4f` |
| 357 | 0.2340 | `reports/model_metrics.csv` | `predictor=base rate; season=2023-24 -> rps` | `.4f` |
| 358 | 0.1919 | `reports/model_metrics.csv` | `predictor=elo only; season=2023-24 -> rps` | `.4f` |
| 359 | 0.1900 | `reports/model_metrics.csv` | `predictor=logistic (all); season=2023-24 -> rps` | `.4f` |
| 360 | 0.1941 | `reports/model_metrics.csv` | `predictor=xgboost; season=2023-24 -> rps` | `.4f` |
| 361 | 0.1897 | `reports/stage6_per_season.csv` | `predictor=compact logistic (C=0.03); season=2023-24 -> rps` | `.4f` |
| 362 | 0.1839 | `reports/model_metrics.csv` | `predictor=bookmaker; season=2023-24 -> rps` | `.4f` |
| 363 | 0.2370 | `reports/model_metrics.csv` | `predictor=uniform; season=2024-25 -> rps` | `.4f` |
| 364 | 0.4697 | `reports/model_metrics.csv` | `predictor=always home; season=2024-25 -> rps` | `.4f` |
| 365 | 0.2365 | `reports/model_metrics.csv` | `predictor=base rate; season=2024-25 -> rps` | `.4f` |
| 366 | 0.2048 | `reports/model_metrics.csv` | `predictor=elo only; season=2024-25 -> rps` | `.4f` |
| 367 | 0.2064 | `reports/model_metrics.csv` | `predictor=logistic (all); season=2024-25 -> rps` | `.4f` |
| 368 | 0.2013 | `reports/model_metrics.csv` | `predictor=xgboost; season=2024-25 -> rps` | `.4f` |
| 369 | 0.2065 | `reports/stage6_per_season.csv` | `predictor=compact logistic (C=0.03); season=2024-25 -> rps` | `.4f` |
| 370 | 0.1972 | `reports/model_metrics.csv` | `predictor=bookmaker; season=2024-25 -> rps` | `.4f` |
| 371 | 0.2389 | `reports/model_metrics.csv` | `predictor=uniform; season=average -> rps` | `.4f` |
| 372 | 0.4384 | `reports/model_metrics.csv` | `predictor=always home; season=average -> rps` | `.4f` |
| 373 | 0.2333 | `reports/model_metrics.csv` | `predictor=base rate; season=average -> rps` | `.4f` |
| 374 | 0.2003 | `reports/model_metrics.csv` | `predictor=elo only; season=average -> rps` | `.4f` |
| 375 | 0.2000 | `reports/model_metrics.csv` | `predictor=logistic (all); season=average -> rps` | `.4f` |
| 376 | 0.2002 | `reports/model_metrics.csv` | `predictor=xgboost; season=average -> rps` | `.4f` |
| 377 | 0.1998 | `reports/stage6_per_season.csv` | `predictor=compact logistic (C=0.03) -> mean(rps)` | `.4f` |
| 378 | 0.1944 | `reports/model_metrics.csv` | `predictor=bookmaker; season=average -> rps` | `.4f` |
| 379 | 41.3% | `reports/model_metrics.csv` | `predictor=uniform; season=2015-16 -> accuracy` | `.1%` |
| 380 | 41.3% | `reports/model_metrics.csv` | `predictor=always home; season=2015-16 -> accuracy` | `.1%` |
| 381 | 41.3% | `reports/model_metrics.csv` | `predictor=base rate; season=2015-16 -> accuracy` | `.1%` |
| 382 | 46.8% | `reports/model_metrics.csv` | `predictor=elo only; season=2015-16 -> accuracy` | `.1%` |
| 383 | 47.6% | `reports/model_metrics.csv` | `predictor=logistic (all); season=2015-16 -> accuracy` | `.1%` |
| 384 | 46.6% | `reports/model_metrics.csv` | `predictor=xgboost; season=2015-16 -> accuracy` | `.1%` |
| 385 | 47.4% | `reports/stage6_per_season.csv` | `predictor=compact logistic (C=0.03); season=2015-16 -> accuracy` | `.1%` |
| 386 | 47.4% | `reports/model_metrics.csv` | `predictor=bookmaker; season=2015-16 -> accuracy` | `.1%` |
| 387 | 380 | `reports/model_metrics.csv` | `predictor=bookmaker; season=2015-16 -> matches` | `d` |
| 388 | 49.2% | `reports/model_metrics.csv` | `predictor=uniform; season=2016-17 -> accuracy` | `.1%` |
| 389 | 49.2% | `reports/model_metrics.csv` | `predictor=always home; season=2016-17 -> accuracy` | `.1%` |
| 390 | 49.2% | `reports/model_metrics.csv` | `predictor=base rate; season=2016-17 -> accuracy` | `.1%` |
| 391 | 58.7% | `reports/model_metrics.csv` | `predictor=elo only; season=2016-17 -> accuracy` | `.1%` |
| 392 | 58.2% | `reports/model_metrics.csv` | `predictor=logistic (all); season=2016-17 -> accuracy` | `.1%` |
| 393 | 59.5% | `reports/model_metrics.csv` | `predictor=xgboost; season=2016-17 -> accuracy` | `.1%` |
| 394 | 58.9% | `reports/stage6_per_season.csv` | `predictor=compact logistic (C=0.03); season=2016-17 -> accuracy` | `.1%` |
| 395 | 61.1% | `reports/model_metrics.csv` | `predictor=bookmaker; season=2016-17 -> accuracy` | `.1%` |
| 396 | 380 | `reports/model_metrics.csv` | `predictor=bookmaker; season=2016-17 -> matches` | `d` |
| 397 | 45.5% | `reports/model_metrics.csv` | `predictor=uniform; season=2017-18 -> accuracy` | `.1%` |
| 398 | 45.5% | `reports/model_metrics.csv` | `predictor=always home; season=2017-18 -> accuracy` | `.1%` |
| 399 | 45.5% | `reports/model_metrics.csv` | `predictor=base rate; season=2017-18 -> accuracy` | `.1%` |
| 400 | 55.8% | `reports/model_metrics.csv` | `predictor=elo only; season=2017-18 -> accuracy` | `.1%` |
| 401 | 53.9% | `reports/model_metrics.csv` | `predictor=logistic (all); season=2017-18 -> accuracy` | `.1%` |
| 402 | 54.5% | `reports/model_metrics.csv` | `predictor=xgboost; season=2017-18 -> accuracy` | `.1%` |
| 403 | 56.6% | `reports/stage6_per_season.csv` | `predictor=compact logistic (C=0.03); season=2017-18 -> accuracy` | `.1%` |
| 404 | 55.3% | `reports/model_metrics.csv` | `predictor=bookmaker; season=2017-18 -> accuracy` | `.1%` |
| 405 | 380 | `reports/model_metrics.csv` | `predictor=bookmaker; season=2017-18 -> matches` | `d` |
| 406 | 47.6% | `reports/model_metrics.csv` | `predictor=uniform; season=2018-19 -> accuracy` | `.1%` |
| 407 | 47.6% | `reports/model_metrics.csv` | `predictor=always home; season=2018-19 -> accuracy` | `.1%` |
| 408 | 47.6% | `reports/model_metrics.csv` | `predictor=base rate; season=2018-19 -> accuracy` | `.1%` |
| 409 | 58.7% | `reports/model_metrics.csv` | `predictor=elo only; season=2018-19 -> accuracy` | `.1%` |
| 410 | 58.2% | `reports/model_metrics.csv` | `predictor=logistic (all); season=2018-19 -> accuracy` | `.1%` |
| 411 | 59.2% | `reports/model_metrics.csv` | `predictor=xgboost; season=2018-19 -> accuracy` | `.1%` |
| 412 | 59.2% | `reports/stage6_per_season.csv` | `predictor=compact logistic (C=0.03); season=2018-19 -> accuracy` | `.1%` |
| 413 | 58.7% | `reports/model_metrics.csv` | `predictor=bookmaker; season=2018-19 -> accuracy` | `.1%` |
| 414 | 380 | `reports/model_metrics.csv` | `predictor=bookmaker; season=2018-19 -> matches` | `d` |
| 415 | 45.3% | `reports/model_metrics.csv` | `predictor=uniform; season=2019-20 -> accuracy` | `.1%` |
| 416 | 45.3% | `reports/model_metrics.csv` | `predictor=always home; season=2019-20 -> accuracy` | `.1%` |
| 417 | 45.3% | `reports/model_metrics.csv` | `predictor=base rate; season=2019-20 -> accuracy` | `.1%` |
| 418 | 53.2% | `reports/model_metrics.csv` | `predictor=elo only; season=2019-20 -> accuracy` | `.1%` |
| 419 | 52.4% | `reports/model_metrics.csv` | `predictor=logistic (all); season=2019-20 -> accuracy` | `.1%` |
| 420 | 52.6% | `reports/model_metrics.csv` | `predictor=xgboost; season=2019-20 -> accuracy` | `.1%` |
| 421 | 52.9% | `reports/stage6_per_season.csv` | `predictor=compact logistic (C=0.03); season=2019-20 -> accuracy` | `.1%` |
| 422 | 52.9% | `reports/model_metrics.csv` | `predictor=bookmaker; season=2019-20 -> accuracy` | `.1%` |
| 423 | 380 | `reports/model_metrics.csv` | `predictor=bookmaker; season=2019-20 -> matches` | `d` |
| 424 | 37.9% | `reports/model_metrics.csv` | `predictor=uniform; season=2020-21 -> accuracy` | `.1%` |
| 425 | 37.9% | `reports/model_metrics.csv` | `predictor=always home; season=2020-21 -> accuracy` | `.1%` |
| 426 | 37.9% | `reports/model_metrics.csv` | `predictor=base rate; season=2020-21 -> accuracy` | `.1%` |
| 427 | 49.2% | `reports/model_metrics.csv` | `predictor=elo only; season=2020-21 -> accuracy` | `.1%` |
| 428 | 48.4% | `reports/model_metrics.csv` | `predictor=logistic (all); season=2020-21 -> accuracy` | `.1%` |
| 429 | 48.2% | `reports/model_metrics.csv` | `predictor=xgboost; season=2020-21 -> accuracy` | `.1%` |
| 430 | 49.7% | `reports/stage6_per_season.csv` | `predictor=compact logistic (C=0.03); season=2020-21 -> accuracy` | `.1%` |
| 431 | 51.8% | `reports/model_metrics.csv` | `predictor=bookmaker; season=2020-21 -> accuracy` | `.1%` |
| 432 | 380 | `reports/model_metrics.csv` | `predictor=bookmaker; season=2020-21 -> matches` | `d` |
| 433 | 42.9% | `reports/model_metrics.csv` | `predictor=uniform; season=2021-22 -> accuracy` | `.1%` |
| 434 | 42.9% | `reports/model_metrics.csv` | `predictor=always home; season=2021-22 -> accuracy` | `.1%` |
| 435 | 42.9% | `reports/model_metrics.csv` | `predictor=base rate; season=2021-22 -> accuracy` | `.1%` |
| 436 | 55.0% | `reports/model_metrics.csv` | `predictor=elo only; season=2021-22 -> accuracy` | `.1%` |
| 437 | 56.8% | `reports/model_metrics.csv` | `predictor=logistic (all); season=2021-22 -> accuracy` | `.1%` |
| 438 | 55.5% | `reports/model_metrics.csv` | `predictor=xgboost; season=2021-22 -> accuracy` | `.1%` |
| 439 | 56.6% | `reports/stage6_per_season.csv` | `predictor=compact logistic (C=0.03); season=2021-22 -> accuracy` | `.1%` |
| 440 | 58.2% | `reports/model_metrics.csv` | `predictor=bookmaker; season=2021-22 -> accuracy` | `.1%` |
| 441 | 380 | `reports/model_metrics.csv` | `predictor=bookmaker; season=2021-22 -> matches` | `d` |
| 442 | 48.4% | `reports/model_metrics.csv` | `predictor=uniform; season=2022-23 -> accuracy` | `.1%` |
| 443 | 48.4% | `reports/model_metrics.csv` | `predictor=always home; season=2022-23 -> accuracy` | `.1%` |
| 444 | 48.4% | `reports/model_metrics.csv` | `predictor=base rate; season=2022-23 -> accuracy` | `.1%` |
| 445 | 53.9% | `reports/model_metrics.csv` | `predictor=elo only; season=2022-23 -> accuracy` | `.1%` |
| 446 | 54.2% | `reports/model_metrics.csv` | `predictor=logistic (all); season=2022-23 -> accuracy` | `.1%` |
| 447 | 55.3% | `reports/model_metrics.csv` | `predictor=xgboost; season=2022-23 -> accuracy` | `.1%` |
| 448 | 53.9% | `reports/stage6_per_season.csv` | `predictor=compact logistic (C=0.03); season=2022-23 -> accuracy` | `.1%` |
| 449 | 55.8% | `reports/model_metrics.csv` | `predictor=bookmaker; season=2022-23 -> accuracy` | `.1%` |
| 450 | 380 | `reports/model_metrics.csv` | `predictor=bookmaker; season=2022-23 -> matches` | `d` |
| 451 | 46.1% | `reports/model_metrics.csv` | `predictor=uniform; season=2023-24 -> accuracy` | `.1%` |
| 452 | 46.1% | `reports/model_metrics.csv` | `predictor=always home; season=2023-24 -> accuracy` | `.1%` |
| 453 | 46.1% | `reports/model_metrics.csv` | `predictor=base rate; season=2023-24 -> accuracy` | `.1%` |
| 454 | 57.6% | `reports/model_metrics.csv` | `predictor=elo only; season=2023-24 -> accuracy` | `.1%` |
| 455 | 57.6% | `reports/model_metrics.csv` | `predictor=logistic (all); season=2023-24 -> accuracy` | `.1%` |
| 456 | 57.6% | `reports/model_metrics.csv` | `predictor=xgboost; season=2023-24 -> accuracy` | `.1%` |
| 457 | 57.4% | `reports/stage6_per_season.csv` | `predictor=compact logistic (C=0.03); season=2023-24 -> accuracy` | `.1%` |
| 458 | 59.7% | `reports/model_metrics.csv` | `predictor=bookmaker; season=2023-24 -> accuracy` | `.1%` |
| 459 | 380 | `reports/model_metrics.csv` | `predictor=bookmaker; season=2023-24 -> matches` | `d` |
| 460 | 40.8% | `reports/model_metrics.csv` | `predictor=uniform; season=2024-25 -> accuracy` | `.1%` |
| 461 | 40.8% | `reports/model_metrics.csv` | `predictor=always home; season=2024-25 -> accuracy` | `.1%` |
| 462 | 40.8% | `reports/model_metrics.csv` | `predictor=base rate; season=2024-25 -> accuracy` | `.1%` |
| 463 | 51.6% | `reports/model_metrics.csv` | `predictor=elo only; season=2024-25 -> accuracy` | `.1%` |
| 464 | 52.1% | `reports/model_metrics.csv` | `predictor=logistic (all); season=2024-25 -> accuracy` | `.1%` |
| 465 | 53.4% | `reports/model_metrics.csv` | `predictor=xgboost; season=2024-25 -> accuracy` | `.1%` |
| 466 | 50.5% | `reports/stage6_per_season.csv` | `predictor=compact logistic (C=0.03); season=2024-25 -> accuracy` | `.1%` |
| 467 | 53.9% | `reports/model_metrics.csv` | `predictor=bookmaker; season=2024-25 -> accuracy` | `.1%` |
| 468 | 380 | `reports/model_metrics.csv` | `predictor=bookmaker; season=2024-25 -> matches` | `d` |
| 469 | 44.5% | `reports/model_metrics.csv` | `predictor=uniform; season=average -> accuracy` | `.1%` |
| 470 | 44.5% | `reports/model_metrics.csv` | `predictor=always home; season=average -> accuracy` | `.1%` |
| 471 | 44.5% | `reports/model_metrics.csv` | `predictor=base rate; season=average -> accuracy` | `.1%` |
| 472 | 54.1% | `reports/model_metrics.csv` | `predictor=elo only; season=average -> accuracy` | `.1%` |
| 473 | 53.9% | `reports/model_metrics.csv` | `predictor=logistic (all); season=average -> accuracy` | `.1%` |
| 474 | 54.2% | `reports/model_metrics.csv` | `predictor=xgboost; season=average -> accuracy` | `.1%` |
| 475 | 54.3% | `reports/stage6_per_season.csv` | `predictor=compact logistic (C=0.03) -> mean(accuracy)` | `.1%` |
| 476 | 55.5% | `reports/model_metrics.csv` | `predictor=bookmaker; season=average -> accuracy` | `.1%` |
| 477 | 3800 | `reports/model_metrics.csv` | `predictor=bookmaker; season=average -> matches` | `d` |
| 478 | 100 | `CLAUDE.md` | `contains at least 100 matches` | `text` |
| 479 | 0.9746 | `reports/model_metrics.csv` | `predictor=xgboost; season=average -> log_loss` | `.4f` |
| 480 | 0.9739 | `reports/model_metrics.csv` | `predictor=elo only; season=average -> log_loss` | `.4f` |
| 481 | 0.9823 | `reports/stage6_per_season.csv` | `predictor=elo only (original); season>=2020-21 -> mean(log_loss)` | `.4f` |
| 482 | 0.9444 | `reports/stage9_calibration.csv` | `forecast=raw; window=tuning 2016-17..2019-20 -> log_loss` | `.4f` |
| 483 | 0.9546 | `reports/stage9_calibration.csv` | `forecast=temperature-scaled; window=tuning 2016-17..2019-20 -> log_loss` | `.4f` |
| 484 | 0.9818 | `reports/stage9_calibration.csv` | `forecast=raw; window=reporting 2020-21..2024-25 -> log_loss` | `.4f` |
| 485 | 0.9853 | `reports/stage9_calibration.csv` | `forecast=temperature-scaled; window=reporting 2020-21..2024-25 -> log_loss` | `.4f` |
| 486 | 0 | `reports/stage10_holdout.md` | `md actual \ predicted=H -> D` | `str` |
| 487 | 0 | `reports/stage10_holdout.md` | `md actual \ predicted=D -> D` | `str` |
| 488 | 0 | `reports/stage10_holdout.md` | `md actual \ predicted=A -> D` | `str` |
| 489 | 10 | `reports/stage9_reliability.csv` | `outcome=A -> sum(observed > predicted)` | `d` |
| 490 | 10 | `reports/stage9_reliability.csv` | `outcome=A -> count()` | `d` |
| 491 | 0.6 | `reports/stage9_reliability.csv` | `outcome=A -> min(observed - predicted)` | `x100:.1f` |
| 492 | 5.9 | `reports/stage9_reliability.csv` | `outcome=A -> max(observed - predicted)` | `x100:.1f` |
| 493 | 1450 | `config/final_model.json` | `key elo.promoted_start` | `d` |
| 494 | 380 | `reports/stage10_holdout.csv` | `predictor=final model -> matches` | `d` |
| 495 | 2.6 | `reports/stage10_holdout.csv` | `predictor=final model -> expr(sqrt(accuracy * (1 - accuracy) / matches))` | `x100:.1f` |
| 496 | 1.0271 | `reports/stage10_holdout.csv` | `predictor=final model -> log_loss` | `.4f` |
| 497 | 0.9818 | `reports/stage9_calibration.csv` | `forecast=raw; window=reporting 2020-21..2024-25 -> log_loss` | `.4f` |
| 498 | 1.0185 | `reports/stage10_holdout.csv` | `predictor=bookmaker -> log_loss` | `.4f` |
| 499 | 0.9581 | `reports/stage6_per_season.csv` | `predictor=bookmaker; season>=2020-21 -> mean(log_loss)` | `.4f` |
| 500 | 5.1 | `CLAUDE.md` | `contains PowerShell 5.1` | `text` |
| 501 | 100 | `CLAUDE.md` | `contains below 100 matches` | `text` |

"""Score the forward prediction log against played results and the bookmaker.

For each played current-season match, uses the latest logged prediction made before its
actual kickoff (from the football-data results file), and compares log loss, RPS and accuracy
with the bookmaker's odds in the same file. Offline: reads matches.parquet, the cached results
file and the log. Run `python -m scripts.predict_upcoming` (or build_dataset) first to refresh.
Run from the project root: python -m scripts.score_forward
"""

from src.config import REPORTS_DIR
from src.forward import actual_kickoffs, forward_summary, load_played_matches, read_log, scoreable
from src.seasons import current_season, season_label


def main() -> None:
    start_year = current_season()
    scored = scoreable(read_log(), load_played_matches(), actual_kickoffs(start_year), season_label(start_year))
    table, verdict = forward_summary(scored)
    table.to_csv(REPORTS_DIR / "forward_score.csv", index=False)
    print(table.to_string(index=False, float_format="{:.4f}".format) if not table.empty else "(nothing scored yet)")
    print(f"\n{verdict}")


if __name__ == "__main__":
    main()

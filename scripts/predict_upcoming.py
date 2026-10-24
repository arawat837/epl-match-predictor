"""Predict upcoming Premier League fixtures with the frozen final model and log them.

Refreshes the current-season football-data file (2026-27), rebuilds matches.parquet, reads
upcoming fixtures from football-data.co.uk's fixtures.csv, builds each fixture's features from
played matches only (Stage 4 code), and appends to data/forward/predictions_log.csv.
Fixtures that have kicked off are skipped; a fixture already logged gets a new row only if new
results changed its inputs. Run from the project root: python -m scripts.predict_upcoming
"""

import sys
from datetime import datetime, timezone

import pandas as pd

from src.data import build_matches, download_epl, fetch_csv, save_matches
from src.final_model import elo_params, load_config, predictor
from src.forward import (FIXTURES_URL, append_log, fixture_features, fixture_row, forecast, inputs_hash,
                         parse_fixtures, season_pipeline, training_table)
from src.holdout import config_hash, git_commit, working_tree_clean
from src.quality import failed_checks
from src.seasons import current_season, season_label


def main() -> int:
    now = datetime.now(timezone.utc)
    matches = build_matches(download_epl())  # re-downloads only the current season
    failures = failed_checks(matches, season_label(current_season()))
    if failures:
        print(f"Data-quality checks failed: {failures}; nothing logged.")
        return 1
    save_matches(matches)
    fixtures = parse_fixtures(fetch_csv(FIXTURES_URL))
    print(f"Fixtures source: {FIXTURES_URL} ({len(fixtures)} Premier League fixtures)")
    started = fixtures[fixtures["kickoff"] <= now]
    for _, fixture in started.iterrows():
        print(f"  skipped, kickoff passed: {fixture['home']} v {fixture['away']} ({fixture['kickoff']})")
    upcoming = fixtures[fixtures["kickoff"] > now]
    if upcoming.empty:
        print("No upcoming fixtures to log.")
        return 0

    config = load_config()
    elo, model = elo_params(config), predictor(config)
    table = training_table(matches, elo)
    commit, config_sha = git_commit(), config_hash()
    if not working_tree_clean():
        print("warning: working tree has uncommitted changes; the logged commit may not match the code")
    rows = []
    for _, fixture in upcoming.iterrows():
        row = fixture_row(fixture["home"], fixture["away"], fixture["kickoff"])
        features = fixture_features(matches, row, elo)
        frame = features[model.columns].astype(float).to_frame().T
        pipeline = season_pipeline(table, row["season"].iloc[0], model)
        probabilities = forecast(pipeline, model.columns, frame).iloc[0]
        rows.append({"predicted_at": now.isoformat(timespec="seconds"), "kickoff": fixture["kickoff"].isoformat(),
                     "home": fixture["home"], "away": fixture["away"], "p_home": probabilities["H"],
                     "p_draw": probabilities["D"], "p_away": probabilities["A"],
                     "inputs_hash": inputs_hash(features, model.columns), "git_commit": commit,
                     "config_hash": config_sha})
    predictions = pd.DataFrame(rows)
    appended = append_log(predictions, now)
    print(predictions[["kickoff", "home", "away", "p_home", "p_draw", "p_away"]].to_string(
        index=False, float_format="{:.3f}".format))
    print(f"\nAppended {appended} row(s) to the prediction log ({len(predictions) - appended} unchanged since logged).")
    return 0


if __name__ == "__main__":
    sys.exit(main())

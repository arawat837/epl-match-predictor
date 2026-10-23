"""Build data/processed/features.parquet from the evaluation seasons, then print the
feature summary and the top and bottom 5 Elo ratings after the last match.

Uses load_evaluation_matches, so the locked holdout is never read.
Run from the project root: python -m scripts.build_features
"""

from src.elo import final_ratings
from src.features import build_features, feature_columns, save_features
from src.splits import load_evaluation_matches


def main() -> None:
    matches = load_evaluation_matches()
    features = build_features(matches)
    path = save_features(features)
    columns = feature_columns(features)
    seasons = features["season"]
    print(f"Saved {len(features)} matches x {len(columns)} features ({seasons.min()} to {seasons.max()}) to {path}")
    print(f"Burn-in rows (first season): {int(features['burn_in'].sum())}\n")
    summary = features[columns].describe().T[["count", "mean", "min", "max"]]
    summary.insert(1, "missing", len(features) - summary["count"].astype(int))
    print(summary.drop(columns="count").to_string(float_format="{:.2f}".format))
    ratings = final_ratings(matches)
    print(f"\nElo after the last match of {seasons.max()}")
    print(f"Top 5\n{ratings.head(5).to_string(float_format='{:.1f}'.format)}")
    print(f"Bottom 5\n{ratings.tail(5).to_string(float_format='{:.1f}'.format)}")


if __name__ == "__main__":
    main()

"""Build data/processed/features.parquet from the evaluation seasons and list the features.

Uses load_evaluation_matches, so the locked holdout is never read.
Run from the project root: python -m scripts.build_features
"""

from src.features import build_features, feature_columns, save_features
from src.splits import load_evaluation_matches


def main() -> None:
    features = build_features(load_evaluation_matches())
    path = save_features(features)
    columns = feature_columns(features)
    seasons = features["season"]
    print(f"Saved {len(features)} matches x {len(columns)} features ({seasons.min()} to {seasons.max()}) to {path}\n")
    summary = features[columns].describe().T[["count", "mean", "min", "max"]]
    summary.insert(1, "missing", len(features) - summary["count"].astype(int))
    print(summary.drop(columns="count").to_string(float_format="{:.2f}".format))


if __name__ == "__main__":
    main()

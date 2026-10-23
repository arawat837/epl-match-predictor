"""Score the baselines walk-forward and save reports/baseline_metrics.csv.

Test seasons run from config.FIRST_TEST_SEASON up to, not including, the holdout.
Run from the project root: python -m scripts.evaluate_baselines
Exits with status 1 if the leakage alarm fires.
"""

import sys

from src.baselines import BASELINES
from src.config import REPORTS_DIR
from src.evaluate import format_report, leakage_alarms, walk_forward, with_average
from src.splits import load_evaluation_matches, walk_forward_splits


def main() -> int:
    matches = load_evaluation_matches()
    table = with_average(walk_forward(BASELINES, walk_forward_splits(matches)))
    REPORTS_DIR.mkdir(exist_ok=True)
    path = REPORTS_DIR / "baseline_metrics.csv"
    table.to_csv(path, index=False)
    print(format_report(table))
    print(f"\nSaved {path}")
    return 1 if not leakage_alarms(table).empty else 0


if __name__ == "__main__":
    sys.exit(main())

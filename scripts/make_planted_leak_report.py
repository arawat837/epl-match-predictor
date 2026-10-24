"""Rerun the leakage checks on the real code and on planted leaks; write reports/planted_leaks.csv.

Each planted leak is checked on a random sample and on a sample targeted at the rare case where
it first shows; the real code is checked on the same targeted sample. Exits 1 if the real code is
flagged anywhere. Needs matches, features, the FPL archive and the Stage 7/8 tables.
Run from the project root: python -m scripts.make_planted_leak_report
"""

import sys

from scripts.audit_availability import AVAILABILITY_PATH
from scripts.evaluate_availability import FEATURES_PATH as STAGE8_PATH
from src.config import REPORTS_DIR
from src.leak_report import planted_leak_report, real_code_flags

REPORT_PATH = REPORTS_DIR / "planted_leaks.csv"


def main() -> int:
    report = planted_leak_report(AVAILABILITY_PATH, STAGE8_PATH)
    print(report.to_string(index=False))
    report.to_csv(REPORT_PATH, index=False)
    print(f"\nwritten {REPORT_PATH}")
    flagged = real_code_flags(report)
    if flagged:
        print(f"LEAK: the real code was flagged on {flagged} match(es); audit before going further.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

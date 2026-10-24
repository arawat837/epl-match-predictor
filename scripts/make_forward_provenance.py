"""Rebuild reports/forward_provenance.json from the prediction log, git, and a recompute of the first
logged batch with the code exported by `git archive` (never the working tree).

Exits 1 if the recompute does not reproduce the logged predictions exactly.
Run from the project root: python -m scripts.make_forward_provenance
"""

import sys

from src.config import REPORTS_DIR
from src.provenance import forward_provenance, record_text

REPORT_PATH = REPORTS_DIR / "forward_provenance.json"


def main() -> int:
    record, notes = forward_provenance()
    if not notes["logged_commit_has_forward_code"]:
        print(f"Logged commit {record['logged_git_commit'][:7]} has no forward code; recomputed with "
              f"{record['recompute_code_commit']}, the commit that added it.")
    print(f"Recompute imported {notes['code_path']}")
    print(record_text(record))
    REPORT_PATH.write_text(record_text(record), encoding="utf-8")
    print(f"\nwritten {REPORT_PATH}")
    reproduced = record["recompute_inputs_unchanged"] and record["recompute_max_abs_difference"] == 0.0
    return 0 if reproduced else 1


if __name__ == "__main__":
    sys.exit(main())

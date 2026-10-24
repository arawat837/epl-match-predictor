"""reports/planted_leaks.csv: a small rerun on the real data must agree with the committed report.

Every sample in the report is seeded and a smaller run checks a prefix of each, so the rerun's
counts must lie within what the full counts allow, and the real code must flag nothing.
"""

import pandas as pd
import pytest

from scripts.audit_availability import AVAILABILITY_PATH
from scripts.evaluate_availability import FEATURES_PATH as STAGE8_PATH
from src.config import FEATURES_PATH, MATCHES_PATH, REPORTS_DIR
from src.fpl import FPL_DIR
from src.leak_report import COLUMNS, COUNTS, injury_rule_row, planted_leak_report, real_code_flags

REPORT = REPORTS_DIR / "planted_leaks.csv"
LIMIT = 2
needs_data = pytest.mark.skipif(
    not all(path.exists() for path in (MATCHES_PATH, FEATURES_PATH, AVAILABILITY_PATH, STAGE8_PATH, FPL_DIR, REPORT)),
    reason="needs the match, feature and availability tables, the FPL archive and reports/planted_leaks.csv")


def test_spell_rule_flags_the_planted_same_day_rule_only():
    row = injury_rule_row()
    assert (row["targeted_cases"], row["targeted_flagged"], row["real_code_targeted_flagged"]) == (1, 1, 0)


def test_real_code_flags_count_real_rows_and_real_code_on_targeted_samples():
    report = pd.DataFrame({"check": ["real code: rebuilt", "planted leak", "real code: rebuilt"],
                           "random_flagged": pd.array([1, 9, 0], dtype="Int64"),
                           "targeted_flagged": pd.array([1, 9, None], dtype="Int64"),
                           "real_code_targeted_flagged": pd.array([1, 2, None], dtype="Int64")})
    assert real_code_flags(report) == 4  # 1 + 0 at random, 1 + 2 on targeted samples


def allowed(cases: int, full_cases: int, full_flagged: int) -> range:
    """Flag counts possible on the first `cases` of a sample whose full count was full_flagged/full_cases."""
    return range(max(0, cases - (full_cases - full_flagged)), min(cases, full_flagged) + 1)


@pytest.fixture(scope="module")
def reports() -> tuple[pd.DataFrame, pd.DataFrame]:
    """The committed report and a rerun on the first LIMIT matches of every sample."""
    committed = pd.read_csv(REPORT, dtype={column: "Int64" for column in COUNTS})
    return committed, planted_leak_report(AVAILABILITY_PATH, STAGE8_PATH, limit=LIMIT)


@needs_data
def test_small_rerun_has_the_committed_checks_and_samples(reports):
    committed, small = reports
    assert list(small.columns) == list(committed.columns) == COLUMNS
    labels = ["stage", "check", "targeted_sample"]
    assert small[labels].fillna("").equals(committed[labels].fillna(""))


@needs_data
def test_small_rerun_counts_agree_with_the_committed_counts(reports):
    committed, small = reports
    for kind in ("random", "targeted"):
        for (_, full), (_, rerun) in zip(committed.iterrows(), small.iterrows()):
            if pd.isna(full[f"{kind}_cases"]):
                assert pd.isna(rerun[f"{kind}_cases"])
                continue
            assert rerun[f"{kind}_cases"] == min(LIMIT, full[f"{kind}_cases"])
            assert rerun[f"{kind}_flagged"] in allowed(rerun[f"{kind}_cases"], full[f"{kind}_cases"],
                                                       full[f"{kind}_flagged"]), (full["check"], kind)


@needs_data
def test_real_code_is_flagged_nowhere(reports):
    committed, small = reports
    assert real_code_flags(committed) == 0
    assert real_code_flags(small) == 0

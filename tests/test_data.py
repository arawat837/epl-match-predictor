from datetime import date
from urllib.error import HTTPError

import pandas as pd
import pytest

import src.data as data
from src.data import (
    MATCH_COLUMNS,
    clean_season,
    derive_result,
    download_epl,
    parse_dates,
    raw_path,
    read_raw_season,
    season_url,
    select_odds,
)


def raw_season(**overrides: list[str | None]) -> pd.DataFrame:
    """Two matches in raw football-data.co.uk form (all text)."""
    columns = {
        "Date": ["13/08/05", "14/08/05"],
        "HomeTeam": ["Arsenal", "Man City"],
        "AwayTeam": ["Chelsea", "Man United"],
        "FTHG": ["2", "1"], "FTAG": ["1", "1"], "FTR": ["H", "D"],
        "HS": ["12", "9"], "AS": ["7", "11"], "HST": ["6", "3"], "AST": ["2", "5"],
        "B365H": ["1.80", "2.50"], "B365D": ["3.40", "3.20"], "B365A": ["4.50", "2.80"],
    }
    return pd.DataFrame(columns | overrides)


def test_parse_dates_handles_two_and_four_digit_years_day_first():
    parsed = parse_dates(pd.Series(["13/08/05", "02/01/2016"]))
    assert parsed.tolist() == [pd.Timestamp("2005-08-13"), pd.Timestamp("2016-01-02")]


def test_derive_result_from_goals():
    home = pd.Series([2, 1, 0, None], dtype="Int64")
    away = pd.Series([1, 1, 3, 1], dtype="Int64")
    assert derive_result(home, away).tolist() == ["H", "D", "A", pd.NA]


def test_clean_season_produces_the_match_table():
    matches = clean_season(raw_season(), 2005)
    assert list(matches.columns) == MATCH_COLUMNS
    assert matches["season"].tolist() == ["2005-06", "2005-06"]
    assert matches["home"].tolist() == ["Arsenal", "Manchester City"]
    assert matches["away"].tolist() == ["Chelsea", "Manchester United"]
    assert matches["result"].tolist() == ["H", "D"]
    assert matches["date"].tolist() == [pd.Timestamp("2005-08-13"), pd.Timestamp("2005-08-14")]
    assert matches["HST"].tolist() == [6, 3]


def test_clean_season_raises_when_ftr_disagrees_with_goals():
    with pytest.raises(ValueError, match="FTR disagrees"):
        clean_season(raw_season(FTR=["A", "D"]), 2005)


def test_season_without_a_stat_column_gets_it_as_missing():
    matches = clean_season(raw_season().drop(columns=["HST", "AST"]), 2005)
    assert matches[["HST", "AST"]].isna().all().all()


def test_odds_prefer_bet365():
    raw = raw_season(PSH=["1.90", "2.60"], PSD=["3.50", "3.30"], PSA=["4.60", "2.90"])
    odds = select_odds(raw)
    assert odds["odds_source"].tolist() == ["B365", "B365"]
    assert odds.loc[0, ["odds_home", "odds_draw", "odds_away"]].tolist() == [1.80, 3.40, 4.50]


def test_odds_fall_back_to_one_bookmaker_for_all_three_prices():
    raw = raw_season(
        B365D=[None, "3.20"],
        PSH=["1.90", "2.60"], PSD=["3.50", "3.30"], PSA=["4.60", "2.90"],
    )
    odds = select_odds(raw)
    assert odds["odds_source"].tolist() == ["PS", "B365"]
    assert odds.loc[0, ["odds_home", "odds_draw", "odds_away"]].tolist() == [1.90, 3.50, 4.60]


def test_odds_use_market_average_from_older_column_names():
    raw = raw_season().drop(columns=["B365H", "B365D", "B365A"]).assign(
        BbAvH=["1.85", "2.55"], BbAvD=["3.30", "3.10"], BbAvA=["4.40", "2.75"],
    )
    assert select_odds(raw)["odds_source"].tolist() == ["BbAv", "BbAv"]


def test_odds_missing_from_every_bookmaker_stay_missing():
    raw = raw_season(B365H=[None, "2.50"])
    odds = select_odds(raw)
    assert odds.loc[0, ["odds_home", "odds_draw", "odds_away", "odds_source"]].isna().all()


def test_read_raw_season_strips_bom_and_blank_rows(tmp_path):
    path = tmp_path / "E0_0506.csv"
    path.write_text("﻿Date,HomeTeam,AwayTeam\n13/08/05,Arsenal,Chelsea\n,,\n", encoding="utf-8")
    raw = read_raw_season(path)
    assert list(raw.columns) == ["Date", "HomeTeam", "AwayTeam"]
    assert len(raw) == 1


def test_download_reuses_cache_but_refreshes_current_season(tmp_path, monkeypatch):
    fetched: list[str] = []
    monkeypatch.setattr(data, "fetch_csv", lambda url: fetched.append(url) or b"new")
    raw_path(2005, tmp_path).write_bytes(b"old")
    raw_path(2026, tmp_path).write_bytes(b"old")

    files = download_epl([2005, 2006, 2026], raw_dir=tmp_path, today=date(2026, 10, 24))

    assert fetched == [season_url(2006), season_url(2026)]
    assert files[2005].read_bytes() == b"old"
    assert files[2006].read_bytes() == b"new"
    assert files[2026].read_bytes() == b"new"


def test_download_urls_use_season_codes():
    assert season_url(2025) == "https://www.football-data.co.uk/mmz4281/2526/E0.csv"


def not_found(url: str) -> bytes:
    raise HTTPError(url, 404, "Not Found", hdrs=None, fp=None)


def test_current_season_without_a_file_yet_is_skipped(tmp_path, monkeypatch):
    monkeypatch.setattr(data, "fetch_csv", not_found)
    assert download_epl([2026], raw_dir=tmp_path, today=date(2026, 8, 2)) == {}


def test_missing_past_season_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(data, "fetch_csv", not_found)
    with pytest.raises(HTTPError):
        download_epl([2010], raw_dir=tmp_path, today=date(2026, 10, 24))

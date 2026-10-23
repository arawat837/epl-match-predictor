import pytest

from src.fpl import download_fpl, fetch_once, fixture_sides, read_gameweeks

GAMEWEEK_CSV = """name,element,fixture,kickoff_time,round,was_home,opponent_team,minutes,yellow_cards,red_cards,bps,ict_index,value,xP
a,1,10,2016-08-13T14:00:00Z,1,True,2,90,0,0,20,5.0,55,3.1
b,2,10,2016-08-13T14:00:00Z,1,False,1,90,1,0,10,2.0,45,2.2
c,3,10,2016-08-13T14:00:00Z,1,True,2,0,0,0,0,0.0,40,0.0
"""


def test_gameweeks_never_read_xp_and_parse_was_home(tmp_path):
    path = tmp_path / "merged_gw.csv"
    path.write_text(GAMEWEEK_CSV, encoding="utf-8")
    rows = read_gameweeks(path)
    assert "xP" not in rows.columns
    assert rows["was_home"].tolist() == [True, False, True]


def test_fixture_sides_come_from_the_opponents_of_each_side(tmp_path):
    path = tmp_path / "merged_gw.csv"
    path.write_text(GAMEWEEK_CSV, encoding="utf-8")
    sides = fixture_sides(read_gameweeks(path)).set_index("fixture")
    assert sides.loc[10, ["home_id", "away_id"]].tolist() == [1, 2]


def test_holdout_seasons_are_never_downloaded(tmp_path):
    with pytest.raises(ValueError, match="off limits"):
        download_fpl(["2024-25", "2025-26"], fpl_dir=tmp_path)


def test_each_file_is_fetched_once_including_a_404(tmp_path, monkeypatch):
    calls: list[str] = []

    def fake_fetch(url: str) -> bytes:
        calls.append(url)
        if "missing" in url:
            from urllib.error import HTTPError
            raise HTTPError(url, 404, "Not Found", hdrs=None, fp=None)
        return b"x"

    monkeypatch.setattr("src.fpl.fetch_csv", fake_fetch)
    for _ in range(2):
        assert fetch_once("2016-17/players_raw.csv", tmp_path) is not None
        assert fetch_once("2016-17/missing.csv", tmp_path) is None
    assert len(calls) == 2

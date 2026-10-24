"""API-Football client: no network in tests (a fake opener stands in), the key never leaves memory,
refused requests are not cached, and coverage flags are read per season."""

import io
import json
from pathlib import Path

import pandas as pd
import pytest

from src.api_football import (ApiFootballError, api_key, cache_path, fetch, fetch_missing, season_coverage,
                              seasons_without_lineups)
from src.config import PROJECT_ROOT

KEY = "test-key-not-real"


class FakeOpener:
    """Records requests and answers with a fixed JSON payload."""

    def __init__(self, payload: dict) -> None:
        self.payload, self.requests = payload, []

    def __call__(self, request, timeout: float) -> io.BytesIO:
        self.requests.append(request)
        return io.BytesIO(json.dumps(self.payload).encode("utf-8"))


def league_payload(seasons: list[dict]) -> dict:
    return {"errors": [], "results": 1, "response": [{"league": {"id": 39, "name": "Premier League"},
                                                      "seasons": seasons}]}


def season(year: int, lineups: bool | None, injuries: bool = False) -> dict:
    fixtures = {"events": True, "statistics_players": True} | ({} if lineups is None else {"lineups": lineups})
    return {"year": year, "start": f"{year}-08-10", "end": f"{year + 1}-05-20",
            "coverage": {"fixtures": fixtures, "injuries": injuries}}


def test_missing_key_raises_and_names_the_variable():
    with pytest.raises(ApiFootballError, match="API_FOOTBALL_KEY"):
        api_key({})
    assert api_key({"API_FOOTBALL_KEY": f"  {KEY} "}) == KEY


def test_fetch_sends_the_key_as_a_header_and_caches_the_response_without_it(tmp_path):
    opener = FakeOpener(league_payload([season(2024, True)]))
    payload = fetch("leagues", {"id": 39}, key=KEY, cache_dir=tmp_path, opener=opener)
    request = opener.requests[0]
    assert request.full_url == "https://v3.football.api-sports.io/leagues?id=39"
    assert request.get_header("X-apisports-key") == KEY
    cached = cache_path("leagues", {"id": 39}, tmp_path)
    assert json.loads(cached.read_text(encoding="utf-8")) == payload
    assert KEY not in cached.read_text(encoding="utf-8")


def test_a_cached_response_is_reused_without_a_request(tmp_path):
    fetch("leagues", {"id": 39}, key=KEY, cache_dir=tmp_path, opener=FakeOpener(league_payload([])))
    opener = FakeOpener({"errors": {"unexpected": "should not be called"}})
    fetch("leagues", {"id": 39}, key=KEY, cache_dir=tmp_path, opener=opener)
    assert opener.requests == []


def test_a_refused_request_raises_and_is_not_cached(tmp_path):
    opener = FakeOpener({"errors": {"plan": "Free plans do not have access to this season."}, "response": []})
    with pytest.raises(ApiFootballError, match="Free plans"):
        fetch("fixtures", {"league": 39, "season": 2026}, key=KEY, cache_dir=tmp_path, opener=opener)
    assert not cache_path("fixtures", {"league": 39, "season": 2026}, tmp_path).exists()


def test_fetch_missing_skips_cached_requests_and_stops_at_the_budget(tmp_path):
    requests = [("fixtures/lineups", {"fixture": n}) for n in range(5)]
    fetch(*requests[1], key=KEY, cache_dir=tmp_path, opener=FakeOpener({"errors": [], "response": []}))
    opener, pauses = FakeOpener({"errors": [], "response": []}), []
    fetched, missing = fetch_missing(requests, budget=2, key=KEY, cache_dir=tmp_path, sleep=pauses.append, opener=opener)
    assert (fetched, missing) == (2, 2)
    assert [request.full_url.rsplit("=", 1)[-1] for request in opener.requests] == ["0", "2"]
    assert len(pauses) == 1  # a pause between live requests, none before the first


def test_fetch_missing_raises_on_a_refusal_and_keeps_what_it_fetched(tmp_path):
    class RefuseSecond(FakeOpener):
        def __call__(self, request, timeout: float) -> io.BytesIO:
            self.payload = {"errors": [], "response": []} if not self.requests else {"errors": {"requests": "limit"}}
            return super().__call__(request, timeout)

    requests = [("fixtures/lineups", {"fixture": n}) for n in range(3)]
    with pytest.raises(ApiFootballError, match="limit"):
        fetch_missing(requests, budget=3, key=KEY, cache_dir=tmp_path, sleep=lambda seconds: None,
                      opener=RefuseSecond({}))
    assert cache_path(*requests[0], tmp_path).exists() and not cache_path(*requests[1], tmp_path).exists()


def test_season_coverage_reads_each_flag_and_marks_absent_ones():
    coverage = season_coverage(league_payload([season(2016, True, injuries=False), season(2015, None)]))
    assert coverage["season"].tolist() == ["2015-16", "2016-17"]
    assert coverage.loc[0, "lineups"] is None and coverage.loc[1, "lineups"] is True
    assert coverage.loc[1, ["events", "injuries"]].tolist() == [True, False]


def test_seasons_without_lineups_lists_uncovered_and_absent_seasons():
    coverage = season_coverage(league_payload([season(2015, False), season(2016, True), season(2018, True)]))
    assert seasons_without_lineups(coverage, first=2015, last=2018) == ["2015-16", "2017-18"]
    assert seasons_without_lineups(coverage, first=2016, last=2016) == []


def test_the_app_never_imports_the_api_client():
    assert "api_football" not in (PROJECT_ROOT / "app" / "app.py").read_text(encoding="utf-8")
    assert "api_football" not in (PROJECT_ROOT / "src" / "app_support.py").read_text(encoding="utf-8")

"""The Streamlit app runs offline: headless run with every network connection blocked."""

import socket

import pytest

from src.config import MATCHES_PATH, PROJECT_ROOT, REPORTS_DIR

APP = PROJECT_ROOT / "app" / "app.py"
needs_data = pytest.mark.skipif(
    not (MATCHES_PATH.exists() and (REPORTS_DIR / "stage9_confidence.csv").exists()),
    reason="needs the built data and the Stage 9/10 reports")


LOOPBACK = {"127.0.0.1", "::1", "localhost"}


@pytest.fixture
def no_network(monkeypatch):
    """Block every connection except loopback (asyncio's event loop uses a local socket pair)."""
    connect, create = socket.socket.connect, socket.create_connection

    def guarded_connect(self, address, *args, **kwargs):
        if address[0] not in LOOPBACK:
            raise OSError(f"network access is blocked in this test: {address}")
        return connect(self, address, *args, **kwargs)

    def guarded_create(address, *args, **kwargs):
        if address[0] not in LOOPBACK:
            raise OSError(f"network access is blocked in this test: {address}")
        return create(address, *args, **kwargs)

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket, "create_connection", guarded_create)


@needs_data
def test_app_runs_offline_for_any_two_teams_and_shows_limits(no_network):
    from streamlit.testing.v1 import AppTest

    app = AppTest.from_file(str(APP), default_timeout=300).run()
    assert not app.exception
    app.sidebar.radio[0].set_value("Any two teams").run()
    assert not app.exception
    text = " ".join(block.value for block in app.markdown)
    assert "Limits" in text and "No injury" in text and "Forward-test record" in text
    assert "seasons used in tuning" in text and "2025-26 holdout" in text and "a season is 380 matches" in text
    assert any("log(p_home / p_away)" in caption.value for caption in app.caption)


def test_app_source_makes_no_network_calls():
    source = APP.read_text(encoding="utf-8")
    for call in ("download_epl", "fetch_csv", "urlopen", "requests", "FIXTURES_URL"):
        assert call not in source

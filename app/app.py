"""Streamlit app for the frozen final model. UI only; all logic lives in src/.

Run from the project root: .venv\\Scripts\\streamlit run app/app.py
Works offline from data/processed/matches.parquet, data/forward/predictions_log.csv and
reports/; it makes no network call. Every accuracy shown is read from reports/ by
src/app_support.py and carries its match count; none is written here.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # the project root holds the src package

import pandas as pd
import streamlit as st

from src.app_support import (confidence_label, equal_coverage_comparison, latest_season_teams, limits_lines,
                             upcoming_fixtures)
from src.explain import contributions, home_minus_away_weights, logit_difference
from src.final_model import elo_params, load_config, predictor
from src.forward import (UK, fixture_features, fixture_row, forecast, load_played_matches, read_log,
                         season_pipeline, training_table)
from src.plots import contribution_bars, probability_bars
from src.seasons import current_season, season_label

FORM_STATS = {"points": "Points", "gf": "Goals for", "ga": "Goals against"}


@st.cache_data
def played_matches() -> pd.DataFrame:
    return load_played_matches()


@st.cache_data
def prediction_log() -> pd.DataFrame:
    return read_log()


@st.cache_resource
def final_model() -> tuple:
    """The frozen model fitted once on every match before the current season."""
    config = load_config()
    elo, model = elo_params(config), predictor(config)
    pipeline = season_pipeline(training_table(played_matches(), elo), season_label(current_season()), model)
    return elo, model.columns, pipeline


@st.cache_data
def features_for(home: str, away: str, kickoff: str) -> pd.Series:
    elo, _, _ = final_model()
    return fixture_features(played_matches(), fixture_row(home, away, pd.Timestamp(kickoff)), elo)


def form_table(features: pd.Series, home: str, away: str) -> pd.DataFrame:
    rows = []
    for side, team in (("home", home), ("away", away)):
        row = {"Team": team}
        for window in (5, 10):
            for stat, label in FORM_STATS.items():
                row[f"{label}, last {window}"] = features[f"{side}_{stat}_last{window}"]
        rows.append(row)
    return pd.DataFrame(rows)


st.set_page_config(page_title="EPL match predictor", layout="wide")
st.title("EPL match predictor")
st.caption("Frozen final model (config tag pre-holdout-config): Elo plus recent form, L2 logistic regression.")

now = pd.Timestamp.now(tz="UTC")
upcoming = upcoming_fixtures(now, prediction_log())
mode = st.sidebar.radio("Pick", ["Upcoming fixture", "Any two teams"], index=0 if not upcoming.empty else 1)
if mode == "Upcoming fixture" and not upcoming.empty:
    choice = upcoming.iloc[st.sidebar.selectbox("Fixture", range(len(upcoming)), format_func=lambda i: upcoming["label"].iloc[i])]
    home, away, kickoff = choice["home"], choice["away"], choice["kickoff"]
else:
    if mode == "Upcoming fixture":
        st.sidebar.info("No upcoming fixtures in the prediction log; run scripts/predict_upcoming.py.")
    teams = latest_season_teams(played_matches())
    home = st.sidebar.selectbox("Home team", teams, index=0)
    away = st.sidebar.selectbox("Away team", teams, index=1)
    kickoff, choice = now, None

if home == away:
    st.error("Pick two different teams.")
    st.stop()

elo, columns, pipeline = final_model()
features = features_for(home, away, kickoff.isoformat())
row = features[columns].astype(float).to_frame().T
probabilities = forecast(pipeline, columns, row).iloc[0]

st.subheader(f"{home} v {away}")
st.write(f"Kickoff {kickoff.tz_convert(UK).strftime('%a %d %b %Y %H:%M')} UK" if choice is not None
         else "Hypothetical match, using results up to today.")
left, right = st.columns([3, 2])
with left:
    st.pyplot(probability_bars(probabilities, home, away), use_container_width=True)
with right:
    top = float(probabilities.max())
    st.metric("Top probability", f"{top:.0%}")
    for line in confidence_label(top):
        st.write(line)
    if choice is not None:
        st.caption(f"Logged {choice['predicted_at']}: H {choice['p_home']:.0%}, D {choice['p_draw']:.0%}, "
                   f"A {choice['p_away']:.0%}")

elo_home, elo_away = st.columns(2)
elo_home.metric(f"{home} Elo", f"{features['elo_home']:.0f}")
elo_away.metric(f"{away} Elo", f"{features['elo_away']:.0f}")

st.markdown("**Form** (per-match averages over the last 5 and last 10 league matches)")
st.dataframe(form_table(features, home, away), hide_index=True, use_container_width=True)

st.markdown("**Why: each feature's contribution to the home-minus-away log-odds**")
table = contributions(pipeline, row, columns)
_, intercept = home_minus_away_weights(pipeline)
st.pyplot(contribution_bars(table, home, away), use_container_width=True)
st.dataframe(table.round(4), hide_index=True, use_container_width=True)
st.caption(f"Contribution = coefficient x standardised feature value. Intercept (home advantage) {intercept:+.3f}; "
           f"intercept + contributions = {intercept + table['contribution'].sum():+.3f} = "
           f"log(p_home / p_away) = {logit_difference(pipeline, row, columns):+.3f}.")

with st.container(border=True):
    st.markdown("### Limits")
    st.markdown("\n".join(f"- {line}" for line in limits_lines()))
    st.markdown("- The bookmaker is ahead at equal confidence (each side's own most confident matches, seasons "
                "used in tuning; accuracy as a fraction):")
    st.dataframe(equal_coverage_comparison().round(3), hide_index=True)
    st.caption("The forward-test record is read from reports/forward_score.csv; run scripts.score_forward to update it.")

"""Stage 7 audit: source coverage per season and checks of derived values.

These read a match's own FPL rows on purpose (to measure coverage and to check predicted
bans against who played); nothing here may feed a model.
"""

import pandas as pd

from src.fpl import audit_seasons

MIN_PLAYERS = 11  # a side "has player-level data" when at least 11 players have minutes
FIELDS = ["minutes", "starts", "yellow_cards", "red_cards", "recorded_position", "recorded_team"]


def sides_with_players(linked: pd.DataFrame) -> pd.DataFrame:
    """Per match (season, date, home, away): players with minutes on each side."""
    played = linked[linked["minutes"] > 0]
    counts = played.groupby(["season", "date", "home", "away", "was_home"])["player"].nunique().unstack("was_home")
    return counts.rename(columns={True: "home_players", False: "away_players"}).fillna(0).reset_index()


def fpl_coverage(linked: pd.DataFrame, matches: pd.DataFrame) -> pd.DataFrame:
    """Per season: share of football-data matches where both sides have >= 11 players with minutes."""
    sides = sides_with_players(linked)
    both = sides[(sides["home_players"] >= MIN_PLAYERS) & (sides["away_players"] >= MIN_PLAYERS)]
    seasons = audit_seasons()
    total = matches[matches["season"].isin(seasons)].groupby("season").size().reindex(seasons, fill_value=0)
    covered = both.groupby("season").size().reindex(seasons, fill_value=0)
    return pd.DataFrame({"matches": total, "fpl_both_sides": covered, "fpl_share": covered / total})


def field_presence(rows: pd.DataFrame) -> pd.DataFrame:
    """Per season and field: share of rows with a value (0 when the season lacks the column)."""
    seasons = audit_seasons()
    present = rows.groupby("season")[FIELDS].agg(lambda values: values.notna().mean())
    return present.reindex(seasons, fill_value=0.0)


def squad_listing_check(linked: pd.DataFrame) -> pd.DataFrame:
    """Per season: players FPL lists per team per match, the share of them with 0 minutes, and
    the share of players whose first listing for a team (after its first match) is one they
    played in, i.e. who may have been added to FPL because they played."""
    per_match = linked.groupby(["season", "date", "team"]).agg(
        listed=("player", "nunique"), zero_minutes=("minutes", lambda minutes: (minutes == 0).mean()))
    first = linked.sort_values("date").groupby(["season", "team", "player"]).head(1)
    opening = linked.groupby(["season", "team"])["date"].transform("min")
    first = first[first["date"] > opening.loc[first.index]]
    by_season = per_match.groupby("season").agg(listed_mean=("listed", "mean"), listed_min=("listed", "min"),
                                                 listed_max=("listed", "max"), zero_minute_share=("zero_minutes", "mean"))
    by_season["late_first_listing_played"] = first.groupby("season")["minutes"].apply(lambda minutes: (minutes > 0).mean())
    return by_season


def ban_outcomes(availability: pd.DataFrame, linked: pd.DataFrame) -> pd.DataFrame:
    """Every predicted ban with what happened in the banned match: did not play, played, or
    not listed for the team (left, loaned, or not registered)."""
    minutes = linked.set_index(["date", "team", "player"])["minutes"]
    records = []
    for _, match in availability.iterrows():
        for side in ("home", "away"):
            for kind in ("red", "yellow"):
                for player in match.get(f"{side}_banned_{kind}") or []:
                    played = minutes.get((match["date"], match[side], player))
                    status = "not listed" if played is None else "did not play" if played == 0 else "played"
                    records.append({"season": match["season"], "date": match["date"], "team": match[side],
                                    "player": player, "kind": kind, "status": status})
    return pd.DataFrame(records)


def ban_summary(outcomes: pd.DataFrame) -> pd.DataFrame:
    """Predicted bans by kind and what happened, with the share who did not play."""
    table = outcomes.groupby(["kind", "status"]).size().unstack("status", fill_value=0)
    table["total"] = table.sum(axis=1)
    table["did_not_play_share"] = table.get("did not play", 0) / table["total"]
    return table

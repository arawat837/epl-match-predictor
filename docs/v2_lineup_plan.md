# v2 lineup model: pre-registered test plan

Written 2026-10-24, before any lineup data was fetched or any v2 code was written. The commit that
adds this file (tag `v2-plan`) is the pre-registration record. Nothing here changes the frozen v1
model (`config/final_model.json`, tag `pre-holdout-config`) or its forward log
(`data/forward/predictions_log.csv`).

## 1. Question

Does knowing both teams' announced starting XIs improve the frozen v1 probabilities? The primary
comparison is v2 against v1 on the same 2026-27 matches. The bookmaker comparison is secondary
and is reported with the timing of each set of odds (section 8).

## 2. What was checked about API-Football (2026-10-24)

API-Football's site and documentation sit behind a bot check, which was not bypassed. The facts
below come from API-Football's public blog posts as indexed by search, and from third-party pages.
Anything marked "unverified" is checked at Gate 0 with a real key before it is relied on.

| Item | Finding | Status |
|---|---|---|
| Premier League id | 39 | API-Football guide |
| Lineups | `/fixtures/lineups`: starting XI, formation, bench, coach; player ids and positions | API-Football guide |
| Lineup timing | "20 to 40 minutes" before kickoff is typical, varies by competition (some as early as 75 minutes, some only after the match); the same guide's quick reference says 30-60 minutes | inconsistent; measured at Gate 0 |
| Batch requests | `/fixtures?ids=` takes up to 20 ids and returns events, lineups and player statistics for each | guide about two years old; unverified |
| Injuries | `/injuries` added 5 April 2021; by fixture, team, player or date; type (injury or suspension) and a reason text; refreshed about every 4 hours | no history before April 2021; when each entry was recorded is unknown |
| Coverage by season | `/leagues?id=39` gives per-season flags (`coverage.fixtures.lineups`, `coverage.injuries`); a published sample shows lineups true for 2021 | earlier seasons unverified |
| Plans | free: 100 requests a day, "limited in terms of available seasons" (a developer reports the 2025 season refused); paid from about $19 a month for 7,500 a day | prices from a vendor guide; unverified |

Injuries are left out of v2. Their history starts in 2021 at best, and an entry for a past match
may have been written or edited after kickoff, which the leakage rules cannot check. A player who
is injured at kickoff is also absent from the announced XI, so lineups carry most of that signal.

## 3. Terms of use and what follows for this project

API-Football's terms, as indexed (the search index dates the page at about 581 days old):
reselling the data to third parties is prohibited; the data is provided for projects such as
applications and websites; API-Football gives no licence to publish the data, and obtaining any
authorisation from rights holders (leagues, federations) is the user's responsibility; betting,
broadcasting, fantasy and mass-media uses may need further licences; French law applies. Nothing
found mentions model training or how long data may be stored.

Rules for v2, from these terms and the public repository:

- Personal, non-commercial research only.
- Raw API responses are cached under `data/raw/api_football/` (already gitignored). They are never
  committed or pushed; neither are features derived from them.
- The public Streamlit app keeps showing v1 only. Nothing lineup-derived is published until
  API-Football confirms in writing that it may be.
- The API key lives in an environment variable (`API_FOOTBALL_KEY`) or `.streamlit/secrets.toml`
  (gitignored), never in code, logs or reports.

## 4. Rule change this needs (user approval required)

CLAUDE.md's prediction-time rule fixes predictions at about 1 hour before kickoff. API-Football
publishes lineups later than that (section 2). v2 therefore needs, for v2 only: "a v2 prediction is
made after both official starting XIs are published and before kickoff; it may use those XIs and
nothing else from the match (no minutes, substitutions, events or result)". v1 keeps the current
rule. No v2 code is written before this amendment is approved (Gate R).

## 5. Model, fixed now

v2 = v1's probabilities plus an offset, exactly as in Stage 8 (`src/offset.py`):
logits = log p_v1 + X W, with the draw column fixed at 0, mean log loss + lambda x sum(W^2),
X standardised on the training window and missing values set to 0, so a match with no lineup
data gets v1's probabilities unchanged.

Features, computed per team from Premier League lineups only (cups are not covered), using matches
dated strictly before the match plus that match's announced XI, within a spell (a gap of more than
200 days since the team's previous match starts a new spell, as in v1). Each enters as home_X,
away_X and X_diff (9 inputs):

1. `xi_regulars`: the share of the team's regular XI who start. Regular XI = the 11 players with
   the most starts over the team's previous 10 league matches in the spell that have lineup data;
   ties go to the more recent start, then the lower API player id. Value = (regulars in the
   announced XI) / 11. Missing if the team has fewer than 3 such earlier matches.
2. `xi_changes`: the number of starters not in the team's XI for its previous league match in the
   spell (0-11). Missing if there is no previous match in the spell or its lineup is missing.
3. `keeper_changed`: 1 if the starting goalkeeper (position "G") differs from the previous league
   match's, else 0. Missing under the same conditions, or if no goalkeeper is marked.

No other features, transformations or interactions are added after this point.

## 6. Data and seasons

- Lineups are needed from 2015-16 (lookback only) to 2026-27: 12 seasons, 4,560 matches.
- Base: v1's walk-forward out-of-sample probabilities from 2016-17, the same base as Stage 8
  (compact logistic, tuned Elo 15/50/0.9, C = 0.03).
- The offset for test season S trains on 2016-17 to S-1.
- Lambda is chosen from {0.001, 0.003, 0.01, 0.03, 0.1} on the tuning seasons 2017-18 to 2019-20
  only.
- Development check: 2020-21 to 2025-26 are scored once with the chosen lambda. All of them have
  been seen before (2025-26 is the spent v1 holdout), so this is a check, not a verdict.
- Verdict model: the offset is fitted once on 2016-17 to 2025-26 with the chosen lambda, on top of
  v1 fitted on every match through 2025-26 (as `src/forward.py` does). It is not refitted during
  2026-27. Its configuration is frozen in `config/v2_model.json` and tagged `v2-pre-verdict`
  before any 2026-27 v2 number is computed.
- Verdict season: every 2026-27 league match, evaluated once after the last matchday by a script
  that refuses to run without an unlock flag and aborts if the v2 configuration differs from the
  `v2-pre-verdict` tag. Matches already played before v2 is frozen are included: their lineups
  were public before their kickoffs, and no v2 result on 2026-27 is looked at before the verdict.
- If lineup coverage starts after 2015-16, every window moves forward by the same number of
  seasons, keeping 3 tuning seasons. If fewer than 3 tuning seasons and 2 development seasons
  remain before 2026-27, the plan stops at Gate 0.

## 7. Gates, in order (stop at the first failure and record it)

- **Gate R (rule):** the user approves the section 4 amendment.
- **Gate T (terms):** the current terms are read in full at sign-up and nothing in them forbids
  this use; API-Football support is asked in writing about local storage, model training and
  public display. Local research may go ahead without an answer; public display may not.
- **Gate 0 (coverage and timing):** with a key, `/leagues?id=39` shows lineups covered for every
  season the windows need (one request). On one or more matchdays, each match's lineup endpoint is
  polled every 5 minutes from 90 minutes before kickoff. Pass if both XIs are available at least 10
  minutes before kickoff for at least 90% of matches.
- **Gate L (leakage and linking):** before anything is scored, (a) at least 99% of API fixtures link
  to `matches.parquet` by date and teams, with every unlinked fixture listed; (b) rebuild tests
  pass on a stratified sample of 50 matches: features rebuilt from earlier lineups plus the match's
  own announced XI only, with the match's result and stats scrambled and other same-day matches
  removed, must equal the stored ones; (c) planted leaks are caught on random and targeted samples
  (regulars counting the match's own substitutes or minutes; the previous XI read from the next
  match; the regular XI built from later matches), and the real code is flagged on none.
- **Gate D (development):** with the chosen lambda, v2 has lower pooled log loss than v1 on the
  tuning seasons. If not, v2 is abandoned and no verdict is run.

## 8. Verdict rule for 2026-27, fixed now

Primary: D = mean over all 2026-27 matches of (v2 log loss - v1 log loss), with SE = standard
deviation / sqrt(n), as in `tuning.paired_difference`.

- "v2 improves on v1" if D < 0 and D / SE < -1.645 (one-sided 5% level).
- "v2 is worse than v1" if D > 0 and D / SE > 1.645.
- Otherwise "no demonstrated difference", including D < 0 within noise.

Secondary, reported but not decisive: the paired RPS difference; accuracy for both; D by month; the
number of matches without lineups (where v2 equals v1); and v1 and v2 against Bet365 two ways:
(a) the recorded odds used so far (B365H/D/A, which football-data collects on Friday afternoon for
weekend games and Tuesday afternoon for midweek games, before lineups are known); and (b) Bet365
closing odds (B365CH/CD/CA, the last before kickoff, present for every 2026-27 match so far). Only
(b) has the same information timing as v2.

Tripwire: if v2's log loss is lower than Bet365 closing odds, or its pooled accuracy exceeds 58%,
stop and audit for leakage before reporting anything.

Whatever the outcome, no claim of edge, profit or betting value is made.

## 9. Expected power

One season is about 380 matches. In Stage 8, offset-versus-base differences pooled over the five
reporting seasons had standard errors of 0.0004 to 0.0014 (`reports/stage8_differences.csv`),
roughly 0.001 to 0.003 for a single season. A lineup effect therefore needs to be at least about
0.002 to 0.005 in log loss to be detected at the section 8 threshold. The development check's
standard error is reported before the verdict; if the likely effect is smaller, "no demonstrated
difference" is the expected outcome even if lineups help a little.

## 10. Calls and cost (estimate)

- Backfill: 4,560 matches, about 230 batch requests if the 20-id batch works as described,
  otherwise 4,560 single lineup requests, plus 12 fixture-list requests.
- The free plan cannot cover the current season (developer report) and limits history, so the
  backfill and Gate 0 need a paid plan, at the user's choice and cost, only after Gates R and T.
- A live log of v2 predictions (logged between lineup publication and kickoff, separate
  append-only file) is optional: it would show the timing works and compare live XIs with those
  fetched later. It needs a paid plan for the rest of the season and is not part of the verdict.

## 11. Implementation outline (after the gates; nothing built yet)

- `src/api_football.py`: requests with the standard library only, key from the environment,
  rate limiting, raw JSON cached under `data/raw/api_football/`.
- `src/lineups.py`: parse XIs and link API fixtures to `matches.parquet` (extending
  `src/teams.py` for API team names).
- `src/lineup_features.py`: the three features and the spell rule.
- Reuse `src/offset.py` and the Stage 8 lambda choice; `config/v2_model.json` frozen and tagged.
- Scripts: fetch lineups, development check, verdict (`--unlock-verdict`, refuses before the last
  matchday).
- Tests: leakage rebuilds and planted leaks, parsing from saved JSON, no network calls in tests.
  No new packages.

## 12. Amendments

Any change after this commit is added below with its date and reason, before the verdict. A change
made after any 2026-27 v2 result has been seen voids the pre-registration.

- 2026-10-25, clarification (no change of intent), written while building the features and before
  any of them was scored: in `xi_regulars`, "the team's previous 10 league matches in the spell that
  have lineup data" is read as: take the previous 10 league matches in the spell, and count only
  those of them that have lineup data (missing if fewer than 3 do). The window is not extended back
  to find 10 matches with lineups. The two readings differ only when lineups are missing.

- 2026-10-25, amendment A (approved by the user; written before any injury data was fetched and
  before any v2 feature was scored). Reason: the user asked to add exponentially weighted form and
  injury data. Section 2's reasons for leaving injuries out of v2 still hold at v2's prediction time
  (after the XIs), so injuries go into a separate variant that predicts before lineups. Everything
  below is fixed now.

  **A1. EWMA form (step 2 of v2).** `points_ewma`: per team, the exponentially weighted mean of
  league points (3, 1, 0) over the team's earlier matches in the spell, pandas
  `ewm(span=5, adjust=True, min_periods=3)` applied after `shift(1)`, so a match never counts toward
  its own value; windows cross seasons within a spell, as in v1. Enters as home_points_ewma,
  away_points_ewma and points_ewma_diff. "v2+EWMA" is the section 5 offset model with these 3 inputs
  added to the 9 lineup inputs, lambda chosen again from the same grid on the same tuning seasons
  (2017-18 to 2019-20), and the same development and verdict windows as v2. Gate D for it: lower
  pooled tuning log loss than v2.

  **A2. Pre-lineup injury variant ("v2-pre").** Predicts under v1's prediction-time rule (about an
  hour before kickoff), so it never uses the match's own XI. Base: v1's walk-forward out-of-sample
  probabilities; offset model as in section 5. Inputs (home_X, away_X, X_diff, 9 in all):
  - `injured_regulars`: the share of the team's regular XI (section 5's definition, built from
    earlier matches' lineups) listed by API-Football as missing the fixture. Missing when the regular
    XI is missing.
  - `injured_count`: the number of the team's players listed as missing the fixture (0 when none are
    listed, within seasons API-Football marks as covered for injuries).
  - `points_ewma` (A1).
  "Listed as missing" means an API-Football `/injuries` record for that fixture whose type says the
  player will miss it (API-Football's "Missing Fixture"); records marked as doubtful ("Questionable")
  are not counted. Source: API-Football only; no scraping.
  Seasons: injuries are covered from 2020-21, so 2020-21 is history only; the offset for test season
  S trains on 2020-21 to S-1; lambda is chosen from the section 6 grid on the tuning seasons 2021-22
  to 2023-24; 2024-25 and 2025-26 are the development check (seen seasons, not a verdict); the
  verdict model's offset is fitted once on 2020-21 to 2025-26 and frozen with v2's configuration
  before any 2026-27 result. Verdict season 2026-27, as for v2.
  Gates, in order: **Gate I (injury lists)**, before any injury feature is scored: on every cached
  fixture that has both lineups and injury records (the free seasons, 2022-23 to 2024-25), the share
  of "Missing Fixture" records whose player is in that fixture's starting XI must be at most 2%. A
  higher share means records were written or edited after kickoff, and v2-pre is dropped. Then
  Gate L for its features (rebuilds from earlier matches and lineups plus the fixture's own injury
  list, with the match's own XI and bench removed and its result scrambled; planted leaks: the
  match's own XI used, the next fixture's injury list used), then Gate D: lower pooled tuning log
  loss than v1.

  **A3. Verdict with the Holm correction.** Up to three one-sided comparisons on 2026-27, each with D
  and SE as in section 8 and p = Φ(D / SE): (1) v2 against v1; (2) v2+EWMA against v2; (3) v2-pre
  against v1. Only comparisons whose variant passed its gates are run; m is their number. Holm:
  order the p-values from smallest, and declare comparison k an improvement while
  p(k) ≤ 0.05 / (m - k + 1); stop at the first that is not. This replaces section 8's unadjusted
  "improves" rule (it is stricter). "Worse" (D / SE > 1.645) stays descriptive. Secondary results and
  the tripwire in section 8 apply to every variant.
  Costs: injury lists are one request per season (more if paginated), so the free seasons are
  affordable now; 2020-21, 2021-22, 2025-26 and 2026-27 need the paid plan already required for v2.

## Sources

- API-Football, [new injuries endpoint](https://www.api-football.com/news/post/new-endpoint-injuries)
- API-Football, [beginner's guide](https://www.api-football.com/news/post/how-to-get-started-with-api-football-the-complete-beginners-guide)
- API-Football, [teams and players from a league id](https://www.api-football.com/news/post/how-to-get-all-teams-and-players-from-a-league-id)
- API-Football, [all fixtures data from one league](https://www.api-football.com/news/post/how-to-get-all-fixtures-data-from-one-league)
- API-Football, [pricing](https://www.api-football.com/pricing) and [terms](https://www.api-football.com/terms); API-SPORTS, [terms](https://api-sports.io/terms)
- GitHub, [free plan season restriction report](https://github.com/MinhHai12345/MMO/pull/38)
- Educative, [fixture lineups with API-Football](https://www.educative.io/courses/soccer-api-football-python/Y5NMBnKoP69)
- football-data.co.uk, [notes](https://www.football-data.co.uk/notes.txt)

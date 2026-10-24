# Stage 10: holdout evaluation (2025-26)

Run 2026-10-24T00:38:56+00:00 at commit `bd77453506cd223cfb9a5d25bc094f50c93f8064` (working tree clean: True); config sha256 `225b2fcd1a71a56b2453fcfc67705807983de651d760c2b424f19f421fada1c7`, identical to `pre-holdout-config`. 380 matches, last match 2026-05-24. Model fitted once on seasons up to 2024-25; no refitting inside the holdout.

## Holdout metrics

| predictor | matches | log_loss | rps | accuracy |
|---|---|---|---|---|
| final model | 380 | 1.0271 | 0.2090 | 0.4868 |
| bookmaker | 380 | 1.0185 | 0.2057 | 0.4895 |
| base rate | 380 | 1.0820 | 0.2277 | 0.4263 |
| Elo-only (original, untuned) | 380 | 1.0278 | 0.2095 | 0.4711 |

## Paired per-match log loss difference (final model minus reference; negative = model better)

| final model minus | difference | standard_error | z |
|---|---|---|---|
| bookmaker | 0.0085 | 0.0081 | 1.0536 |
| Elo-only (original, untuned) | -0.0007 | 0.0033 | -0.2135 |

## Confusion matrix (final model; rows actual, columns predicted)

| actual \ predicted | H | D | A |
|---|---|---|---|
| H | 134 | 0 | 28 |
| D | 67 | 0 | 37 |
| A | 63 | 0 | 51 |

## Confidence (Stage 9 definitions; reliable = at least 100 matches)

| predictor | subset | lowest_top_probability | matches | accuracy | reliable |
|---|---|---|---|---|---|
| final model | top probability > 0.45 | 0.4510 | 263 | 0.5247 | True |
| final model | top probability > 0.50 | 0.5000 | 199 | 0.5578 | True |
| final model | top probability > 0.55 | 0.5511 | 139 | 0.5827 | True |
| final model | top probability > 0.60 | 0.6043 | 93 | 0.6452 | False |
| final model | top probability > 0.65 | 0.6506 | 57 | 0.6842 | False |
| final model | most confident 10% | 0.6907 | 38 | 0.6842 | False |
| final model | most confident 20% | 0.6250 | 76 | 0.6711 | False |
| final model | most confident 30% | 0.5805 | 114 | 0.6316 | True |
| bookmaker | top probability > 0.45 | 0.4505 | 262 | 0.5344 | True |
| bookmaker | top probability > 0.50 | 0.5012 | 195 | 0.5590 | True |
| bookmaker | top probability > 0.55 | 0.5504 | 140 | 0.6143 | True |
| bookmaker | top probability > 0.60 | 0.6014 | 90 | 0.6889 | False |
| bookmaker | top probability > 0.65 | 0.6501 | 57 | 0.7193 | False |
| bookmaker | most confident 10% | 0.6782 | 38 | 0.7105 | False |
| bookmaker | most confident 20% | 0.6144 | 76 | 0.6711 | False |
| bookmaker | most confident 30% | 0.5718 | 114 | 0.6579 | True |

The top-10% (38 matches) and top-20% (76 matches) cells are too small to quote alone.

## Noise

Holdout log loss 1.0271 against the 0.9818 reporting-season average: a difference of +0.0453, +1.95 per-match standard errors (SE 0.0233 over 380 matches). That is within the noise expected from one 380-match season.

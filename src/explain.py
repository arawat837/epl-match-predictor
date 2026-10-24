"""Exact per-feature contributions of the final logistic model to the home-minus-away log-odds.

For multinomial logistic regression, log(p_H / p_A) = (b_H - b_A) + sum_j (w_Hj - w_Aj) * z_j,
where z_j is feature j after the pipeline's median imputer and scaler. Each term is that
feature's contribution; with the intercept they sum exactly to the logit difference, so no
approximation such as SHAP is needed.
"""

import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline

from src.models import LABELS


def standardised(pipeline: Pipeline, rows: pd.DataFrame, columns: list[str]) -> np.ndarray:
    """Features after the pipeline's imputer and scaler (fitted on the training window)."""
    imputer, scaler = pipeline.named_steps["simpleimputer"], pipeline.named_steps["standardscaler"]
    return scaler.transform(imputer.transform(rows[columns]))


def class_position(pipeline: Pipeline, outcome: str) -> int:
    classes = list(pipeline.named_steps["logisticregression"].classes_)
    return classes.index(LABELS[outcome])


def home_minus_away_weights(pipeline: Pipeline) -> tuple[np.ndarray, float]:
    """(w_H - w_A per feature, b_H - b_A)."""
    model = pipeline.named_steps["logisticregression"]
    home, away = class_position(pipeline, "H"), class_position(pipeline, "A")
    return model.coef_[home] - model.coef_[away], float(model.intercept_[home] - model.intercept_[away])


def contributions(pipeline: Pipeline, row: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Per feature for one match: raw value, standardised value, coefficient and contribution."""
    weights, _ = home_minus_away_weights(pipeline)
    z = standardised(pipeline, row, columns)[0]
    return pd.DataFrame({"feature": columns, "value": row[columns].iloc[0].to_numpy(dtype=float),
                         "standardised": z, "coefficient": weights, "contribution": weights * z})


def logit_difference(pipeline: Pipeline, row: pd.DataFrame, columns: list[str]) -> float:
    """log(p_H / p_A) from the model's own probabilities."""
    probabilities = pipeline.predict_proba(row[columns])[0]
    return float(np.log(probabilities[class_position(pipeline, "H")] / probabilities[class_position(pipeline, "A")]))

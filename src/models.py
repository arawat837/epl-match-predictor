"""Model predictors for the walk-forward harness: (train, test) -> H/D/A probabilities.

Each model reads only the columns it is given, is fitted on the training window alone,
and is refitted from scratch for every test season. Defaults are the untuned Stage 5
settings; src/tuning.py passes tuned ones.
"""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.base import ClassifierMixin
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from src.metrics import OUTCOMES

LABELS = {outcome: code for code, outcome in enumerate(OUTCOMES)}  # H=0, D=1, A=2
MAX_ITER = 1000  # lbfgs iterations, enough to converge; not a tuned setting
XGB_PARAMS = {
    "objective": "multi:softprob", "eval_metric": "mlogloss", "max_depth": 3,
    "learning_rate": 0.04, "subsample": 0.8, "colsample_bytree": 0.8, "random_state": 0,
}
MAX_TREES = 600
EARLY_STOPPING_ROUNDS = 50


def encode(results: pd.Series) -> pd.Series:
    """H/D/A as 0/1/2, so class order matches OUTCOMES."""
    return results.map(LABELS)


def forecast(probabilities: np.ndarray, index: pd.Index) -> pd.DataFrame:
    """Class probabilities as an H/D/A forecast."""
    return pd.DataFrame(probabilities, index=index, columns=OUTCOMES)


def fit_predict(estimator: ClassifierMixin, columns: list[str], train: pd.DataFrame,
                test: pd.DataFrame) -> pd.DataFrame:
    """Fit on the training window's `columns`, forecast the test matches."""
    estimator.fit(train[columns], encode(train["result"]))
    return forecast(estimator.predict_proba(test[columns]), test.index)


def elo_only(train: pd.DataFrame, test: pd.DataFrame) -> pd.DataFrame:
    """Multinomial logistic regression on elo_diff alone."""
    return fit_predict(LogisticRegression(max_iter=MAX_ITER), ["elo_diff"], train, test)


@dataclass
class LogisticModel:
    """L2 logistic regression on `columns` in a Pipeline whose median imputer and scaler
    are fitted on the training window only. Keeps each fitted pipeline by test season."""

    columns: list[str]
    C: float = 1.0
    fitted: dict[str, Pipeline] = field(default_factory=dict)

    def __call__(self, train: pd.DataFrame, test: pd.DataFrame) -> pd.DataFrame:
        pipeline = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                                 LogisticRegression(C=self.C, max_iter=MAX_ITER))
        self.fitted[test["season"].iloc[0]] = pipeline
        return fit_predict(pipeline, self.columns, train, test)


def stopping_season(train: pd.DataFrame) -> str:
    """The season XGBoost early-stops on: the last season of the training window."""
    return train["season"].max()


def early_stopping_tree_count(train: pd.DataFrame, columns: list[str],
                              params: dict[str, object] = XGB_PARAMS) -> int:
    """Trees to use: fit on all but the training window's last season, stop early on that season."""
    last = stopping_season(train)
    fit_part, stop_part = train[train["season"] < last], train[train["season"] == last]
    model = XGBClassifier(**params, n_estimators=MAX_TREES, early_stopping_rounds=EARLY_STOPPING_ROUNDS)
    model.fit(fit_part[columns], encode(fit_part["result"]),
              eval_set=[(stop_part[columns], encode(stop_part["result"]))], verbose=False)
    return model.best_iteration + 1


@dataclass
class XGBoostModel:
    """XGBoost with the tree count chosen by early stopping, then refitted on the full
    training window. Keeps each fitted model by test season for feature importance."""

    columns: list[str]
    params: dict[str, object] = field(default_factory=lambda: dict(XGB_PARAMS))
    fitted: dict[str, XGBClassifier] = field(default_factory=dict)
    trees: dict[str, int] = field(default_factory=dict)
    stopping_seasons: dict[str, str] = field(default_factory=dict)

    def __call__(self, train: pd.DataFrame, test: pd.DataFrame) -> pd.DataFrame:
        trees = early_stopping_tree_count(train, self.columns, self.params)
        model = XGBClassifier(**self.params, n_estimators=trees)
        model.fit(train[self.columns], encode(train["result"]))
        season = test["season"].iloc[0]
        self.fitted[season], self.trees[season] = model, trees
        self.stopping_seasons[season] = stopping_season(train)
        return forecast(model.predict_proba(test[self.columns]), test.index)


def gain_importance(models: list[XGBClassifier]) -> pd.Series:
    """Mean share of gain per feature across fitted models (each model's gains sum to 1)."""
    shares = [pd.Series(model.get_booster().get_score(importance_type="gain")) for model in models]
    shares = [share / share.sum() for share in shares]
    return pd.concat(shares, axis=1).fillna(0.0).mean(axis=1).sort_values(ascending=False)

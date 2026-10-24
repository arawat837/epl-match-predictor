"""Offset model: frozen base probabilities plus a penalised linear adjustment of the logits.

logits_c = log(p_base_c) + sum_j W[j, c] * x_j, with the draw column of W fixed at 0.
W minimises mean log loss + lam * sum(W**2) (L-BFGS). Features are standardised with
training-window statistics and NaNs become 0 after standardising. With W = 0 the model
returns the base probabilities.
"""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from src.metrics import OUTCOMES, one_hot

BASE_COLUMNS = ["base_H", "base_D", "base_A"]
FREE_COLUMNS = [0, 2]  # H and A columns of W are fitted; D stays 0


def softmax(logits: np.ndarray) -> np.ndarray:
    """Row-wise softmax."""
    exponentials = np.exp(logits - logits.max(axis=1, keepdims=True))
    return exponentials / exponentials.sum(axis=1, keepdims=True)


def full_weights(free: np.ndarray, n_features: int) -> np.ndarray:
    """W with the fitted H and A columns and a zero draw column."""
    weights = np.zeros((n_features, len(OUTCOMES)))
    weights[:, FREE_COLUMNS] = free.reshape(n_features, len(FREE_COLUMNS))
    return weights


def offset_probabilities(log_base: np.ndarray, features: np.ndarray, weights: np.ndarray) -> np.ndarray:
    """softmax(log p_base + X W)."""
    return softmax(log_base + features @ weights)


def objective(free: np.ndarray, log_base: np.ndarray, features: np.ndarray, observed: np.ndarray,
              lam: float) -> tuple[float, np.ndarray]:
    """Mean log loss + lam * sum(W**2), and its gradient with respect to the free weights."""
    weights = full_weights(free, features.shape[1])
    probabilities = offset_probabilities(log_base, features, weights)
    loss = -np.mean(np.log((probabilities * observed).sum(axis=1))) + lam * np.sum(weights ** 2)
    gradient = features.T @ (probabilities - observed) / len(features) + 2 * lam * weights
    return float(loss), gradient[:, FREE_COLUMNS].ravel()


def fit_offset(log_base: np.ndarray, features: np.ndarray, observed: np.ndarray, lam: float) -> np.ndarray:
    """W minimising the penalised mean log loss, starting from W = 0."""
    start = np.zeros(features.shape[1] * len(FREE_COLUMNS))
    result = minimize(objective, start, args=(log_base, features, observed, lam), jac=True, method="L-BFGS-B")
    if not result.success:
        raise RuntimeError(f"offset fit did not converge: {result.message}")
    return full_weights(result.x, features.shape[1])


@dataclass(frozen=True)
class Standardiser:
    """Training-window means and standard deviations; NaN after standardising becomes 0."""

    mean: np.ndarray
    std: np.ndarray

    @classmethod
    def fit(cls, features: pd.DataFrame) -> "Standardiser":
        mean = features.mean().fillna(0.0).to_numpy()
        std = features.std(ddof=0).to_numpy()
        return cls(mean, np.where(np.isfinite(std) & (std > 0), std, 1.0))

    def transform(self, features: pd.DataFrame) -> np.ndarray:
        return np.nan_to_num((features.to_numpy(dtype=float) - self.mean) / self.std, nan=0.0)


def base_log_probabilities(table: pd.DataFrame) -> np.ndarray:
    return np.log(table[BASE_COLUMNS].to_numpy(dtype=float))


@dataclass
class OffsetModel:
    """Predictor: base probabilities adjusted by availability features, refitted per test season."""

    columns: list[str]
    lam: float
    weights: dict[str, np.ndarray] = field(default_factory=dict)
    training_seasons: dict[str, list[str]] = field(default_factory=dict)

    def __call__(self, train: pd.DataFrame, test: pd.DataFrame) -> pd.DataFrame:
        scaler = Standardiser.fit(train[self.columns])
        weights = fit_offset(base_log_probabilities(train), scaler.transform(train[self.columns]),
                             one_hot(train["result"]), self.lam)
        season = test["season"].iloc[0]
        self.weights[season], self.training_seasons[season] = weights, sorted(set(train["season"]))
        probabilities = offset_probabilities(base_log_probabilities(test), scaler.transform(test[self.columns]), weights)
        return pd.DataFrame(probabilities, index=test.index, columns=OUTCOMES)


def base_forecast(train: pd.DataFrame, test: pd.DataFrame) -> pd.DataFrame:
    """The frozen base model's out-of-sample probabilities for the test matches."""
    return test[BASE_COLUMNS].set_axis(OUTCOMES, axis=1)

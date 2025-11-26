# src/py_livechart/ml.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple
import warnings

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from .client import LiveChartClient

DEFAULT_FEATURES = ["z", "n", "binding", "qbm", "qa", "qec", "sn", "sp"]
TARGET_COLUMN = "half_life_sec"


@dataclass
class MLResult:
    model: Pipeline
    metrics: Dict[str, float]
    features: List[str]


def _clean_numeric(df: pd.DataFrame) -> pd.DataFrame:
    df = df.apply(pd.to_numeric, errors="coerce")
    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    return df


def _build_pipeline(random_state: int) -> Pipeline:
    return Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("model", RandomForestRegressor(n_estimators=300, random_state=random_state, n_jobs=-1)),
        ]
    )


def train_half_life_model(
    client: LiveChartClient,
    features: List[str] = None,
    test_size: float = 0.2,
    random_state: int = 42,
) -> Tuple[Pipeline, Dict[str, float], List[str]]:
    """
    Fetches all ground state data and trains a regression model that predicts
    nuclide half-life (log-seconds). The function now imputes missing values and
    guards against NaNs so the downstream example does not crash.
    """
    selected_features = features or DEFAULT_FEATURES
    print("Fetching all ground state data... (this may take a moment)")
    gs_data = client.get_ground_states(nuclide="all")
    print("Data fetched successfully.")

    print("Preprocessing data for machine learning...")
    df = gs_data[selected_features + [TARGET_COLUMN]].copy()
    df = _clean_numeric(df)
    df = df[df[TARGET_COLUMN] > 0]
    df.dropna(subset=[TARGET_COLUMN], inplace=True)

    y = np.log1p(df[TARGET_COLUMN])
    X = df[selected_features]

    # Remove rows that have all NaNs in the feature space before fitting
    mask = ~X.isna().all(axis=1)
    X = X[mask]
    y = y[mask]

    print(f"Preprocessing complete. {len(X)} nuclides available for training.")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state
    )

    print("Training RandomForestRegressor model with automatic imputation...")
    model = _build_pipeline(random_state)
    model.fit(X_train, y_train)

    print("Evaluating model...")
    y_pred_log = model.predict(X_test)
    r2 = r2_score(y_test, y_pred_log)
    rmsle = np.sqrt(mean_squared_error(y_test, y_pred_log))
    mae_log = mean_absolute_error(y_test, y_pred_log)

    print("\n--- Model Evaluation Results ---")
    print(f"R-squared (R²): {r2:.4f}")
    print(f"Root Mean Squared Log Error (RMSLE): {rmsle:.4f}")
    print(f"Mean Absolute Log Error (MALE): {mae_log:.4f}")
    print("---------------------------------")

    metrics = {"r2_score": r2, "rmsle": rmsle, "male": mae_log}

    if r2 < 0:
        warnings.warn(
            "Half-life regression yielded a negative R² score. "
            "This indicates the simple baseline is not predictive for the current snapshot. "
            "Consider feature engineering or refraining from using the ML helper in production analyses.",
            RuntimeWarning,
        )

    return model, metrics, selected_features


def predict_half_life_seconds(
    model: Pipeline, feature_order: List[str], nuclide_df: pd.DataFrame
) -> float:
    """
    Helper utility that takes the trained pipeline, enforces the feature order,
    and returns the predicted physical half-life in seconds.
    """
    features = _clean_numeric(nuclide_df[feature_order].copy())
    features.fillna(0.0, inplace=True)
    log_pred = model.predict(features)[0]
    return float(np.expm1(log_pred))
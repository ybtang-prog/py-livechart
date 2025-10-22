# src/py_livechart/ml.py

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score

from .client import LiveChartClient


def train_half_life_model(client: LiveChartClient, test_size: float = 0.2, random_state: int = 42):
    """
    Fetches all ground state data and trains a model to predict nuclide half-life.
    """
    print("Fetching all ground state data... (this may take a moment)")
    gs_data = client.get_ground_states(nuclide='all')
    print("Data fetched successfully.")

    print("Preprocessing data for machine learning...")
    features = ['z', 'n', 'isospin', 'binding', 'qbm', 'qa', 'qec', 'sn', 'sp']
    target = 'half_life_sec'

    df = gs_data[features + [target]].copy()
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df.dropna(inplace=True)
    df = df[df[target] > 0]
    df[target] = np.log1p(df[target])

    print(f"Preprocessing complete. {len(df)} nuclides available for training.")

    X = df[features]
    y = df[target]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state
    )

    print("Training RandomForestRegressor model...")
    model = RandomForestRegressor(n_estimators=100, random_state=random_state, n_jobs=-1)
    model.fit(X_train, y_train)

    print("Evaluating model...")
    y_pred_log = model.predict(X_test)
    r2 = r2_score(y_test, y_pred_log)
    rmsle = np.sqrt(mean_squared_error(y_test, y_pred_log))

    print("\n--- Model Evaluation Results ---")
    print(f"R-squared (R²): {r2:.4f}")
    print(f"Root Mean Squared Log Error (RMSLE): {rmsle:.4f}")
    print("---------------------------------")

    metrics = {"r2_score": r2, "rmsle": rmsle}

    return model, metrics, features
import numpy as np
import pandas as pd
from pathlib import Path

from py_livechart import ml


DATA_SNAPSHOT = Path(__file__).resolve().parents[1] / "data" / "ground_states_sample.csv"


class SnapshotClient:
    def __init__(self):
        if not DATA_SNAPSHOT.exists():
            raise FileNotFoundError(
                f"{DATA_SNAPSHOT} missing. Run the LiveChart snapshot script before testing."
            )
        self._df = pd.read_csv(DATA_SNAPSHOT)

    def get_ground_states(self, nuclide: str):
        if nuclide.lower() == "all":
            return self._df.copy()
        mask = self._df["nuclide"].str.lower() == nuclide.lower()
        if not mask.any():
            raise ValueError(f"No cached data for nuclide '{nuclide}'")
        return self._df[mask].copy()


def test_train_half_life_model_returns_metrics():
    client = SnapshotClient()
    model, metrics, features = ml.train_half_life_model(client)

    assert set(["r2_score", "rmsle", "male"]).issubset(metrics.keys())
    assert len(features) > 0

    ca48 = client.get_ground_states("48ca").iloc[[0]]
    prediction = ml.predict_half_life_seconds(model, features, ca48)
    assert prediction > 0



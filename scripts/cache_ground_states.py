from __future__ import annotations

from io import StringIO
from pathlib import Path
from typing import Iterable, List, Optional

import pandas as pd
import requests

BASE_URL = "https://nds.iaea.org/relnsd/v1/data"
USER_AGENT = "py-livechart/1.x (cache script; https://github.com/ybtang-prog/py-livechart)"


def _request_ground_states(nuclide: str) -> pd.DataFrame:
    response = requests.get(
        BASE_URL,
        params={"fields": "ground_states", "nuclides": nuclide},
        headers={"User-Agent": USER_AGENT},
        timeout=120,
    )
    response.raise_for_status()
    df = pd.read_csv(StringIO(response.text))
    if "nuclide" not in df.columns:
        df["nuclide"] = (df["z"] + df["n"]).astype(int).astype(str) + df["symbol"].str.lower()
    return df


def fetch_snapshot(nuclides: Optional[Iterable[str]] = None) -> pd.DataFrame:
    """
    Download ground-state data directly from LiveChart.

    If `nuclides` is None, fetches the complete table via `nuclides=all`.
    Otherwise, iterates through the provided nuclide list.
    """
    if nuclides is None:
        return _request_ground_states("all")

    frames: List[pd.DataFrame] = []
    for nuclide in nuclides:
        df = _request_ground_states(nuclide)
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def main() -> None:
    snapshot = fetch_snapshot()
    output_path = Path(__file__).resolve().parents[1] / "data" / "ground_states_sample.csv"
    output_path.parent.mkdir(exist_ok=True)
    snapshot.to_csv(output_path, index=False)
    print(f"Wrote {len(snapshot)} rows to {output_path}")


if __name__ == "__main__":
    main()


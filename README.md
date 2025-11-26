# py-livechart

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PyPI](https://img.shields.io/pypi/v/py-livechart)](https://pypi.org/project/py-livechart/)
[![CI](https://github.com/ybtang-prog/py-livechart/actions/workflows/publish.yml/badge.svg)](https://github.com/ybtang-prog/py-livechart/actions/workflows/publish.yml)

`py-livechart` is a resilient Python client for the [IAEA LiveChart of Nuclides Data Download API](https://nds.iaea.org/relnsd/v1/data). It wraps `requests` with thread-safe sessions, retry-aware HTTP adapters, client-side rate limiting, rich exceptions, and optional dataclass models so nuclear engineers can script reproducible pipelines without re-implementing networking boilerplate.

## Table of contents

1. [Installation](#installation)
2. [Quick start](#quick-start)
3. [Core API surface](#core-api-surface)
4. [Robustness and concurrency](#robustness-and-concurrency)
5. [Request limits and performance](#request-limits-and-performance)
6. [Examples and case studies](#examples-and-case-studies)
7. [Machine learning helper](#machine-learning-helper)
8. [License](#license)

## Installation

### PyPI (recommended)

```bash
pip install py-livechart
```

Optional extras:

```bash
pip install "py-livechart[plot]"     # plotly, kaleido
pip install "py-livechart[ml]"       # scikit-learn
pip install "py-livechart[dev]"      # pytest, requests-mock, build
```

### From source

```bash
git clone https://github.com/ybtang-prog/py-livechart.git
cd py-livechart
pip install -e .
```

## Quick start

```python
from py_livechart import LiveChartClient

client = LiveChartClient(rate_limit_per_sec=1.0, timeout=20)
ground_states = client.get_ground_states("60co")
fission_records = client.get_fission_yields(
    "cumulative_fy", parent="235u", return_type="records"
)

print(ground_states.head())
print(fission_records[0])
```

Additional, fully reproducible scripts live in `example.py`, `data/`, and `output/`.

## Core API surface

| Method | Key parameters | Return | Notes |
| --- | --- | --- | --- |
| `get_ground_states(nuclide, return_type)` | `nuclide="60co"` or `"all"` | DataFrame / `GroundStateRecord` | Nuclide ground-state metadata |
| `get_levels(nuclide, return_type)` | same as above | DataFrame / records | Level schemes |
| `get_gammas(nuclide, return_type)` | same as above | DataFrame / records | Gamma emissions |
| `get_decay_rads(nuclide, rad_type, return_type)` | `rad_type ∈ {a,bp,bm,g,e,x}` | DataFrame / records | Decay radiation |
| `get_beta_spectra(nuclide, rad_type, metastable_seqno, return_type)` | `rad_type ∈ {bp,bm}` | DataFrame / records | Beta spectra with optional metastable selector |
| `get_fission_yields(yield_type, parent, product, return_type)` | `yield_type ∈ {cumulative_fy, independent_fy}` | DataFrame / `FissionYieldRecord` | Parent/product filters |
| `fetch_ground_states_many(nuclides, return_type, max_workers)` | sequence of nuclides | mapping + error map | Thread-safe concurrent helper |

Each public method has parameter-oriented docstrings, and all custom exceptions are defined in `py_livechart/exceptions.py` for easy rendering with `pdoc`, `sphinx`, or the SoftwareX manuscript.

## Robustness and concurrency

- **Timeouts + retries**: every HTTP call honors a configurable timeout (default 15 s) and attaches `urllib3.Retry` with exponential backoff for 429/5xx codes.
- **Token-bucket rate limiting**: default throttle is 1.5 req/s to satisfy the LiveChart guideline of ≤3 req/s per user. Set `rate_limit_per_sec=0` to disable or tune `burst_size`.
- **Thread-safe sessions**: each worker thread lazily receives its own `requests.Session` so researchers can re-use a single client inside `ThreadPoolExecutor`.
- **Concurrent helper**: `fetch_ground_states_many` batches nuclide lists and emits both payloads and per-nuclide errors, which removes boilerplate when building large caches.
- **Rich error model**: the client differentiates invalid parameter payloads, missing inputs, server-side outages, request timeouts, and local throttling, making it clear which failures are actionable.
- **Data abstractions**: `GroundStateRecord` and `FissionYieldRecord` decouple downstream code from raw CSV column names, easing cross-library comparisons (ENSDF, JEFF, ENDF/B, etc.).

## Request limits and performance

- The IAEA Nuclear Data Section recommends **≤3 requests/s per user**. The default limit of 1.5 req/s proved reliable for day-to-day scripted work and for HPC queues.
- Shanghai 100 Mbps lab measurements (Nov 2025):
  - `get_ground_states("60co")`: median 0.34 s (n=30)
  - `get_ground_states("all")`: ~95 s at 1 req/s, suitable for nightly jobs or cached mirrors
  - `get_fission_yields("cumulative_fy","235u")`: ~0.78 s (n=20)
- Additional benchmarks, including throughput vs. rate-limit settings, are documented in `docs/case_studies.md` for direct citation inside the SoftwareX manuscript.

## Examples and case studies

`example.py` contains four runnable workflows with logging and exception handling:

1. **Thread-safe batch fetch** – uses `fetch_ground_states_many` to download multiple nuclides in parallel and reports individual failures.
2. **Ground-state query** – prints the full Co‑60 table and demonstrates the `return_type="records"` abstraction.
3. **Fission yield analysis** – generates `output/u235_fission_yield.pdf` with Plotly, and compares IAEA yields against the `data/jeff_fission_yield_sample.csv` excerpt.
4. **Machine learning template** – calls `ml.train_half_life_model` and `ml.predict_half_life_seconds` to showcase a reproducible data-mining workflow.

Expanded commentary, reproducibility notes, and links to figures referenced in the manuscript are compiled in `docs/case_studies.md`.

To keep tests deterministic while still relying on real physics data, run `python scripts/cache_ground_states.py`. This helper downloads **the entire** ground-state catalog (`nuclides=all`) from the official LiveChart API (using the recommended User-Agent header) and stores the snapshot in `data/ground_states_sample.csv` (~3.3k rows). The ML unit test consumes this real snapshot so reviewers can reproduce the workflow without synthetic fixtures.

## Machine learning helper

The optional `py_livechart.ml` module packages a safe baseline for researchers who want to perform rapid prototyping:

- `train_half_life_model` standardizes numeric columns, removes non-physical targets, and trains a `SimpleImputer + RandomForestRegressor` pipeline with deterministic seeds.
- The function returns `(model, metrics, features)` where `metrics` contains `r2_score`, `rmsle`, and `male`. Negative `r2` values trigger a warning so users know the proxy model should not be deployed as-is.
- `predict_half_life_seconds` enforces feature order, performs the same numeric cleanup, fills any missing data prior to inference, and returns physical half-life values in seconds.

```python
from py_livechart import LiveChartClient, ml

client = LiveChartClient()
model, metrics, features = ml.train_half_life_model(client)
print(metrics)

ca48 = client.get_ground_states("48ca")
prediction = ml.predict_half_life_seconds(model, features, ca48)
print(f"T1/2(Ca-48) ≈ {prediction:.3e} s")
```

## License

MIT. See [LICENSE](LICENSE) for details.


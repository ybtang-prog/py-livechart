# Case studies and performance notes

This supplemental document expands on the examples referenced in the SoftwareX manuscript (Submission SOFTX-D-25-00755). It targets reproducibility, reviewer feedback, and the quantitative evidence requested by the editor.

## 1. Thread-safe batch ground-state cache

- **Script**: `python example.py` (Example 1)
- **Workflow**: `LiveChartClient.fetch_ground_states_many` receives a list of nuclides, uses the built-in thread-safe sessions, and deduplicates inputs before dispatching them inside a `ThreadPoolExecutor`.
- **Output**: the script prints an ordered summary with per-nuclide payload sizes and reports any failures separately so that users can retry only what failed.
- **Purpose**: addresses the editor's concern about concurrent use by providing an out-of-the-box routine that exercises the thread-safety guarantees.

## 2. Fission yield analysis + JEFF comparison

- **Script**: `python example.py` (Example 3)
- **Steps**:
  1. `get_fission_yields("cumulative_fy","235u")` provides the IAEA data.
  2. `data/jeff_fission_yield_sample.csv` supplies a JEFF-3.3 excerpt.
  3. `compare_with_reference_library` aligns on `a_daughter` and prints the top five percentage deviations.
  4. A Plotly bar chart is exported to `output/u235_fission_yield.pdf` with logarithmic Y axis for readability.
- **Purpose**: responds directly to Reviewer #4 by demonstrating cross-library validation and by producing a camera-ready figure cited in the paper.

## 3. Machine learning template (half-life regression)

- **Functions**: `ml.train_half_life_model`, `ml.predict_half_life_seconds`.
- **Features**: `["z","n","binding","qbm","qa","qec","sn","sp"]`; all numeric columns are coerced with `pd.to_numeric`, infinities are replaced with NaN, and median imputation prevents NaN propagation.
- **Metrics** (Shanghai lab, Nov 26, 2025; random_state=42):
  - R² = 0.41
  - RMSLE = 0.86
  - MALE = 0.61
- **Prediction example**: running the sample script yields `T1/2(Ca-48) ≈ 6.5e19 s`, consistent with the tabulated (6.4e19 s) reference.
- **Purpose**: resolves Reviewer #2 and #3 feedback regarding NaN failures and demonstrates that the machine learning component is an optional, well-instrumented template.

## 4. Throughput and rate-limit measurements

| API call | Sample size | Avg time (s) | Notes |
| --- | --- | --- | --- |
| `get_ground_states("60co")` | 1 nuclide | 0.34 | 30 runs, wired network |
| `get_ground_states("all")` | ~3400 rows | 95 | Rate limit pinned to 1 req/s |
| `get_fission_yields("cumulative_fy","235u")` | 876 rows | 0.78 | Includes Plotly export |

> Environment: Shanghai 100 Mbps campus network, 230 ms round-trip latency. These figures match the discussion in Section 3 of the manuscript.

## 5. Common issues and resolutions

- **NaN in ML workflow**: the latest `ml.py` uses median imputation and explicit numeric coercion. If scikit-learn still raises a NaN error, verify that `scikit-learn>=1.2` is installed.
- **API timeouts**: adjust `LiveChartClient(timeout=30, max_retries=5)` in the constructor or provide a custom session factory with a proxy if running behind a firewall.
- **Parallel downloads**: prefer `fetch_ground_states_many` over ad-hoc threading; it respects local throttling and propagates individual failures without stopping the whole batch.
- **Ground-state fixtures**: `data/ground_states_sample.csv` is produced via `python scripts/cache_ground_states.py`, which downloads the complete ground-state table (`nuclides=all`) from the IAEA API using the recommended User-Agent header. Regenerate the snapshot before rerunning the ML unit test if the IAEA releases new evaluations.


# example.py

import pandas as pd
import numpy as np
import sys
from pathlib import Path

from py_livechart import LiveChartClient, NoDataFoundError, ml

DATA_DIR = Path("data")
REFERENCE_FY = DATA_DIR / "jeff_fission_yield_sample.csv"

# --- Helper Functions ---


def print_header(title: str):
    """Prints a formatted header to the console."""
    print("\n" + "=" * 80)
    print(f" {title.upper()} ".center(80, "="))
    print("=" * 80)


def save_plot_as_pdf(fig, filename: str):
    """Saves a Plotly figure as a PDF, checking for the 'kaleido' dependency."""
    try:
        import kaleido  # noqa: F401

        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        file_path = output_dir / filename
        print(f"\nGenerating plot '{file_path}'...")
        fig.write_image(file_path, format="pdf")
        print(f"Plot saved successfully. You can find it in the '{output_dir.name}/' directory.")
    except ImportError:
        print("\nSkipping PDF plot generation: 'kaleido' package not found.")
        print("To save plots as PDF for your paper, please install it with: pip install kaleido")
    except Exception as e:
        print(f"\nAn error occurred while saving the plot: {e}")


def compare_with_reference_library(u235_df: pd.DataFrame):
    """Compare IAEA cumulative FYs with JEFF sample data to illustrate workflows."""
    if not REFERENCE_FY.exists():
        print("Reference JEFF dataset missing; skipping comparison example.")
        return
    ref_df = pd.read_csv(REFERENCE_FY)
    ref_df.rename(columns={"mass_number": "a_daughter", "cumulative_fy": "jeff_fy"}, inplace=True)
    merged = u235_df.merge(ref_df, how="inner", on="a_daughter")
    merged["iaea_fy"] = pd.to_numeric(merged["cumulative_thermal_fy"], errors="coerce")
    merged["delta_pct"] = ((merged["iaea_fy"] - merged["jeff_fy"]) / merged["jeff_fy"]) * 100
    merged.dropna(subset=["iaea_fy", "jeff_fy"], inplace=True)
    print("\nJEFF vs IAEA LiveChart (subset provided in data/jeff_fission_yield_sample.csv)")
    print(merged[["a_daughter", "iaea_fy", "jeff_fy", "delta_pct"]].head())


def demonstrate_concurrent_ground_state_fetch(client: LiveChartClient):
    """Showcase the built-in thread-safe helper for Reviewer #1/#4 requests."""
    print_header("Example 1: Thread-safe batch fetch of ground states")
    nuclides = ["60co", "99tc", "137cs", "bad-input"]
    results, errors = client.fetch_ground_states_many(
        nuclides, return_type="records", max_workers=4
    )
    print("Successful nuclides:")
    for name, payload in results.items():
        print(f"  - {name}: {len(payload)} record(s)")
    if errors:
        print("\nNuclides that failed (can be retried individually):")
        for name, exc in errors.items():
            print(f"  - {name}: {exc}")
    print("Concurrent fetch complete.\n")


def main():
    """Main function to run all demonstration examples."""
    print_header("Initializing py-livechart client")
    client = LiveChartClient(rate_limit_per_sec=1.0, burst_size=2, timeout=20)
    print("Client initialized successfully.")

    demonstrate_concurrent_ground_state_fetch(client)

    print_header("Example 2: Fetching Ground State Properties for Cobalt-60")
    try:
        co60_gs = client.get_ground_states("60co")
        print("Successfully fetched data for Co-60:")
        print(co60_gs.to_string())
    except Exception as e:
        print(f"An error occurred: {e}")

    print_header("Example 3: Analyzing Fission Yields of U-235")
    try:
        u235_fy_df = client.get_fission_yields(yield_type="cumulative_fy", parent="235u")
        fy_plot_df = u235_fy_df[["a_daughter", "cumulative_thermal_fy"]].copy()
        fy_plot_df.columns = ["mass_number", "yield"]
        fy_plot_df["yield"] = pd.to_numeric(fy_plot_df["yield"], errors="coerce")
        fy_plot_df.dropna(inplace=True)
        mass_yield = fy_plot_df.groupby("mass_number")["yield"].sum().reset_index()
        print("Top 5 most abundant fission product mass numbers for U-235 (thermal):")
        print(mass_yield.sort_values(by="yield", ascending=False).head())
        try:
            import plotly.express as px

            fig = px.bar(
                mass_yield,
                x="mass_number",
                y="yield",
                log_y=True,
                title="Cumulative Fission Yield vs. Mass Number for U-235 (Thermal)",
                labels={"mass_number": "Mass Number (A)", "yield": "Cumulative Yield"},
            )
            fig.update_layout(
                font=dict(family="Arial, sans-serif", size=12),
                title_font_size=16,
                xaxis_title_font_size=14,
                yaxis_title_font_size=14,
            )
            save_plot_as_pdf(fig, "u235_fission_yield.pdf")
        except ImportError:
            print("\nPlotly is not installed. Skipping plot generation. Install with: pip install plotly")
        compare_with_reference_library(u235_fy_df)
    except NoDataFoundError:
        print("Could not retrieve fission yield data for U-235.")
    except Exception as e:
        print(f"An error occurred: {e}")

    print_header("Example 4: Machine Learning - Predicting Nuclide Half-Life")
    print("This may take a minute or two depending on your internet connection.")
    run_ml = input("Do you want to run this example? (y/n): ").strip().lower()
    if run_ml == "y":
        try:
            model, metrics, features = ml.train_half_life_model(client)
            print("\nModel training complete!")
            print(f"Achieved R-squared (R²) score on the test set: {metrics['r2_score']:.4f}")
            print("\nUsing the trained model for a prediction on a known nuclide...")
            ca48_df = client.get_ground_states("48ca")
            predicted_half_life_sec = ml.predict_half_life_seconds(model, features, ca48_df)
            actual_half_life_series = pd.to_numeric(
                ca48_df["half_life_sec"], errors="coerce"
            ).dropna()
            actual_half_life_sec = float(actual_half_life_series.iloc[0]) if not actual_half_life_series.empty else np.nan
            print(f"-> Predicted half-life for Ca-48: {predicted_half_life_sec:.3e} seconds")
            if not np.isnan(actual_half_life_sec):
                print(f"-> Actual half-life for Ca-48:    {actual_half_life_sec:.3e} seconds")
        except Exception as e:
            print(f"\nAn error occurred during the machine learning example: {e}")
    else:
        print("Skipping machine learning example.")


if __name__ == "__main__":
    main()

# example.py

import pandas as pd
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from py_livechart import LiveChartClient, NoDataFoundError, ml

DATA_DIR = Path("data")
JEFF_U235_FY = DATA_DIR / "jeff33_u235_thermal_mass_yield.csv"

# --- Helper Functions ---


def print_header(title: str):
    """Prints a formatted header to the console."""
    print("\n" + "=" * 80)
    print(f" {title.upper()} ".center(80, "="))
    print("=" * 80)


def save_plot_as_pdf(fig, filename: str):
    """Saves a Plotly figure as a PDF, checking for the 'kaleido' dependency."""
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    file_path = output_dir / filename
    
    # Try to save as PDF
    try:
        import kaleido  # noqa: F401
        print(f"\nGenerating plot '{file_path}'...")
        fig.write_image(file_path, format="pdf")
        print(f"Plot saved successfully as PDF. You can find it in the '{output_dir.name}/' directory.")
    except ImportError:
        print("\nSkipping PDF plot generation: 'kaleido' package not found.")
        print("To save plots as PDF for your paper, please install it with: pip install kaleido")
        # Save as HTML instead
        html_path = file_path.with_suffix(".html")
        fig.write_html(str(html_path))
        print(f"Plot saved as HTML instead: {html_path}")
    except Exception as e:
        print(f"\nAn error occurred while saving the plot as PDF: {e}")
        # Save as HTML as fallback
        html_path = file_path.with_suffix(".html")
        try:
            fig.write_html(str(html_path))
            print(f"Plot saved as HTML instead: {html_path}")
        except Exception as e2:
            print(f"Failed to save as HTML: {e2}")


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
            import plotly.graph_objects as go

            # Determine x-axis range based on IAEA data
            x_min = mass_yield["mass_number"].min()
            x_max = mass_yield["mass_number"].max()
            
            # Create figure
            fig = go.Figure()
            
            # Add IAEA data as bar chart
            fig.add_trace(
                go.Bar(
                    x=mass_yield["mass_number"],
                    y=mass_yield["yield"],
                    name="IAEA LiveChart",
                    marker=dict(color="blue", opacity=0.7),
                    hovertemplate="Mass: %{x}<br>IAEA Yield: %{y:.4e}<extra></extra>"
                )
            )
            
            # Add JEFF-3.3 data as bar chart if available
            if JEFF_U235_FY.exists():
                try:
                    jeff_df = pd.read_csv(JEFF_U235_FY)
                    jeff_df["yield"] = pd.to_numeric(jeff_df["yield"], errors="coerce")
                    jeff_df.dropna(inplace=True)
                    jeff_df = jeff_df.sort_values("mass_number")
                    
                    # Filter JEFF data to IAEA x-axis range (optional, for better visualization)
                    # But keep all data for completeness
                    jeff_in_range = jeff_df[
                        (jeff_df["mass_number"] >= x_min) & 
                        (jeff_df["mass_number"] <= x_max)
                    ]
                    
                    # Add JEFF-3.3 data as bar chart
                    fig.add_trace(
                        go.Bar(
                            x=jeff_df["mass_number"],
                            y=jeff_df["yield"],
                            name="JEFF-3.3",
                            marker=dict(color="red", opacity=0.7),
                            hovertemplate="Mass: %{x}<br>JEFF-3.3 Yield: %{y:.4e}<extra></extra>"
                        )
                    )
                    print(f"\nAdded JEFF-3.3 data: {len(jeff_df)} mass numbers")
                    print(f"  JEFF data in IAEA range ({x_min}-{x_max}): {len(jeff_in_range)} mass numbers")
                except Exception as e:
                    print(f"\nWarning: Could not load JEFF-3.3 data: {e}")
            
            # Update layout with x-axis range based on IAEA data
            fig.update_layout(
                title="Cumulative Fission Yield vs. Mass Number for U-235 (Thermal): IAEA LiveChart vs JEFF-3.3",
                xaxis_title="Mass Number (A)",
                yaxis_title="Cumulative Yield",
                yaxis_type="log",
                xaxis=dict(range=[x_min - 2, x_max + 2]),
                font=dict(family="Arial, sans-serif", size=12),
                title_font_size=16,
                xaxis_title_font_size=14,
                yaxis_title_font_size=14,
                legend=dict(
                    x=0.02,
                    y=0.98,
                    bgcolor="rgba(255,255,255,0.8)",
                    bordercolor="black",
                    borderwidth=1
                ),
                barmode="group",  # Group bars side by side
            )
            save_plot_as_pdf(fig, "u235_fission_yield.pdf")
        except ImportError:
            print("\nPlotly is not installed. Skipping plot generation. Install with: pip install plotly")
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

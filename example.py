# example.py

import pandas as pd
import numpy as np
import sys
from pathlib import Path

# --- Local Development Import ---
# This ensures that the 'src' directory is on the Python path,
# allowing us to import 'py_livechart' as if it were installed.
# This script MUST be run from the project root directory.
# (e.g., C:\...\py-livechart> python example.py)
sys.path.insert(0, str(Path(__file__).resolve().parent / 'src'))

from py_livechart import LiveChartClient, NoDataFoundError, ml

# --- Helper Functions ---

def print_header(title: str):
    """Prints a formatted header to the console."""
    print("\n" + "="*80)
    print(f" {title.upper()} ".center(80, "="))
    print("="*80)

def save_plot_as_pdf(fig, filename: str):
    """Saves a Plotly figure as a PDF, checking for the 'kaleido' dependency."""
    try:
        import kaleido
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

def main():
    """Main function to run all demonstration examples."""
    print_header("Initializing py-livechart client")
    client = LiveChartClient()
    print("Client initialized successfully.")

    print_header("Example 1: Fetching Ground State Properties for Cobalt-60")
    try:
        co60_gs = client.get_ground_states('60co')
        print("Successfully fetched data for Co-60:")
        print(co60_gs.to_string())
    except Exception as e:
        print(f"An error occurred: {e}")

    print_header("Example 2: Analyzing Fission Yields of U-235")
    try:
        u235_fy_df = client.get_fission_yields(yield_type='cumulative_fy', parent='235u')
        fy_plot_df = u235_fy_df[['a_daughter', 'cumulative_thermal_fy']].copy()
        fy_plot_df.columns = ['mass_number', 'yield']
        fy_plot_df['yield'] = pd.to_numeric(fy_plot_df['yield'], errors='coerce')
        fy_plot_df.dropna(inplace=True)
        mass_yield = fy_plot_df.groupby('mass_number')['yield'].sum().reset_index()
        print("Top 5 most abundant fission product mass numbers for U-235 (thermal):")
        print(mass_yield.sort_values(by='yield', ascending=False).head())
        try:
            import plotly.express as px
            fig = px.bar(
                mass_yield, x='mass_number', y='yield', log_y=True,
                title='Cumulative Fission Yield vs. Mass Number for U-235 (Thermal)',
                labels={'mass_number': 'Mass Number (A)', 'yield': 'Cumulative Yield'}
            )
            fig.update_layout(
                font=dict(family="Arial, sans-serif", size=12),
                title_font_size=16, xaxis_title_font_size=14, yaxis_title_font_size=14
            )
            save_plot_as_pdf(fig, "u235_fission_yield.pdf")
        except ImportError:
            print("\nPlotly is not installed. Skipping plot generation. Install with: pip install plotly")
    except NoDataFoundError:
        print("Could not retrieve fission yield data for U-235.")
    except Exception as e:
        print(f"An error occurred: {e}")

    print_header("Example 3: Machine Learning - Predicting Nuclide Half-Life")
    print("This may take a minute or two depending on your internet connection.")
    run_ml = input("Do you want to run this example? (y/n): ")
    if run_ml.lower() == 'y':
        try:
            model, metrics, features = ml.train_half_life_model(client)
            print("\nModel training complete!")
            print(f"Achieved R-squared (R²) score on the test set: {metrics['r2_score']:.4f}")
            print("\nUsing the trained model for a prediction on a known nuclide...")
            ca48_data = client.get_ground_states('48ca')[features]
            log_pred = model.predict(ca48_data)
            predicted_half_life_sec = np.expm1(log_pred)[0]
            actual_half_life_sec = pd.to_numeric(client.get_ground_states('48ca')['half_life_sec'].iloc[0])
            print(f"-> Predicted half-life for Ca-48: {predicted_half_life_sec:.3e} seconds")
            print(f"-> Actual half-life for Ca-48:    {actual_half_life_sec:.3e} seconds")
        except Exception as e:
            print(f"\nAn error occurred during the machine learning example: {e}")
    else:
        print("Skipping machine learning example.")

if __name__ == "__main__":
    main()
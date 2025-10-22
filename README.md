# py-livechart

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

`py-livechart` is a user-friendly Python client for the [IAEA Livechart of Nuclides Data Download API](https://nds.iaea.org/relnsd/v1/data). It simplifies the process of retrieving nuclear structure and decay data by providing a clean, high-level interface that returns data directly as `pandas.DataFrame` objects, ready for analysis.

This library is designed for physicists, nuclear engineers, data scientists, and students who need programmatic access to reliable nuclear data without the hassle of manual URL construction and error handling.

## Key Features

- **Simple API**: Intuitive methods like `get_levels('135xe')` instead of complex URLs.
- **Pandas Integration**: All data is returned in a `pandas.DataFrame` for immediate use with the Python data science ecosystem.
- **Robust Error Handling**: Automatically handles API-specific error codes and HTTP issues, raising clear, specific exceptions.
- **Machine Learning Ready**: Includes a module (`ml.py`) to demonstrate how to use the data for scientific machine learning tasks, such as predicting nuclide half-life.

## Installation

As this package is not yet on PyPI, you can use it directly from the source code.

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/ybtang-prog/py-livechart.git
    cd py-livechart
    ```

2.  **Install the dependencies:**
    The project requires several packages. You can install them using pip:
    ```bash
    pip install requests pandas scikit-learn numpy plotly kaleido
    ```

## How to Run the Examples

The `example.py` script in the root directory demonstrates the main functionalities of the library. It is designed to be run directly from the project's root directory:

```bash
python example.py
```

This script will:
1.  Fetch ground state data for Cobalt-60.
2.  Analyze the fission yields for Uranium-235 and save a publication-quality plot as `output/u235_fission_yield.pdf`.
3.  Optionally, download all nuclide data to train a machine learning model to predict half-lives.

An `output/` directory will be created to store the generated figures.

## Basic Usage in Your Own Project

To use the library in your own scripts, you can either:

**A) Work within the cloned directory:**

Place your script in the root of the `py-livechart` directory. Because `example.py` modifies the system path, a simpler way to import in your own script is:

```python
# your_script.py
from src.py_livechart import LiveChartClient

client = LiveChartClient()
data = client.get_ground_states('fe')
print(data)
```

**B) Install the package in editable mode (Recommended for development):**

This method links the package in your Python environment directly to your source code, allowing you to import it from anywhere.

From the project root directory, run:
```bash
pip install -e .
```
Now you can import `py_livechart` from any script on your system, and any changes you make to the source code will be immediately available.

```python
# Can be run from any directory after editable install
from py_livechart import LiveChartClient

client = LiveChartClient()
levels = client.get_levels('137cs')
print(levels.head())
```

## Machine Learning Example

`py-livechart` makes it easy to gather datasets for machine learning. The `ml` module provides a turnkey function to train a model that predicts nuclide half-life based on ground state properties. You can see it in action by running `example.py` and following the prompts.

```python
# Snippet from example.py
from py_livechart import LiveChartClient, ml

client = LiveChartClient()

# This function fetches all data, preprocesses it, and trains a model
model, metrics, features = ml.train_half_life_model(client)

print(f"\nModel training complete! R² score: {metrics['r2_score']:.4f}")
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
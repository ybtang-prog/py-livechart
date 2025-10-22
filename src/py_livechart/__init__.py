# src/py_livechart/__init__.py

__version__ = "1.0.0"

from .client import LiveChartClient
from .exceptions import (
    LiveChartAPIError,
    NoDataFoundError,
    MissingParameterError,
    InvalidParameterError,
    UnknownAPIError,
    HTTPError
)
# This makes the 'ml' module accessible as 'py_livechart.ml'
from . import ml
# src/py_livechart/exceptions.py

class LiveChartAPIError(Exception):
    """Base exception class for all py-livechart errors."""
    pass

class NoDataFoundError(LiveChartAPIError):
    """Raised when the API returns code 0 (request is valid, but no data found)."""
    pass

class MissingParameterError(LiveChartAPIError):
    """Raised for API codes 1, 2, 4 (a required parameter is missing)."""
    pass

class InvalidParameterError(LiveChartAPIError):
    """Raised for API codes 3, 5 (a parameter value is invalid)."""
    pass

class UnknownAPIError(LiveChartAPIError):
    """Raised for API code 6 or any other unknown error."""
    pass

class HTTPError(LiveChartAPIError):
    """Raised for HTTP errors (e.g., 403 Forbidden, 500 Server Error)."""
    pass
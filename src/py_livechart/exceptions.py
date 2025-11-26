# src/py_livechart/exceptions.py

class LiveChartAPIError(Exception):
    """Base exception class for all py-livechart errors."""


class NoDataFoundError(LiveChartAPIError):
    """Raised when the API returns code 0 (request is valid, but no data found)."""


class MissingParameterError(LiveChartAPIError):
    """Raised for API codes 1, 2, 4 (a required parameter is missing)."""


class InvalidParameterError(LiveChartAPIError):
    """Raised for API codes 3, 5 (a parameter value is invalid)."""


class UnknownAPIError(LiveChartAPIError):
    """Raised for API code 6 or any other unknown error."""


class HTTPError(LiveChartAPIError):
    """Raised for HTTP errors (e.g., 403 Forbidden, 500 Server Error)."""


class LiveChartClientRequestError(LiveChartAPIError):
    """Raised when a request cannot be sent because of a client-side issue."""


class LiveChartServerError(LiveChartAPIError):
    """Raised when the remote LiveChart service is unavailable (5xx)."""


class NetworkTimeoutError(LiveChartAPIError):
    """Raised when an HTTP timeout occurs."""


class RateLimitExceededError(LiveChartAPIError):
    """Raised when local throttling prevents issuing a request in time."""
# src/py_livechart/client.py

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from io import StringIO
import threading
import time
from typing import Dict, List, Literal, Optional, Sequence, Tuple, Union

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from .exceptions import (
    HTTPError,
    InvalidParameterError,
    LiveChartAPIError,
    LiveChartClientRequestError,
    LiveChartServerError,
    MissingParameterError,
    NetworkTimeoutError,
    NoDataFoundError,
    RateLimitExceededError,
    UnknownAPIError,
)
from .models import FissionYieldRecord, GroundStateRecord

ReturnType = Literal["dataframe", "records"]


class _TokenBucket:
    """Simple, thread-safe token bucket rate limiter."""

    def __init__(self, rate_per_sec: float, burst_size: int):
        self.rate = max(rate_per_sec, 0.0)
        self.capacity = max(burst_size, 1)
        self.tokens = float(self.capacity)
        self.timestamp = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self, timeout: Optional[float] = None) -> None:
        if self.rate == 0:
            # rate == 0 disables throttling
            return
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            with self._lock:
                now = time.monotonic()
                delta = now - self.timestamp
                self.timestamp = now
                self.tokens = min(self.capacity, self.tokens + delta * self.rate)
                if self.tokens >= 1:
                    self.tokens -= 1
                    return
                wait_time = (1 - self.tokens) / self.rate if self.rate else 0
            if deadline is not None and (time.monotonic() + wait_time) > deadline:
                raise RateLimitExceededError(
                    "Rate limiter prevented issuing a request within the allotted time."
                )
            time.sleep(wait_time)


class LiveChartClient:
    """
    Thread-safe Python client for the IAEA LiveChart Data Download API.

    Parameters
    ----------
    base_url:
        API endpoint root; overrideable for testing.
    user_agent:
        Custom User-Agent header. Defaults to a modern desktop signature as
        recommended by the NDS team.
    timeout:
        Per-request timeout (seconds). Defaults to 15 s.
    max_retries:
        Number of idempotent retries for transient failures (HTTP 429/5xx, timeouts).
    backoff_factor:
        Exponential backoff factor applied between retries.
    rate_limit_per_sec:
        Client-side throttle to respect the IAEA guideline of ≤3 requests/s per user.
        Set to 0 to disable throttling.
    burst_size:
        Number of immediate requests allowed before throttling kicks in.
    session_factory:
        Optional callable returning a configured :class:`requests.Session`. Used mainly
        for testing.
    """

    def __init__(
        self,
        base_url: str = "https://nds.iaea.org/relnsd/v1/data",
        user_agent: Optional[str] = None,
        timeout: float = 15.0,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        rate_limit_per_sec: float = 1.5,
        burst_size: int = 3,
        session_factory=None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.user_agent = user_agent or (
            "py-livechart/1.x (+https://github.com/ybtang-prog/py-livechart)"
        )
        self.timeout = timeout
        self._thread_local = threading.local()
        self._session_factory = session_factory
        self._rate_limiter = _TokenBucket(rate_limit_per_sec, burst_size)
        self._retry_config = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET",),
            raise_on_status=False,
        )

    # --------------------------------------------------------------------- #
    # Internal helpers
    # --------------------------------------------------------------------- #
    def _get_session(self) -> requests.Session:
        """Provide a per-thread requests.Session with retry adapters attached."""
        session = getattr(self._thread_local, "session", None)
        if session is not None:
            return session

        session = self._session_factory() if self._session_factory else requests.Session()
        adapter = HTTPAdapter(max_retries=self._retry_config)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        session.headers.update({"User-Agent": self.user_agent})
        self._thread_local.session = session
        return session

    @staticmethod
    def _handle_api_error(code: int) -> None:
        error_map = {
            0: NoDataFoundError("Request is valid, but no data fulfilling the conditions was found."),
            1: MissingParameterError("'fields' parameter is not given."),
            2: MissingParameterError("'nuclides' parameter is required but was not given."),
            3: InvalidParameterError("'fields' parameter is misspelled or invalid."),
            4: MissingParameterError("'parents' or 'products' not given for fission yields."),
            5: InvalidParameterError("'rad_types' parameter is not valid."),
            6: UnknownAPIError("An unknown error occurred on the API server."),
        }
        raise error_map.get(code, UnknownAPIError(f"Received unknown API error code: {code}"))

    def _request(
        self,
        params: dict,
        return_type: ReturnType = "dataframe",
        record_factory=None,
    ) -> Union[pd.DataFrame, List]:
        """Issue a throttled, retried GET request and parse the CSV payload."""
        self._rate_limiter.acquire(timeout=self.timeout)
        session = self._get_session()

        try:
            response = session.get(self.base_url, params=params, timeout=self.timeout)
        except requests.exceptions.Timeout as exc:
            raise NetworkTimeoutError(f"Request timed out after {self.timeout} s.") from exc
        except requests.exceptions.RequestException as exc:
            raise LiveChartClientRequestError(f"Unable to complete request: {exc}") from exc

        if response.status_code >= 500:
            raise LiveChartServerError(
                f"LiveChart service unavailable (HTTP {response.status_code})."
            )
        if response.status_code >= 400:
            raise HTTPError(
                f"LiveChart rejected the request (HTTP {response.status_code} {response.reason})."
            )

        content = response.text.strip()
        if content.isdigit():
            self._handle_api_error(int(content))

        df = pd.read_csv(StringIO(content))
        if return_type == "records":
            if record_factory:
                return [record_factory(row) for _, row in df.iterrows()]
            return df.to_dict(orient="records")
        return df

    @staticmethod
    def _validate_rad_type(rad_type: str, allowed: Sequence[str], label: str) -> None:
        if rad_type not in allowed:
            raise InvalidParameterError(
                f"Invalid '{label}'. Must be one of {sorted(list(allowed))}."
            )

    # --------------------------------------------------------------------- #
    # Public API
    # --------------------------------------------------------------------- #
    def get_ground_states(
        self, nuclide: str, return_type: ReturnType = "dataframe"
    ) -> Union[pd.DataFrame, List[GroundStateRecord]]:
        """
        Retrieve ground-state properties for a nuclide or for the full chart.

        Parameters
        ----------
        nuclide:
            Any nuclide string accepted by the LiveChart API (e.g., "60co") or the
            literal "all" to download the entire table.
        return_type:
            "dataframe" for a pandas.DataFrame payload (default) or "records" to
            convert into :class:`GroundStateRecord` dataclasses.
        """
        params = {"fields": "ground_states", "nuclides": nuclide}
        if return_type == "records":
            return self._request(params, return_type="records", record_factory=GroundStateRecord.from_row)
        return self._request(params)

    def get_levels(
        self, nuclide: str, return_type: ReturnType = "dataframe"
    ) -> Union[pd.DataFrame, List[dict]]:
        """
        Retrieve level scheme information.

        Parameters
        ----------
        nuclide:
            Target nuclide symbol.
        return_type:
            "dataframe" (default) or "records" for dictionaries.
        """
        params = {"fields": "levels", "nuclides": nuclide}
        return self._request(params, return_type=return_type)

    def get_gammas(
        self, nuclide: str, return_type: ReturnType = "dataframe"
    ) -> Union[pd.DataFrame, List[dict]]:
        """
        Retrieve gamma emission intensities and energies.

        Parameters mirror :meth:`get_levels`.
        """
        params = {"fields": "gammas", "nuclides": nuclide}
        return self._request(params, return_type=return_type)

    def get_decay_rads(
        self, nuclide: str, rad_type: str, return_type: ReturnType = "dataframe"
    ) -> Union[pd.DataFrame, List[dict]]:
        """
        Retrieve decay radiation data for a given radiation type.

        Parameters
        ----------
        nuclide:
            Target nuclide symbol.
        rad_type:
            One of {"a","bp","bm","g","e","x"} as defined by the API.
        return_type:
            "dataframe" (default) or "records" for dictionaries.
        """
        allowed = {"a", "bp", "bm", "g", "e", "x"}
        self._validate_rad_type(rad_type, allowed, "rad_type")
        params = {"fields": "decay_rads", "nuclides": nuclide, "rad_types": rad_type}
        return self._request(params, return_type=return_type)

    def get_beta_spectra(
        self,
        nuclide: str,
        rad_type: str,
        metastable_seqno: Optional[int] = None,
        return_type: ReturnType = "dataframe",
    ) -> Union[pd.DataFrame, List[dict]]:
        """
        Retrieve beta spectra for a nuclide.

        Parameters
        ----------
        nuclide:
            Target nuclide symbol.
        rad_type:
            "bp" or "bm".
        metastable_seqno:
            Optional metastable level identifier used by LiveChart.
        return_type:
            "dataframe" (default) or "records" for dictionaries.
        """
        allowed = {"bp", "bm"}
        self._validate_rad_type(rad_type, allowed, "rad_type (beta spectra)")
        params = {"fields": "bin_beta", "nuclides": nuclide, "rad_types": rad_type}
        if metastable_seqno is not None:
            params["metastable_seqno"] = metastable_seqno
        return self._request(params, return_type=return_type)

    def get_fission_yields(
        self,
        yield_type: Literal["cumulative_fy", "independent_fy"],
        parent: Optional[str] = None,
        product: Optional[str] = None,
        return_type: ReturnType = "dataframe",
    ) -> Union[pd.DataFrame, List[FissionYieldRecord]]:
        """
        Retrieve fission yield data filtered by parent and/or product nuclide.

        Parameters
        ----------
        yield_type:
            "cumulative_fy" or "independent_fy".
        parent:
            Parent fissile nuclide string (e.g., "235u").
        product:
            Optional product nuclide symbol to further filter results.
        return_type:
            "dataframe" (default) or "records" to emit :class:`FissionYieldRecord`.
        """
        allowed = {"cumulative_fy", "independent_fy"}
        if yield_type not in allowed:
            raise InvalidParameterError(f"Invalid 'yield_type'. Must be one of {sorted(list(allowed))}.")
        if not parent and not product:
            raise MissingParameterError("At least one of 'parent' or 'product' must be specified for fission yields.")
        params = {"fields": yield_type}
        if parent:
            params["parents"] = parent
        if product:
            params["products"] = product
        if return_type == "records":
            return self._request(params, return_type="records", record_factory=FissionYieldRecord.from_row)
        return self._request(params)

    def fetch_ground_states_many(
        self,
        nuclides: Sequence[str],
        return_type: ReturnType = "dataframe",
        max_workers: int = 4,
        raise_on_error: bool = False,
    ) -> Tuple[
        Dict[str, Union[pd.DataFrame, List[GroundStateRecord]]],
        Dict[str, Exception],
    ]:
        """
        Fetch ground states for multiple nuclides concurrently in a thread-safe way.

        Parameters
        ----------
        nuclides:
            Iterable of nuclide strings. Duplicates are ignored.
        return_type:
            Matches :meth:`get_ground_states`.
        max_workers:
            Upper bound for internal ThreadPoolExecutor workers.
        raise_on_error:
            If true, the first encountered exception is raised immediately. If false,
            failures are aggregated into the second return value.

        Returns
        -------
        Tuple[Dict[str, Any], Dict[str, Exception]]
            Mapping of nuclide string to payload plus a per-nuclide error map.
        """
        unique = list(dict.fromkeys(nuclides))
        results: Dict[str, Union[pd.DataFrame, List[GroundStateRecord]]] = {}
        errors: Dict[str, Exception] = {}

        if not unique:
            return results, errors

        def _worker(nuclide: str):
            try:
                payload = self.get_ground_states(nuclide, return_type=return_type)
                return (nuclide, payload, None)
            except Exception as exc:  # pragma: no cover - error path validated separately
                return (nuclide, None, exc)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for future in as_completed([executor.submit(_worker, n) for n in unique]):
                nuclide, payload, error = future.result()
                if error is not None:
                    if raise_on_error:
                        raise error
                    errors[nuclide] = error
                else:
                    results[nuclide] = payload

        return results, errors
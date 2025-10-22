# src/py_livechart/client.py

import requests
import pandas as pd
from io import StringIO

from .exceptions import (
    LiveChartAPIError, NoDataFoundError, InvalidParameterError,
    MissingParameterError, UnknownAPIError, HTTPError
)

class LiveChartClient:
    """
    A Python client for the IAEA Livechart of Nuclides Data Download API.
    """
    def __init__(self, base_url="https://nds.iaea.org/relnsd/v1/data", user_agent=None):
        self.base_url = base_url
        self.user_agent = user_agent or 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:77.0) Gecko/20100101 Firefox/77.0'
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': self.user_agent})

    def _handle_api_error(self, code: int):
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

    def _make_request(self, params: dict) -> pd.DataFrame:
        try:
            response = self.session.get(self.base_url, params=params)
            response.raise_for_status()
            content = response.text
            if content.isdigit():
                self._handle_api_error(int(content))
            return pd.read_csv(StringIO(content))
        except requests.exceptions.HTTPError as e:
            raise HTTPError(f"HTTP request failed: {e.response.status_code} {e.response.reason}") from e
        except LiveChartAPIError:
            raise
        except Exception as e:
            raise LiveChartAPIError(f"An unexpected error occurred during the request: {e}") from e

    def get_ground_states(self, nuclide: str) -> pd.DataFrame:
        params = {'fields': 'ground_states', 'nuclides': nuclide}
        return self._make_request(params)

    def get_levels(self, nuclide: str) -> pd.DataFrame:
        params = {'fields': 'levels', 'nuclides': nuclide}
        return self._make_request(params)

    def get_gammas(self, nuclide: str) -> pd.DataFrame:
        params = {'fields': 'gammas', 'nuclides': nuclide}
        return self._make_request(params)

    def get_decay_rads(self, nuclide: str, rad_type: str) -> pd.DataFrame:
        allowed = {'a', 'bp', 'bm', 'g', 'e', 'x'}
        if rad_type not in allowed:
            raise InvalidParameterError(f"Invalid 'rad_type'. Must be one of {sorted(list(allowed))}.")
        params = {'fields': 'decay_rads', 'nuclides': nuclide, 'rad_types': rad_type}
        return self._make_request(params)

    def get_beta_spectra(self, nuclide: str, rad_type: str, metastable_seqno: int = None) -> pd.DataFrame:
        allowed = {'bp', 'bm'}
        if rad_type not in allowed:
            raise InvalidParameterError(f"Invalid 'rad_type' for beta spectra. Must be one of {sorted(list(allowed))}.")
        params = {'fields': 'bin_beta', 'nuclides': nuclide, 'rad_types': rad_type}
        if metastable_seqno is not None:
            params['metastable_seqno'] = metastable_seqno
        return self._make_request(params)

    def get_fission_yields(self, yield_type: str, parent: str = None, product: str = None) -> pd.DataFrame:
        allowed = {'cumulative_fy', 'independent_fy'}
        if yield_type not in allowed:
            raise InvalidParameterError(f"Invalid 'yield_type'. Must be one of {sorted(list(allowed))}.")
        if not parent and not product:
            raise MissingParameterError("At least one of 'parent' or 'product' must be specified for fission yields.")
        params = {'fields': yield_type}
        if parent:
            params['parents'] = parent
        if product:
            params['products'] = product
        return self._make_request(params)
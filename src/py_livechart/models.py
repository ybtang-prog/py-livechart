from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


def _to_float(value) -> Optional[float]:
    try:
        if value is None:
            return None
        if value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value) -> Optional[int]:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


@dataclass
class GroundStateRecord:
    """Pythonic representation of a nuclide ground state."""

    symbol: Optional[str]
    mass_number: Optional[int]
    proton_number: Optional[int]
    neutron_number: Optional[int]
    half_life_sec: Optional[float]
    spin_parity: Optional[str]
    binding_mev: Optional[float]
    q_alpha_mev: Optional[float]
    q_beta_minus_mev: Optional[float]
    q_beta_plus_mev: Optional[float]
    sn_mev: Optional[float]
    sp_mev: Optional[float]

    @classmethod
    def from_row(cls, row) -> "GroundStateRecord":
        return cls(
            symbol=row.get("symbol"),
            mass_number=_to_int(row.get("a")),
            proton_number=_to_int(row.get("z")),
            neutron_number=_to_int(row.get("n")),
            half_life_sec=_to_float(row.get("half_life_sec")),
            spin_parity=row.get("spin"),
            binding_mev=_to_float(row.get("binding")),
            q_alpha_mev=_to_float(row.get("qa")),
            q_beta_minus_mev=_to_float(row.get("qbm")),
            q_beta_plus_mev=_to_float(row.get("qbp")),
            sn_mev=_to_float(row.get("sn")),
            sp_mev=_to_float(row.get("sp")),
        )


@dataclass
class FissionYieldRecord:
    """Normalized record for fission yield data."""

    parent: Optional[str]
    product: Optional[str]
    mass_number: Optional[int]
    cumulative_thermal_fy: Optional[float]
    independent_thermal_fy: Optional[float]

    @classmethod
    def from_row(cls, row) -> "FissionYieldRecord":
        return cls(
            parent=row.get("parent"),
            product=row.get("product"),
            mass_number=_to_int(row.get("a_daughter")),
            cumulative_thermal_fy=_to_float(row.get("cumulative_thermal_fy")),
            independent_thermal_fy=_to_float(row.get("independent_thermal_fy")),
        )


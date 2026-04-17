"""Converts burned area (km2) into emissions and health impact metrics."""

from dataclasses import dataclass
from typing import Dict

from .config import EMISSION_FACTORS, RegionConfig


@dataclass
class EmissionResult:
    burned_area_km2: float
    straw_burnt_tonnes: float
    pm25_tonnes: float
    co2_eq_tonnes: float
    co_tonnes: float
    ch4_tonnes: float
    nox_tonnes: float
    bc_tonnes: float
    health_cost_usd: float
    carbon_credit_usd: float
    all_pollutants: Dict

    @property
    def health_cost_usd_bn(self) -> float:
        return self.health_cost_usd / 1e9

    @property
    def co2_eq_million_tonnes(self) -> float:
        return self.co2_eq_tonnes / 1e6

    @property
    def straw_million_tonnes(self) -> float:
        return self.straw_burnt_tonnes / 1e6


def calculate_emissions(burned_area_km2: float,
                        cfg: RegionConfig) -> EmissionResult:
    """Calculate pollutant emissions and costs from burned area."""
    straw = burned_area_km2 * cfg.straw_yield_t_per_km2

    def emit(g_per_kg: float) -> float:
        # g/kg to t/t then multiply by straw tonnes.
        return straw * (g_per_kg / 1000.0)

    pm25 = emit(cfg.pm25_g_per_kg)
    co2 = emit(cfg.co2_g_per_kg)
    ch4 = emit(cfg.ch4_g_per_kg)
    co_e = emit(cfg.co_g_per_kg)

    # GWP100 for CH4 from IPCC AR6.
    co2_eq = co2 + (ch4 * 27.9)

    health_cost = pm25 * cfg.health_cost_usd_per_t_pm25
    carbon_credit = co2_eq * 15.0

    all_pollutants = {
        pol: {
            'tonnes': straw * (ef['value'] / 1000.0),
            'kilotonnes': straw * (ef['value'] / 1000.0) / 1000.0,
            'unit': ef['unit'],
            'source': ef['source'],
        }
        for pol, ef in EMISSION_FACTORS.items()
    }

    return EmissionResult(
        burned_area_km2=burned_area_km2,
        straw_burnt_tonnes=straw,
        pm25_tonnes=pm25,
        co2_eq_tonnes=co2_eq,
        co_tonnes=co_e,
        ch4_tonnes=ch4,
        nox_tonnes=emit(EMISSION_FACTORS['NOx']['value']),
        bc_tonnes=emit(EMISSION_FACTORS['BC']['value']),
        health_cost_usd=health_cost,
        carbon_credit_usd=carbon_credit,
        all_pollutants=all_pollutants,
    )

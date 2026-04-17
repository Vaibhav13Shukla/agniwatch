"""Tests for the production emissions module."""

import sys

sys.path.insert(0, "/home/vaibhav/agniwatch")

from core.config import RegionConfig
from core.emissions import calculate_emissions


def _cfg() -> RegionConfig:
    return RegionConfig(
        name="Test Region",
        bounds=[0.0, 0.0, 1.0, 1.0],
        country="XX",
        crop="Rice",
        pre_start="09-01",
        pre_end="09-30",
        post_start="10-15",
        post_end="11-30",
        straw_yield_t_per_km2=400.0,
        pm25_g_per_kg=6.0,
        co2_g_per_kg=1515.0,
        ch4_g_per_kg=2.7,
        co_g_per_kg=92.0,
        health_cost_usd_per_t_pm25=75000.0,
    )


def test_calculate_emissions_basic():
    cfg = _cfg()
    result = calculate_emissions(burned_area_km2=100.0, cfg=cfg)

    # 100 km2 * 400 t/km2 = 40,000 t straw
    assert result.burned_area_km2 == 100.0
    assert result.straw_burnt_tonnes == 40000.0
    assert result.pm25_tonnes == 240.0
    assert result.health_cost_usd == 18000000.0
    assert result.co2_eq_tonnes > result.pm25_tonnes
    assert result.carbon_credit_usd > 0


def test_properties():
    result = calculate_emissions(burned_area_km2=250.0, cfg=_cfg())
    assert result.health_cost_usd_bn == result.health_cost_usd / 1e9
    assert result.co2_eq_million_tonnes == result.co2_eq_tonnes / 1e6
    assert result.straw_million_tonnes == result.straw_burnt_tonnes / 1e6


def test_all_pollutants_shape():
    result = calculate_emissions(burned_area_km2=100.0, cfg=_cfg())
    for pollutant in ["PM2.5", "CO2", "CO", "CH4", "NOx", "BC", "N2O"]:
        assert pollutant in result.all_pollutants
        assert "tonnes" in result.all_pollutants[pollutant]
        assert "unit" in result.all_pollutants[pollutant]


if __name__ == "__main__":
    test_calculate_emissions_basic()
    test_properties()
    test_all_pollutants_shape()
    print("All emission tests passed.")
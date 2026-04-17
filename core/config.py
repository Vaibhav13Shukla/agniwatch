"""
AGNIWATCH Configuration System
Agricultural Fire & Air Quality Intelligence Platform
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import yaml
import os


@dataclass
class RegionConfig:
    """
    Everything needed to run AGNIWATCH over any farming region.
    Change these values — zero code changes required.
    """
    name: str
    bounds: List[float]  # [W, S, E, N]
    country: str
    crop: str
    pre_start: str  # 'MM-DD'
    pre_end: str
    post_start: str
    post_end: str
    sub_regions: Dict[str, List[float]] = field(default_factory=dict)
    alert_email: Optional[str] = None
    language: str = 'en'

    # Thresholds
    s2_cloud_pct: int = 35
    burn_threshold_any: float = 0.10
    burn_threshold_moderate: float = 0.27
    firms_temp_k: int = 320
    alert_fire_km2: float = 50.0
    alert_no2_pct: float = 30.0

    # Emission factors (Andreae 2019 + IPCC 2006)
    straw_yield_t_per_km2: float = 400.0
    pm25_g_per_kg: float = 6.0
    co2_g_per_kg: float = 1515.0
    ch4_g_per_kg: float = 2.7
    co_g_per_kg: float = 92.0
    health_cost_usd_per_t_pm25: float = 75000.0

    # Scale
    scale_s2: int = 100
    scale_modis: int = 1000
    scale_s5p: int = 5500
    max_retries: int = 3
    retry_delay: int = 5


# Built-in region library
BUILTIN_REGIONS: Dict[str, RegionConfig] = {

    "Punjab & Haryana, India": RegionConfig(
        name="Punjab & Haryana, India",
        bounds=[73.5, 29.5, 77.5, 32.5],
        country="IN",
        crop="Rice (Kharif)",
        pre_start="09-01",
        pre_end="09-30",
        post_start="10-15",
        post_end="11-30",
        sub_regions={
            "Amritsar": [74.5, 31.3, 75.4, 32.2],
            "Ludhiana": [75.5, 30.5, 76.3, 31.2],
            "Patiala": [76.0, 29.9, 76.8, 30.8],
            "Hisar": [75.3, 29.0, 76.2, 29.8],
            "Rohtak": [76.3, 28.6, 77.0, 29.2],
        },
        alert_email="ppcb@punjab.gov.in",
    ),

    "Maharashtra, India": RegionConfig(
        name="Maharashtra, India",
        bounds=[72.6, 15.6, 80.9, 22.0],
        country="IN",
        crop="Sugarcane",
        pre_start="09-01",
        pre_end="10-31",
        post_start="11-01",
        post_end="03-31",
        sub_regions={
            "Pune": [73.5, 17.8, 74.5, 18.8],
            "Nashik": [73.5, 19.5, 74.5, 20.5],
            "Kolhapur": [73.8, 16.3, 74.5, 17.0],
        },
    ),

    "Central Thailand": RegionConfig(
        name="Central Thailand",
        bounds=[98.0, 13.0, 105.0, 20.0],
        country="TH",
        crop="Rice / Sugarcane",
        pre_start="12-01",
        pre_end="12-31",
        post_start="01-15",
        post_end="04-30",
        sub_regions={
            "Chiang Mai": [98.8, 18.4, 99.3, 19.0],
            "Chiang Rai": [99.5, 19.5, 100.5, 20.5],
        },
        s2_cloud_pct=50,
    ),

    "Custom Region": RegionConfig(
        name="Custom Region",
        bounds=[0.0, 0.0, 1.0, 1.0],
        country="XX",
        crop="Unknown",
        pre_start="09-01",
        pre_end="09-30",
        post_start="10-01",
        post_end="11-30",
    ),
}


def load_region_from_yaml(path: str) -> RegionConfig:
    """Load a region config from a YAML file."""
    with open(path) as f:
        data = yaml.safe_load(f)

    # Backward compatibility: allow sub_regions as list of
    # {name: str, bounds: [W,S,E,N]} records.
    sub_regions = data.get("sub_regions")
    if isinstance(sub_regions, list):
        mapped = {}
        for item in sub_regions:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            bounds = item.get("bounds")
            if name and isinstance(bounds, list) and len(bounds) == 4:
                mapped[name] = bounds
        data["sub_regions"] = mapped

    return RegionConfig(**data)


def load_all_yaml_regions(regions_dir: str = "regions") -> Dict[str, RegionConfig]:
    """Scan regions/ directory and load all YAML configs."""
    regions = {}
    if not os.path.exists(regions_dir):
        return regions
    for fname in os.listdir(regions_dir):
        if fname.endswith('.yaml') and fname != 'template.yaml':
            path = os.path.join(regions_dir, fname)
            try:
                rc = load_region_from_yaml(path)
                regions[rc.name] = rc
            except Exception as e:
                print(f"Warning: could not load {fname}: {e}")
    return regions


def get_all_regions() -> Dict[str, RegionConfig]:
    """Return built-in + YAML regions merged."""
    all_regions = dict(BUILTIN_REGIONS)
    all_regions.update(load_all_yaml_regions())
    return all_regions


# Global emission factor reference table
EMISSION_FACTORS = {
    "PM2.5": {"value": 6.0, "unit": "g/kg", "source": "Andreae 2019"},
    "PM10": {"value": 8.3, "unit": "g/kg", "source": "Andreae 2019"},
    "CO": {"value": 92.0, "unit": "g/kg", "source": "Andreae 2019"},
    "CO2": {"value": 1515.0, "unit": "g/kg", "source": "IPCC 2006"},
    "CH4": {"value": 2.7, "unit": "g/kg", "source": "Andreae 2019"},
    "NOx": {"value": 3.9, "unit": "g/kg", "source": "Andreae 2019"},
    "BC": {"value": 0.37, "unit": "g/kg", "source": "Andreae 2019"},
    "N2O": {"value": 0.07, "unit": "g/kg", "source": "IPCC 2006"},
}

SEVERITY_META = {
    0: {"label": "Enhanced Regrowth", "color": "#00c800", "range": "dNBR < -0.1"},
    1: {"label": "Unburned", "color": "#c8c8c8", "range": "-0.1 ≤ dNBR < 0.1"},
    2: {"label": "Low Severity", "color": "#ffff00", "range": "0.1 ≤ dNBR < 0.27"},
    3: {"label": "Moderate-Low", "color": "#ff8c00", "range": "0.27 ≤ dNBR < 0.44"},
    4: {"label": "Moderate-High", "color": "#ff2800", "range": "0.44 ≤ dNBR < 0.66"},
    5: {"label": "High Severity", "color": "#7f0000", "range": "dNBR ≥ 0.66"},
}
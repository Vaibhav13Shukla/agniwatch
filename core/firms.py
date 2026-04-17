"""
MODIS FIRMS active fire detection and multi-year trend analysis.
Correctly uses ImageCollection (not FeatureCollection).
"""

import ee
import pandas as pd
from typing import Dict, Optional
from .config import RegionConfig
from .preprocessing import _safe_get


def get_firms_stats(roi: ee.Geometry, start: str, end: str,
                    temp_k: int = 320) -> Dict:
    """
    Detect active fire pixels from MODIS FIRMS T21 band.
    T21 = brightness temperature at 21µm (MIR channel).
    Pixels ≥ threshold indicate thermal anomaly = active fire.
    Native resolution: 1 km → 1 pixel = 1 km².
    """
    col = (ee.ImageCollection('FIRMS')
              .filterBounds(roi)
              .filterDate(start, end))

    count = _safe_get(col.size(), 'FIRMS count', 0)
    if not count:
        return {
            'fire_pixels': 0,
            'area_km2': 0.0,
            'granules': 0,
            'valid': False,
        }

    fire_max = col.select('T21').max().clip(roi)
    fire_mask = fire_max.gte(temp_k).rename('fire_px')

    px_result = _safe_get(
        fire_mask.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=roi,
            scale=1000,
            maxPixels=1e9
        ),
        'FIRMS pixels', {}
    )

    px = float((px_result or {}).get('fire_px', 0) or 0)
    area = px * 1.0  # 1 km² per pixel at 1km scale

    return {
        'fire_pixels': int(px),
        'area_km2': area,
        'granules': count,
        'valid': True,
        'image': fire_max,
        'mask': fire_mask,
    }


def get_firms_sub_regions(fire_mask: ee.Image, sub_regions: Dict,
                           temp_k: int = 320) -> Dict:
    """Per sub-region FIRMS pixel counts."""
    results = {}
    for name, bounds in sub_regions.items():
        geom = ee.Geometry.Rectangle(bounds)
        res = _safe_get(
            fire_mask.reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=geom,
                scale=1000,
                maxPixels=1e9
            ),
            f"FIRMS {name}", {}
        )
        px = float((res or {}).get('fire_px', 0) or 0)
        results[name] = {'fire_pixels': int(px), 'area_km2': px}
    return results


def get_multi_year_trend(roi: ee.Geometry, years: list,
                         temp_k: int = 320) -> pd.DataFrame:
    """
    Fire area trend across multiple years (Oct–Nov season each year).
    Returns DataFrame with Year, Fire_Pixels, Area_km2, Granules, YoY_pct.
    """
    rows = []
    for year in years:
        start = f'{year}-10-01'
        end = f'{year}-11-30'

        col = (ee.ImageCollection('FIRMS')
                  .filterBounds(roi)
                  .filterDate(start, end))

        granules = _safe_get(col.size(), f"FIRMS {year}", 0)

        if not granules:
            rows.append({'Year': year, 'Fire_Pixels': 0,
                         'Area_km2': 0.0, 'Granules': 0})
            continue

        f_mask = col.select('T21').max().clip(roi).gte(temp_k).rename('fp')
        res = _safe_get(
            f_mask.reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=roi,
                scale=1000,
                maxPixels=1e9
            ),
            f"FIRMS px {year}", {}
        )
        px = float((res or {}).get('fp', 0) or 0)
        rows.append({
            'Year': year,
            'Fire_Pixels': int(px),
            'Area_km2': px,
            'Granules': granules,
        })

    df = pd.DataFrame(rows)
    if len(df) > 1:
        df['YoY_pct'] = df['Area_km2'].pct_change() * 100
        baseline = df[df['Year'] == df['Year'].min()]['Area_km2'].values[0]
        df['vs_baseline_pct'] = (df['Area_km2'] - baseline) / max(baseline, 1) * 100
    return df
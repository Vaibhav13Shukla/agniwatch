"""
Sentinel-5P TROPOMI retrieval for NO₂ and CO columns.
Supports pre/post comparison and monthly time series.
"""

import ee
import pandas as pd
from typing import Optional, Dict
from .preprocessing import _safe_get


S5P_PRODUCTS = {
    'NO2': {
        'collection': 'COPERNICUS/S5P/NRTI/L3_NO2',
        'band': 'tropospheric_NO2_column_number_density',
        'scale_factor': 1e6,
        'display_unit': 'µmol/m²',
        'label': 'Tropospheric NO₂',
    },
    'CO': {
        'collection': 'COPERNICUS/S5P/NRTI/L3_CO',
        'band': 'CO_column_number_density',
        'scale_factor': 1000,
        'display_unit': 'mmol/m²',
        'label': 'CO Column',
    },
}


def get_s5p_stats(roi: ee.Geometry, start: str, end: str,
                  scale: int = 5500) -> Dict:
    """
    Retrieve mean ± std for NO₂ and CO over ROI and date range.
    S5P native resolution ~3.5km × 7km → use scale=5500.
    Fill values masked (S5P uses large negative fill sentinel).
    """
    results = {}
    for pol, cfg in S5P_PRODUCTS.items():
        col = (ee.ImageCollection(cfg['collection'])
                  .filterBounds(roi)
                  .filterDate(start, end)
                  .select(cfg['band'])
                  .map(lambda img: img.updateMask(img.gt(-1e29))))

        count = _safe_get(col.size(), f"S5P {pol} count", 0)

        if not count:
            results[pol] = {
                'mean': None, 'std': None, 'count': 0,
                'mean_display': None, 'display_unit': cfg['display_unit'],
            }
            continue

        stats = _safe_get(
            col.mean().reduceRegion(
                reducer=ee.Reducer.mean().combine(
                    ee.Reducer.stdDev(), '', True),
                geometry=roi,
                scale=scale,
                maxPixels=1e9
            ),
            f"S5P {pol} stats", {}
        )
        band = cfg['band']
        mean = (stats or {}).get(f'{band}_mean')
        std = (stats or {}).get(f'{band}_stdDev')
        sf = cfg['scale_factor']

        results[pol] = {
            'mean': mean,
            'std': std,
            'count': count,
            'mean_display': mean * sf if mean else None,
            'std_display': std * sf if std else None,
            'display_unit': cfg['display_unit'],
            'label': cfg['label'],
        }

    return results


def get_monthly_series(roi: ee.Geometry, windows: list,
                       scale: int = 5500) -> pd.DataFrame:
    """
    Retrieve monthly NO₂ and CO for a list of date windows.
    windows: list of (label, start, end) tuples
    Returns wide DataFrame with columns for each pollutant.
    """
    rows = []
    for label, start, end in windows:
        stats = get_s5p_stats(roi, start, end, scale)
        row = {'Period': label, 'Start': start}
        for pol, data in stats.items():
            sf = S5P_PRODUCTS[pol]['scale_factor']
            row[f'{pol}_mean'] = data['mean']
            row[f'{pol}_display'] = data['mean_display']
            row[f'{pol}_std'] = data['std_display'] or 0
            row[f'{pol}_unit'] = data['display_unit']
            row[f'{pol}_count'] = data['count']
        rows.append(row)

    return pd.DataFrame(rows)
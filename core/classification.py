"""
Burn severity classification using Key & Benson 2006 USGS protocol.
6-class scheme applied to dNBR. Water and non-cropland excluded.
"""

import ee
from .config import SEVERITY_META, RegionConfig
from .preprocessing import _safe_get


def classify_burn_severity(dnbr: ee.Image) -> ee.Image:
    """
    6-class burn severity from dNBR using BINARY SUM method.
    Each binary mask selects one class value — sum gives the class label.
    NOT chained .where() which overwrites classes.

    Classes (Key & Benson 2006):
        0 = Enhanced Regrowth  (dNBR < -0.1)
        1 = Unburned           (-0.1 ≤ dNBR < 0.1)
        2 = Low Severity       (0.1  ≤ dNBR < 0.27)
        3 = Moderate-Low       (0.27 ≤ dNBR < 0.44)
        4 = Moderate-High      (0.44 ≤ dNBR < 0.66)
        5 = High Severity      (dNBR ≥ 0.66)
    """
    c0 = dnbr.lt(-0.10).multiply(0)
    c1 = dnbr.gte(-0.10).And(dnbr.lt(0.10)).multiply(1)
    c2 = dnbr.gte(0.10).And(dnbr.lt(0.27)).multiply(2)
    c3 = dnbr.gte(0.27).And(dnbr.lt(0.44)).multiply(3)
    c4 = dnbr.gte(0.44).And(dnbr.lt(0.66)).multiply(4)
    c5 = dnbr.gte(0.66).multiply(5)

    return (c0.add(c1).add(c2).add(c3).add(c4).add(c5)
              .rename('burn_severity')
              .toByte()
              .updateMask(dnbr.mask()))


def apply_masks(dnbr: ee.Image, severity: ee.Image,
               ndwi_pre: ee.Image, cropland_mask: ee.Image) -> tuple:
    """
    Apply water body + cropland masks.
    - Water: NDWI >= 0 → water pixel → exclude
    - Cropland: only classify agricultural land as burned
    Returns: (dnbr_masked, severity_masked)
    """
    valid_mask = ndwi_pre.lt(0).And(cropland_mask)
    return (dnbr.updateMask(valid_mask),
            severity.updateMask(valid_mask))


def count_pixels(image: ee.Image, band: str, geom: ee.Geometry,
                 scale: int, desc: str = '') -> float:
    """Count non-zero pixels in a binary mask image."""
    result = _safe_get(
        image.rename(band).reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=geom,
            scale=scale,
            maxPixels=1e10
        ),
        desc, {}
    )
    return float((result or {}).get(band, 0) or 0)


def compute_area_stats(dnbr_masked: ee.Image, severity_masked: ee.Image,
                       roi: ee.Geometry, cfg: RegionConfig) -> dict:
    """
    Compute burned area and severity distribution.
    Returns: area_any_km2, area_moderate_km2, severity_dist, sub_regions
    """
    scale = cfg.scale_s2
    pix_km2 = (scale ** 2) / 1e6

    px_any = count_pixels(
        dnbr_masked.gte(cfg.burn_threshold_any),
        'b', roi, scale, 'burned any'
    )
    px_mod = count_pixels(
        dnbr_masked.gte(cfg.burn_threshold_moderate),
        'b', roi, scale, 'burned moderate'
    )

    area_any = px_any * pix_km2
    area_mod = px_mod * pix_km2

    # Per-class distribution
    severity_dist = {}
    for cls_val, meta in SEVERITY_META.items():
        px = count_pixels(
            severity_masked.eq(cls_val),
            'b', roi, scale,
            f"severity {cls_val}"
        )
        severity_dist[cls_val] = {
            **meta,
            'pixels': int(px),
            'area_km2': px * pix_km2,
        }

    # Per sub-region breakdown
    sub_region_results = {}
    for name, bounds in cfg.sub_regions.items():
        geom = ee.Geometry.Rectangle(bounds)
        px_sr = count_pixels(
            dnbr_masked.gte(cfg.burn_threshold_any),
            'b', geom, scale, f"sub {name}"
        )
        area_sr = px_sr * pix_km2
        alert = area_sr >= cfg.alert_fire_km2
        sub_region_results[name] = {
            'area_km2': area_sr,
            'alert': alert,
        }

    return {
        'area_any_km2': area_any,
        'area_moderate_km2': area_mod,
        'severity_dist': severity_dist,
        'sub_regions': sub_region_results,
        'scale_m': scale,
        'pixel_area_km2': pix_km2,
    }
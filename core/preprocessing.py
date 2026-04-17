"""
Sentinel-2 SR cloud + shadow masking and compositing.
Dual-method QA60+SCL cloud masking with progressive threshold fallback.
"""

import ee
import time
from typing import Tuple, Optional
from .config import RegionConfig


def mask_s2_clouds_shadows(image: ee.Image) -> ee.Image:
    """
    Dual-method cloud + shadow masking for Sentinel-2 SR.
    Method 1 — QA60 bitmask: Bit 10 = opaque clouds, Bit 11 = cirrus
    Method 2 — SCL (Scene Classification Layer): classes 3,8,9,10
    Returns surface reflectance scaled to [0, 1].
    """
    qa = image.select('QA60')
    scl = image.select('SCL')

    qa_mask = (qa.bitwiseAnd(1 << 10).eq(0)
               .And(qa.bitwiseAnd(1 << 11).eq(0)))

    scl_mask = (scl.neq(3)
                .And(scl.neq(8))
                .And(scl.neq(9))
                .And(scl.neq(10)))

    optical = ['B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B8A', 'B11', 'B12']

    return (image
            .select(optical)
            .divide(10000)
            .updateMask(qa_mask.And(scl_mask))
            .copyProperties(image, ['system:time_start', 'CLOUDY_PIXEL_PERCENTAGE']))


def get_s2_composite(
    roi: ee.Geometry,
    start: str,
    end: str,
    cfg: RegionConfig,
    label: str = '',
    progress_fn=None,
) -> Tuple[Optional[ee.Image], int]:
    """
    Load, filter, mask, and median-composite Sentinel-2 SR.
    Progressive fallback: relaxes cloud threshold if too few images.
    Returns: (composite_image, image_count), (None, 0) if no imagery
    """
    thresholds = [cfg.s2_cloud_pct,
                  min(cfg.s2_cloud_pct + 20, 60),
                  80]

    for threshold in thresholds:
        if progress_fn:
            progress_fn(f"Loading S2 {label} (cloud < {threshold}%)...")

        col = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                 .filterBounds(roi)
                 .filterDate(start, end)
                 .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', threshold))
                 .map(mask_s2_clouds_shadows))

        count = _safe_get(col.size(), f"S2 count {label}", 0)

        if count > 0:
            if threshold > cfg.s2_cloud_pct and progress_fn:
                progress_fn(f"⚠️ Relaxed cloud threshold to {threshold}%")
            return col.median().clip(roi), count

    return None, 0


def get_cropland_mask(roi: ee.Geometry, year: int) -> ee.Image:
    """
    MODIS MCD12Q1 cropland mask.
    Classes 12 = Croplands, 14 = Cropland/Natural Vegetation Mosaic
    Restricts burn analysis to agricultural pixels only.
    """
    lc = (ee.ImageCollection('MODIS/061/MCD12Q1')
             .filterDate(f'{year}-01-01', f'{year}-12-31')
             .first()
             .select('LC_Type1'))

    return lc.eq(12).Or(lc.eq(14)).clip(roi)


def _safe_get(ee_obj, desc: str = '', default=None,
              retries: int = 3, delay: int = 5):
    """Retry-wrapped getInfo with descriptive error handling."""
    for attempt in range(retries):
        try:
            return ee_obj.getInfo()
        except ee.EEException as e:
            err = str(e)
            if any(k in err for k in ['Too many pixels',
                                       'memory capacity exceeded']):
                return default
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                return default
    return default
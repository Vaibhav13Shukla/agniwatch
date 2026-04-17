"""
Spectral indices for burn detection.
All functions operate on Sentinel-2 SR images scaled to [0,1].
"""

import ee


def compute_nbr(image: ee.Image) -> ee.Image:
    """
    Normalized Burn Ratio: (NIR - SWIR2) / (NIR + SWIR2)
    Sentinel-2: NIR=B8 (842nm), SWIR2=B12 (2190nm)
    High NBR = healthy vegetation. Low/negative = burned.
    """
    return (image.normalizedDifference(['B8', 'B12'])
                 .rename('NBR').toFloat())


def compute_ndvi(image: ee.Image) -> ee.Image:
    """
    NDVI: (NIR - Red) / (NIR + Red)
    Sentinel-2: NIR=B8, Red=B4
    """
    return (image.normalizedDifference(['B8', 'B4'])
                 .rename('NDVI').toFloat())


def compute_ndwi(image: ee.Image) -> ee.Image:
    """
    NDWI: (Green - NIR) / (Green + NIR)
    Positive NDWI = water. Used to mask water bodies.
    """
    return (image.normalizedDifference(['B3', 'B8'])
                 .rename('NDWI').toFloat())


def compute_bai(image: ee.Image) -> ee.Image:
    """
    Burn Area Index (Chuvieco et al. 2002)
    BAI = 1 / ((0.1 - Red)² + (0.06 - NIR)²)
    """
    red = image.select('B4')
    nir = image.select('B8')
    return (ee.Image(1)
            .divide(
                (ee.Image(0.1).subtract(red)).pow(2)
                .add((ee.Image(0.06).subtract(nir)).pow(2))
            )
            .rename('BAI').toFloat())


def compute_dnbr(nbr_pre: ee.Image, nbr_post: ee.Image) -> ee.Image:
    """
    dNBR = NBR_pre - NBR_post (Key & Benson 2006)
    Positive = burned. Negative = enhanced regrowth.
    Sign convention: pre MINUS post so burned = positive.
    """
    return nbr_pre.subtract(nbr_post).rename('dNBR').toFloat()


def compute_rdnbr(dnbr: ee.Image, nbr_pre: ee.Image) -> ee.Image:
    """
    Relative dNBR: dNBR / sqrt(|NBR_pre|)
    More robust than dNBR for cropland (low pre-fire vegetation).
    Small epsilon avoids division by zero.
    """
    return (dnbr
            .divide(nbr_pre.abs().sqrt().add(1e-6))
            .rename('RdNBR').toFloat())


def compute_all_indices(pre: ee.Image, post: ee.Image) -> dict:
    """
    Compute complete index suite from pre/post composites.
    Returns dict with all computed images.
    """
    nbr_pre = compute_nbr(pre)
    nbr_post = compute_nbr(post)
    ndvi_pre = compute_ndvi(pre)
    ndvi_post = compute_ndvi(post)
    ndwi_pre = compute_ndwi(pre)
    dnbr = compute_dnbr(nbr_pre, nbr_post)
    rdnbr = compute_rdnbr(dnbr, nbr_pre)
    bai = compute_bai(post)
    ndvi_diff = ndvi_pre.subtract(ndvi_post).rename('NDVI_diff').toFloat()

    return {
        'nbr_pre': nbr_pre,
        'nbr_post': nbr_post,
        'ndvi_pre': ndvi_pre,
        'ndvi_post': ndvi_post,
        'ndwi_pre': ndwi_pre,
        'ndvi_diff': ndvi_diff,
        'dnbr': dnbr,
        'rdnbr': rdnbr,
        'bai': bai,
    }
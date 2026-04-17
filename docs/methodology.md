# AGNIWATCH Technical Methodology

This document describes the scientific and engineering methods used in AGNIWATCH for wildfire and agricultural burning detection, classification, and impact assessment.

---

## 1. Sentinel-2 Cloud Masking (QA60 + SCL Dual Method)

### QA60 Bit Index

Sentinel-2 Level-1C products include a Quality Assurance (QA60) band encoding cloud and vegetation/probability flags:

| Bit | Description | Value | Meaning |
|---|---|---|---|
| 10 | Opaque clouds | 0 | Clear sky |
| 10 | Opaque clouds | 1 | Cloudy |
| 11 | Cirrus | 0 | No cirrus |
| 11 | Cirrus | 1 | Cirrus detected |

Pixels where `QA60 bit 10 == 1 OR QA60 bit 11 == 1` are flagged as cloud-contaminated and excluded.

### Scene Classification Map (SCL)

Sentinel-2 L2A products include an SCL band with 11 classes. AGNIWATCH excludes:

| SCL Value | Class | Excluded |
|---|---|---|
| 3 | CLOUD_SHADOWS | Yes |
| 8 | CLOUD_MEDIUM_PROBA | Yes |
| 9 | CLOUD_HIGH_PROBA | Yes |
| 10 | THIN_CIRRUS | Yes |

### Dual-Method Intersection

A pixel is retained only when **both** QA60 and SCL indicate clear-sky conditions.

---

## 2. dNBR Burn Detection Protocol

### Reference: Key & Benson 2006

```
NBR = (NIR - SWIR) / (NIR + SWIR)
dNBR = pre-fire NBR - post-fire NBR
```

Where:
- NIR = Sentinel-2 Band 8A (865 nm)
- SWIR = Sentinel-2 Band 12 (2190 nm)

### Burn Threshold

Pixels with `dNBR >= 0.10` are classified as burned (Key & Benson 2006).

---

## 3. Six-Class Severity Classification

| Class | dNBR Range | Description |
|---|---|---|
| 0 | dNBR < -0.1 | Enhanced regrowth |
| 1 | -0.1 ≤ dNBR < 0.1 | Unburned |
| 2 | 0.1 ≤ dNBR < 0.27 | Low severity |
| 3 | 0.27 ≤ dNBR < 0.44 | Moderate-Low |
| 4 | 0.44 ≤ dNBR < 0.66 | Moderate-High |
| 5 | dNBR ≥ 0.66 | High Severity |

---

## 4. Cropland Masking (MODIS MCD12Q1)

AGNIWATCH includes only IGBP classes 12 (Croplands) and 14 (Cropland/Natural Mosaic).
All other land classes are excluded from burned-area accounting.

---

## 5. MODIS FIRMS Thermal Detection (T21 Threshold)

Thermal anomalies detected when `T21 >= 310 K` using MODIS 4μm mid-infrared band.

---

## 6. Sentinel-5P TROPOMI NO₂ and CO Retrieval

- NO₂: Tropospheric column density at 7×3.5km resolution
- CO: Column density at 7×7km resolution
- Fill values (-1e29) masked

---

## 7. Emission Calculation

### References: IPCC 2006 Vol 4 Ch 2, Andreae 2019

```
Emissions (t) = burned_area_km² × straw_load(t/km²) × emission_factor(g/kg) / 1000
```

### Default Emission Factors

| Species | g/kg DM |
|---|---|
| CO2 | 1515 |
| CO | 92 |
| CH4 | 2.7 |
| PM2.5 | 6.0 |
| NOx | 3.9 |
| BC | 0.37 |

### CO2eq = CO2 + CH4 × 27.9 (IPCC AR6 GWP100)

---

## 8. Health Cost Methodology (WHO VSL)

```
Health Cost = PM2.5_tonnes × HealthCostFactor_USD_per_tonne
```

Default AGNIWATCH factor is 75,000 USD per tonne PM2.5 (region-configurable in `regions/*.yaml`).
This keeps assumptions explicit and auditable for policy adaptation by country.

---

## References

- Key, C.H. & Benson, N.C. (2006). Measuring and Remote Sensing of Fire Effects. USGS Open-File Report 2006-1301.
- Andreae, M.O. (2019). Biomass Burning Emissions. Atmos. Chem. Phys., 19, 8523-8546.
- IPCC (2006). IPCC Guidelines for National Greenhouse Gas Inventories. Volume 4.
- IPCC AR6 (2021). Sixth Assessment Report, WGI.
- WHO (2021). Environmental Health Advice for Europe.
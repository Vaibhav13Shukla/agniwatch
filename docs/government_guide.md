# AGNIWATCH Government User Guide

This guide is for government officials, policymakers, and public servants who use AGNIWATCH for fire monitoring, emergency response, and policy reporting.

---

## 1. How to Interpret Alert Bulletins

### Alert Format

Each AGNIWATCH alert bulletin contains:

| Field | Description |
|---|---|
| Alert Level | GREEN / YELLOW / RED |
| Date/Time | Timestamp of detection (UTC) |
| Region | District and state |
| Burned Area | Area detected in km² (Sentinel-2 + MODIS) |
| Severity | 6-class classification |
| MODIS Gap | Undercount percentage vs official counts |
| Health Cost | WHO VSL-based estimate (USD) |

### Alert Levels

| Level | Trigger | Action |
|---|---|---|
| 🟢 GREEN | No active alerts | Routine monitoring |
| 🟡 YELLOW | ≥1 district alert | Notify district collectors |
| 🔴 RED | ≥3 active alerts | State emergency activation |

---

## 2. District Action Thresholds

### Standard Thresholds

| Threshold | Trigger | Action |
|---|---|---|
| Fire ≥ 50 km² | District burned area | Deploy enforcement team |
| NO₂ increase ≥ 30% | vs pre-harvest baseline | Issue health advisory |
| Any RED alert | Satellite-confirmed fire | Notify district collector |

---

## 3. Using CSV Exports for Reporting

### Export Format

AGNIWATCH CSV exports contain one row per metric:

```csv
Metric, Value
Burned area any burn km2, 103368.3
Burned area moderate+ km2, 69355.6
FIRMS fire area km2, 14169.7
MODIS undercount pct, 85.7
NO2 change pct, 47.9
PM2.5 emitted tonnes, 27765.0
CO2eq emitted million tonnes, 128.5
Health cost USD billion, 2.08
```

### Aggregation

```python
import pandas as pd
df = pd.read_csv('agniwatch_summary.csv')
df.groupby('Metric')['Value'].sum()
```

---

## 4. How to Cite in Policy Documents

### Standard Citation

```
AGNIWATCH (2024). Agricultural Fire & Air Quality Intelligence Platform v3.0.
Open Source, MIT License. https://github.com/agniwatch/agniwatch
Satellite data: ESA Sentinel-2, Sentinel-5P (Copernicus); NASA MODIS FIRMS.
```

### Sample Paragraph

> "According to AGNIWATCH satellite monitoring using ESA Sentinel-2 data,
> a total of 103,368 km² of agricultural land was affected by open burning
> during the 2023 post-harvest season. This is 7.3× more than indicated by
> official MODIS-based counts (14,170 km²). Estimated health costs total
> USD 2.08 billion using WHO VSL methodology."

---

## 5. Integration with Existing Systems

### GeoJSON Endpoints

```bash
GET https://your-streamlit-app.com/api/alerts?region=DISTRICT&format=geojson
```

### Compatible Platforms

| Platform | Method |
|---|---|
| QGIS | Add GeoJSON as vector layer |
| ArcGIS | Register as feature service |
| Google Earth Engine | CSV import, join to admin boundaries |

### Webhook Notifications

Configure SMTP email alerts via Gmail App Password (500/day free tier).

---

## Support

GitHub Issues: https://github.com/agniwatch/agniwatch/issues
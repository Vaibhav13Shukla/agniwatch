"""
Alert bulletin generator.
Outputs structured JSON + human-readable text.
In production: email/SMS/webhook delivery.
"""

import json
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
from .config import RegionConfig
from .emissions import EmissionResult


@dataclass
class AlertBulletin:
    system: str
    version: str
    generated: str
    region: str
    season: str
    alert_level: str  # 'GREEN', 'YELLOW', 'RED'
    alerts: List[Dict]
    burned_area_km2: float
    firms_area_km2: float
    modis_gap_pct: float
    no2_change_pct: Optional[float]
    pm25_tonnes: float
    health_cost_usd_bn: float
    co2eq_mt: float
    districts: Dict
    recommendations: List[str]

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, default=str)

    def to_text(self) -> str:
        return _format_bulletin_text(self)


def generate_bulletin(
    cfg: RegionConfig,
    area_stats: dict,
    firms_stats: dict,
    aq_pre: dict,
    aq_post: dict,
    emissions: EmissionResult,
    year: int,
) -> AlertBulletin:
    """Generate a structured alert bulletin from analysis results."""
    alerts = []

    # Check district fire alerts
    for district, data in area_stats['sub_regions'].items():
        if data['alert']:
            alerts.append({
                'type': 'FIRE_AREA',
                'district': district,
                'value_km2': data['area_km2'],
                'threshold': cfg.alert_fire_km2,
                'action': 'Deploy enforcement team immediately',
            })

    # Check NO₂ air quality alert
    no2_pct = None
    no2_pre_v = aq_pre.get('NO2', {}).get('mean')
    no2_post_v = aq_post.get('NO2', {}).get('mean')
    if no2_pre_v and no2_post_v and no2_pre_v > 0:
        no2_pct = (no2_post_v - no2_pre_v) / no2_pre_v * 100
        if no2_pct > cfg.alert_no2_pct:
            alerts.append({
                'type': 'AIR_QUALITY',
                'pollutant': 'NO2',
                'value_pct': round(no2_pct, 1),
                'threshold': cfg.alert_no2_pct,
                'action': 'Issue public health advisory',
            })

    # Alert level
    n_alerts = len(alerts)
    level = 'RED' if n_alerts >= 3 else ('YELLOW' if n_alerts >= 1 else 'GREEN')

    # MODIS gap
    s2_area = area_stats['area_any_km2']
    firms_area = firms_stats['area_km2']
    gap_pct = ((s2_area - firms_area) / max(s2_area, 1) * 100
               if s2_area > 0 else 0)

    recommendations = _get_recommendations(alerts, level, cfg)

    return AlertBulletin(
        system='AGNIWATCH',
        version='3.0',
        generated=datetime.utcnow().isoformat() + 'Z',
        region=cfg.name,
        season=f"{year}-{cfg.post_start} → {year}-{cfg.post_end}",
        alert_level=level,
        alerts=alerts,
        burned_area_km2=s2_area,
        firms_area_km2=firms_area,
        modis_gap_pct=round(gap_pct, 1),
        no2_change_pct=round(no2_pct, 1) if no2_pct else None,
        pm25_tonnes=emissions.pm25_tonnes,
        health_cost_usd_bn=emissions.health_cost_usd_bn,
        co2eq_mt=emissions.co2_eq_million_tonnes,
        districts=area_stats['sub_regions'],
        recommendations=recommendations,
    )


def _get_recommendations(alerts, level, cfg):
    recs = []
    if level in ('RED', 'YELLOW'):
        recs += [
            "Issue public health advisory for sensitive groups (children, elderly, asthmatics)",
            "Notify district collectors of satellite-confirmed fire activity",
        ]
    if any(a['type'] == 'FIRE_AREA' for a in alerts):
        recs += [
            "Deploy PPCB/pollution board enforcement teams to flagged districts",
            "Activate Happy Seeder / bio-decomposer subsidy disbursement",
        ]
    if any(a['type'] == 'AIR_QUALITY' for a in alerts):
        recs += [
            "Alert hospitals to expect increased respiratory admissions",
            "Recommend N95 mask use in affected districts",
        ]
    recs += [
        "Log this bulletin to district compliance register",
        "Schedule follow-up satellite pass in 5 days",
    ]
    return recs


def _format_bulletin_text(b: AlertBulletin) -> str:
    alert_icon = {'RED': '🔴', 'YELLOW': '🟡', 'GREEN': '🟢'}.get(
        b.alert_level, '⚪')
    lines = [
        "=" * 68,
        f"  {alert_icon} AGNIWATCH ALERT BULLETIN — {b.alert_level}",
        f"  Region  : {b.region}",
        f"  Season  : {b.season}",
        f"  Generated: {b.generated}",
        "=" * 68,
        "",
        "KEY FINDINGS:",
        f"  Burned area (Sentinel-2) : {b.burned_area_km2:>10,.0f} km²",
        f"  Burned area (MODIS)      : {b.firms_area_km2:>10,.0f} km²",
        f"  MODIS undercount         : {b.modis_gap_pct:>10.0f}%",
    ]
    if b.no2_change_pct:
        lines.append(f"  NO₂ change               : {b.no2_change_pct:>+10.1f}%")
    lines += [
        f"  PM2.5 emitted            : {b.pm25_tonnes:>10,.0f} t",
        f"  Health cost estimate     : USD {b.health_cost_usd_bn:>6.2f} billion",
        f"  CO₂eq emitted            : {b.co2eq_mt:>10.2f} Mt",
        "",
        "DISTRICT STATUS:",
    ]
    for d, v in b.districts.items():
        flag = "🚨 ALERT" if v['alert'] else "✅ OK"
        lines.append(f"  {d:<18}: {v['area_km2']:>8,.0f} km²  {flag}")
    lines += ["", "RECOMMENDED ACTIONS:"]
    for i, r in enumerate(b.recommendations, 1):
        lines.append(f"  {i}. {r}")
    lines += ["", "=" * 68]
    return "\n".join(lines)


def send_email_alert(bulletin: AlertBulletin, smtp_user: str,
                     smtp_pass: str, to_email: str) -> bool:
    """
    Send alert bulletin via Gmail SMTP (free, 500/day limit).
    Use Gmail App Password (not account password).
    """
    try:
        msg = MIMEText(bulletin.to_text())
        msg['Subject'] = (
            f"[AGNIWATCH {bulletin.alert_level}] "
            f"{bulletin.region} — {bulletin.generated[:10]}"
        )
        msg['From'] = smtp_user
        msg['To'] = to_email

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Email failed: {e}")
        return False
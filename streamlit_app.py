"""AGNIWATCH Streamlit dashboard entry point."""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import date, datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

sys.path.insert(0, os.path.dirname(__file__))

logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO").upper())
logger = logging.getLogger("agniwatch")

try:
    import ee

    from core.airquality import get_monthly_series, get_s5p_stats
    from core.alerting import generate_bulletin
    from core.classification import apply_masks, classify_burn_severity, compute_area_stats
    from core.config import RegionConfig, get_all_regions
    from core.emissions import calculate_emissions
    from core.firms import get_firms_stats, get_multi_year_trend
    from core.gee_auth import initialize_gee
    from core.indices import compute_all_indices
    from core.preprocessing import get_cropland_mask, get_s2_composite

    CORE_AVAILABLE = True
except ImportError as exc:
    logger.warning("Core imports unavailable: %s", exc)
    CORE_AVAILABLE = False


st.set_page_config(
    page_title="AGNIWATCH - Fire Intelligence",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
:root {
  --bg: #f4efe3;
  --panel: #fdfaf1;
  --ink: #1c1a18;
  --muted: #5f5952;
  --accent: #c34a23;
  --accent-2: #386641;
  --line: #d4c8ad;
}

[data-testid="stAppViewContainer"] {
  background: radial-gradient(1200px 500px at 10% -20%, #ffe9c6 0%, rgba(255,233,198,0) 60%),
              radial-gradient(1000px 500px at 120% 20%, #f6d5bf 0%, rgba(246,213,191,0) 55%),
              var(--bg);
}

[data-testid="stSidebar"] {
  background: #efe6d3;
  border-right: 1px solid var(--line);
}

h1, h2, h3, h4 {
  color: var(--ink);
  letter-spacing: 0.01em;
}

p, li, label, span, div {
  color: var(--ink);
}

[data-testid="stMetric"] {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 0.8rem;
  padding: 0.6rem 0.8rem;
}

[data-testid="stMetricLabel"] {
  color: var(--muted) !important;
}

[data-testid="stMetricValue"] {
  color: var(--accent) !important;
}

.agni-banner {
  border: 1px solid var(--line);
  border-left: 8px solid var(--accent);
  background: linear-gradient(120deg, #fef9ef, #fff4e7);
  border-radius: 1rem;
  padding: 1rem 1.2rem;
}

.agni-caption {
  color: var(--muted);
  margin-top: 0.15rem;
  font-size: 0.95rem;
}

.small-note {
  color: var(--muted);
  font-size: 0.86rem;
}

.stButton > button {
  min-height: 2.8rem;
  background: var(--accent);
  color: #fff;
  border: 0;
  border-radius: 0.6rem;
  font-weight: 700;
}

.stButton > button:hover {
  background: #a73d1b;
}

@media (min-width: 768px) {
  .agni-banner {
    padding: 1.3rem 1.5rem;
  }
}
</style>
""",
    unsafe_allow_html=True,
)


DEMO_DATA = {
    "region": "Punjab & Haryana, India",
    "season": "2023-10-15 -> 2023-11-30",
    "area_any_km2": 103368.3,
    "area_mod_km2": 69355.6,
    "firms_area_km2": 14169.7,
    "no2_change_pct": 47.9,
    "co_change_pct": 9.7,
    "pm25_tonnes": 27765.0,
    "co2_eq_mt": 128.5,
    "health_cost_bn": 2.08,
    "alert_level": "RED",
    "fire_trend": {
        "years": [2020, 2021, 2022, 2023, 2024],
        "area_km2": [29881, 33144, 21335, 15284, 7140],
    },
    "severity_dist": {
        0: {"label": "Enhanced Regrowth", "color": "#4CAF50", "area_km2": 5074},
        1: {"label": "Unburned", "color": "#BDBDBD", "area_km2": 38241},
        2: {"label": "Low Severity", "color": "#F4D35E", "area_km2": 34013},
        3: {"label": "Moderate-Low", "color": "#EE964B", "area_km2": 31429},
        4: {"label": "Moderate-High", "color": "#F95738", "area_km2": 31658},
        5: {"label": "High Severity", "color": "#7A1E12", "area_km2": 6269},
    },
    "districts": {
        "Amritsar": {"area_km2": 3240, "alert": True},
        "Ludhiana": {"area_km2": 4180, "alert": True},
        "Patiala": {"area_km2": 2890, "alert": True},
        "Hisar": {"area_km2": 1650, "alert": False},
        "Rohtak": {"area_km2": 820, "alert": False},
    },
    "no2_monthly": {
        "periods": ["Aug 2023", "Sep 2023", "Oct 2023", "Nov 2023", "Dec 2023"],
        "no2": [34.9, 34.4, 42.4, 55.9, 47.7],
        "co": [35.7, 36.0, 35.8, 41.6, 37.8],
        "no2_std": [9.8, 9.9, 15.8, 24.3, 24.0],
        "co_std": [3.7, 4.3, 5.2, 8.2, 5.8],
    },
    "emissions": {
        "PM2.5": 27765,
        "CO": 508840,
        "CO2": 8381015,
        "CH4": 14931,
        "NOx": 21572,
        "BC": 2047,
        "N2O": 387,
    },
}


def _plot_theme(fig: go.Figure) -> None:
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#fffdf7",
        font=dict(color="#1c1a18", size=12),
        margin=dict(t=40, b=20, l=20, r=20),
    )
    fig.update_xaxes(gridcolor="#ece2ce")
    fig.update_yaxes(gridcolor="#ece2ce")


def _render_header(data: dict) -> None:
    st.markdown(
        f"""
<div class="agni-banner">
  <h2 style="margin:0;">AGNIWATCH - {data['alert_level']} ALERT</h2>
  <div class="agni-caption">{data['region']} | {data['season']} | Sentinel-2 + MODIS + Sentinel-5P</div>
</div>
""",
        unsafe_allow_html=True,
    )


def _render_sidebar() -> dict:
    with st.sidebar:
        st.markdown("## AGNIWATCH")
        st.caption("Agricultural Fire Intelligence Platform")

        gee_project = st.text_input(
            "GEE Project ID",
            value=os.environ.get("GEE_PROJECT", ""),
            help="Required for Live Satellite mode.",
            placeholder="my-gee-project-123",
        )

        if CORE_AVAILABLE:
            region_options = list(get_all_regions().keys())
            if "Custom Region" not in region_options:
                region_options.append("Custom Region")
        else:
            region_options = [
                "Punjab & Haryana, India",
                "Maharashtra, India",
                "Central Thailand",
                "Custom Region",
            ]
        selected_region = st.selectbox("Region", region_options)
        years = [datetime.utcnow().year - i for i in range(5)]
        selected_year = st.selectbox("Season Year", years, index=1 if len(years) > 1 else 0)

        custom_bounds = None
        if selected_region == "Custom Region":
            st.markdown("Custom bounds [W, S, E, N]")
            c1, c2 = st.columns(2)
            with c1:
                west = st.number_input("West", value=73.5, step=0.5)
                south = st.number_input("South", value=29.5, step=0.5)
            with c2:
                east = st.number_input("East", value=77.5, step=0.5)
                north = st.number_input("North", value=32.5, step=0.5)
            custom_bounds = [west, south, east, north]
            bounds_valid = (
                -180 <= west <= 180
                and -180 <= east <= 180
                and -90 <= south <= 90
                and -90 <= north <= 90
                and west < east
                and south < north
            )
            if not bounds_valid:
                st.error("Invalid bounds. Ensure W < E, S < N, and coordinates are within valid latitude/longitude ranges.")

        mode = st.radio("Mode", ["Demo (instant)", "Live Satellite (GEE)"], index=0)
        alert_email = st.text_input("Alert Email (optional)", placeholder="district@gov.in")
        run_analysis = st.button("Run Analysis", use_container_width=True, type="primary")

        st.markdown("---")
        st.markdown(
            """
- Open in Colab: https://colab.research.google.com
- Docs: https://github.com/agniwatch/agniwatch/tree/main/docs
- License: MIT
"""
        )

    return {
        "gee_project": gee_project,
        "selected_region": selected_region,
        "selected_year": selected_year,
        "custom_bounds": custom_bounds,
        "mode": mode,
        "alert_email": alert_email,
        "run_analysis": run_analysis,
    }


def _render_kpis(data: dict) -> None:
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    s2 = data["area_any_km2"]
    firms = data["firms_area_km2"]
    gap = (s2 - firms) / max(s2, 1) * 100

    c1.metric("Burned Area (S2)", f"{s2/1000:.1f}k km2")
    c2.metric("FIRMS Fire Area", f"{firms/1000:.1f}k km2", delta=f"Undercount {gap:.0f}%")
    c3.metric("NO2 Increase", f"+{data['no2_change_pct']:.1f}%")
    c4.metric("Health Cost", f"${data['health_cost_bn']:.2f}B")
    c5.metric("PM2.5", f"{data['pm25_tonnes']/1000:.1f} kt")
    c6.metric("CO2eq", f"{data['co2_eq_mt']:.1f} Mt")


def _render_analysis_tab(data: dict) -> None:
    cl, cr = st.columns(2)

    with cl:
        trend = data["fire_trend"]
        fig = go.Figure(
            data=[
                go.Bar(
                    x=trend["years"],
                    y=trend["area_km2"],
                    marker_color=["#c34a23" if y == 2023 else "#9b8f7a" for y in trend["years"]],
                )
            ]
        )
        fig.update_layout(title="Fire area trend")
        _plot_theme(fig)
        st.plotly_chart(fig, use_container_width=True)

    with cr:
        sev = data["severity_dist"]
        labels = [v["label"] for k, v in sev.items() if k != 1 and v["area_km2"] > 0]
        values = [v["area_km2"] for k, v in sev.items() if k != 1 and v["area_km2"] > 0]
        colors = [v["color"] for k, v in sev.items() if k != 1 and v["area_km2"] > 0]
        fig = go.Figure(
            go.Pie(labels=labels, values=values, marker_colors=colors, hole=0.42, textinfo="percent+label")
        )
        fig.update_layout(title="Burn severity distribution")
        _plot_theme(fig)
        st.plotly_chart(fig, use_container_width=True)

    aq = data["no2_monthly"]
    fig_aq = make_subplots(rows=1, cols=2, subplot_titles=("NO2", "CO"))
    fig_aq.add_trace(
        go.Scatter(x=aq["periods"], y=aq["no2"], mode="lines+markers", error_y=dict(type="data", array=aq["no2_std"])),
        row=1,
        col=1,
    )
    fig_aq.add_trace(
        go.Scatter(x=aq["periods"], y=aq["co"], mode="lines+markers", error_y=dict(type="data", array=aq["co_std"])),
        row=1,
        col=2,
    )
    fig_aq.update_layout(title="Monthly air quality trend")
    _plot_theme(fig_aq)
    st.plotly_chart(fig_aq, use_container_width=True)


def _render_map_tab(data: dict) -> None:
    st.info("Live tile map requires GEE auth. This view shows district alert summary.")
    rows = [
        {"District": d, "Area_km2": v["area_km2"], "Alert": v["alert"]}
        for d, v in data["districts"].items()
    ]
    df = pd.DataFrame(rows)
    fig = go.Figure(
        go.Bar(
            x=df["District"],
            y=df["Area_km2"],
            marker_color=["#d62828" if a else "#386641" for a in df["Alert"]],
        )
    )
    fig.update_layout(title="District fire burden")
    _plot_theme(fig)
    st.plotly_chart(fig, use_container_width=True)


def _render_alert_tab(data: dict) -> None:
    st.markdown("### Alert Bulletin")
    findings = pd.DataFrame(
        [
            ["Burned area (S2)", f"{data['area_any_km2']:,.0f} km2"],
            ["Burned area (FIRMS)", f"{data['firms_area_km2']:,.0f} km2"],
            ["NO2 change", f"+{data['no2_change_pct']:.1f}%"],
            ["PM2.5 emitted", f"{data['pm25_tonnes']:,.0f} t"],
            ["Health cost", f"USD {data['health_cost_bn']:.2f} bn"],
        ],
        columns=["Metric", "Value"],
    )
    st.dataframe(findings, use_container_width=True, hide_index=True)

    bulletin_json = {
        "system": "AGNIWATCH",
        "version": "3.0",
        "generated": datetime.utcnow().isoformat() + "Z",
        "region": data["region"],
        "alert_level": data["alert_level"],
        "districts": data["districts"],
    }
    st.download_button(
        "Download alert JSON",
        data=json.dumps(bulletin_json, indent=2),
        file_name=f"agniwatch_alert_{date.today()}.json",
        mime="application/json",
        use_container_width=True,
    )


def _render_impact_tab(data: dict) -> None:
    c1, c2, c3 = st.columns(3)
    c1.metric("Health cost", f"${data['health_cost_bn']:.2f}B")
    c2.metric("CO2eq", f"{data['co2_eq_mt']:.1f} Mt")
    c3.metric("Carbon credit", f"${data['co2_eq_mt'] * 15:.0f}M")

    em = data["emissions"]
    fig = go.Figure(go.Bar(x=list(em.keys()), y=[v / 1000 for v in em.values()]))
    fig.update_layout(title="Pollutants (kilotonnes)")
    _plot_theme(fig)
    st.plotly_chart(fig, use_container_width=True)


def _render_export_tab(data: dict) -> None:
    trend_df = pd.DataFrame({"Year": data["fire_trend"]["years"], "Area_km2": data["fire_trend"]["area_km2"]})
    trend_df["YoY_pct"] = trend_df["Area_km2"].pct_change() * 100

    summary_df = pd.DataFrame(
        [
            ["Burned Area Any", data["area_any_km2"]],
            ["Burned Area Moderate+", data["area_mod_km2"]],
            ["FIRMS Area", data["firms_area_km2"]],
            ["NO2 Change pct", data["no2_change_pct"]],
            ["CO Change pct", data["co_change_pct"]],
            ["PM2.5 Tonnes", data["pm25_tonnes"]],
            ["CO2eq Mt", data["co2_eq_mt"]],
            ["Health Cost USD bn", data["health_cost_bn"]],
        ],
        columns=["Metric", "Value"],
    )

    st.download_button(
        "Download summary CSV",
        data=summary_df.to_csv(index=False),
        file_name=f"agniwatch_summary_{date.today()}.csv",
        mime="text/csv",
        use_container_width=True,
    )
    st.download_button(
        "Download trend CSV",
        data=trend_df.to_csv(index=False),
        file_name=f"agniwatch_fire_trend_{date.today()}.csv",
        mime="text/csv",
        use_container_width=True,
    )


@st.cache_data(show_spinner=False)
def _run_live_analysis(sidebar: dict) -> dict:
    if not CORE_AVAILABLE:
        raise RuntimeError("Core modules unavailable")

    if not initialize_gee(sidebar["gee_project"]):
        raise RuntimeError("GEE authentication failed")

    regions = get_all_regions()
    region_name = sidebar["selected_region"]

    if region_name == "Custom Region" or region_name not in regions:
        custom_bounds = sidebar.get("custom_bounds") or [73.5, 29.5, 77.5, 32.5]
        west, south, east, north = custom_bounds
        if not (
            -180 <= west <= 180
            and -180 <= east <= 180
            and -90 <= south <= 90
            and -90 <= north <= 90
            and west < east
            and south < north
        ):
            raise ValueError("Invalid custom bounds. Use [W, S, E, N] with W < E and S < N.")
        cfg = RegionConfig(
            name=region_name,
            bounds=custom_bounds,
            country="XX",
            crop="Unknown",
            pre_start="09-01",
            pre_end="09-30",
            post_start="10-15",
            post_end="11-30",
        )
    else:
        cfg = regions[region_name]

    year = sidebar["selected_year"]
    roi = ee.Geometry.Rectangle(cfg.bounds)

    pre_start = f"{year}-{cfg.pre_start}"
    pre_end = f"{year}-{cfg.pre_end}"
    post_start = f"{year}-{cfg.post_start}"
    post_end = f"{year}-{cfg.post_end}"

    pre, _ = get_s2_composite(roi, pre_start, pre_end, cfg, "Pre")
    post, _ = get_s2_composite(roi, post_start, post_end, cfg, "Post")
    if pre is None or post is None:
        raise RuntimeError("No Sentinel-2 composites available for selected season")

    idx = compute_all_indices(pre, post)
    severity = classify_burn_severity(idx["dnbr"])
    crop_mask = get_cropland_mask(roi, year)
    dnbr_m, sev_m = apply_masks(idx["dnbr"], severity, idx["ndwi_pre"], crop_mask)

    area_stats = compute_area_stats(dnbr_m, sev_m, roi, cfg)
    emissions = calculate_emissions(area_stats["area_moderate_km2"], cfg)

    firms_stats = get_firms_stats(roi, post_start, post_end, cfg.firms_temp_k)
    trend_years = [year - i for i in range(4, -1, -1)]
    trend_df = get_multi_year_trend(roi, trend_years, cfg.firms_temp_k)

    aq_pre = get_s5p_stats(roi, pre_start, pre_end, cfg.scale_s5p)
    aq_post = get_s5p_stats(roi, post_start, post_end, cfg.scale_s5p)

    monthly_df = get_monthly_series(
        roi,
        [
            (f"Aug {year}", f"{year}-08-01", f"{year}-08-31"),
            (f"Sep {year}", f"{year}-09-01", f"{year}-09-30"),
            (f"Oct {year}", f"{year}-10-01", f"{year}-10-31"),
            (f"Nov {year}", f"{year}-11-01", f"{year}-11-30"),
            (f"Dec {year}", f"{year}-12-01", f"{year}-12-31"),
        ],
        cfg.scale_s5p,
    )

    bulletin = generate_bulletin(cfg, area_stats, firms_stats, aq_pre, aq_post, emissions, year)

    no2_pre = aq_pre.get("NO2", {}).get("mean")
    no2_post = aq_post.get("NO2", {}).get("mean")
    co_pre = aq_pre.get("CO", {}).get("mean")
    co_post = aq_post.get("CO", {}).get("mean")

    no2_pct = ((no2_post - no2_pre) / max(no2_pre, 1e-10) * 100) if no2_pre and no2_post else 0
    co_pct = ((co_post - co_pre) / max(co_pre, 1e-10) * 100) if co_pre and co_post else 0

    return {
        "region": cfg.name,
        "season": f"{post_start} -> {post_end}",
        "area_any_km2": area_stats["area_any_km2"],
        "area_mod_km2": area_stats["area_moderate_km2"],
        "firms_area_km2": firms_stats["area_km2"],
        "no2_change_pct": round(no2_pct, 1),
        "co_change_pct": round(co_pct, 1),
        "pm25_tonnes": emissions.pm25_tonnes,
        "co2_eq_mt": emissions.co2_eq_million_tonnes,
        "health_cost_bn": emissions.health_cost_usd_bn,
        "alert_level": bulletin.alert_level,
        "fire_trend": {
            "years": trend_df["Year"].tolist(),
            "area_km2": trend_df["Area_km2"].tolist(),
        },
        "severity_dist": area_stats["severity_dist"],
        "districts": area_stats["sub_regions"],
        "no2_monthly": {
            "periods": monthly_df["Period"].tolist(),
            "no2": monthly_df["NO2_display"].fillna(0).tolist(),
            "co": monthly_df["CO_display"].fillna(0).tolist(),
            "no2_std": monthly_df["NO2_std"].fillna(0).tolist(),
            "co_std": monthly_df["CO_std"].fillna(0).tolist(),
        },
        "emissions": {k: v["tonnes"] for k, v in emissions.all_pollutants.items()},
    }


def main() -> None:
    sidebar = _render_sidebar()

    if "analysis_data" not in st.session_state:
        st.session_state.analysis_data = DEMO_DATA

    if sidebar["run_analysis"]:
        if sidebar["mode"] == "Live Satellite (GEE)":
            if not sidebar["gee_project"]:
                st.error("Please provide GEE Project ID first.")
            else:
                with st.spinner("Running live satellite workflow..."):
                    try:
                        st.session_state.analysis_data = _run_live_analysis(sidebar)
                        st.success("Live analysis complete.")
                    except Exception as exc:
                        st.error(f"Live run failed: {exc}")
                        st.info("Falling back to demo dataset.")
                        st.session_state.analysis_data = DEMO_DATA
        else:
            st.session_state.analysis_data = DEMO_DATA
            st.success("Demo dataset loaded.")

    data = st.session_state.analysis_data
    _render_header(data)
    st.write("")
    _render_kpis(data)

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Analysis", "Map", "Alert Bulletin", "Impact", "Export"])

    with tab1:
        _render_analysis_tab(data)
    with tab2:
        _render_map_tab(data)
    with tab3:
        _render_alert_tab(data)
    with tab4:
        _render_impact_tab(data)
    with tab5:
        _render_export_tab(data)

    st.markdown("---")
    st.markdown(
        "<div class='small-note'>AGNIWATCH v3.0 | MIT License | ESA Copernicus + NASA datasets</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()

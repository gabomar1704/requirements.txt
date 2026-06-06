"""
COVID-19 Global Dashboard — Streamlit + Plotly
Reescrito desde React. Usa los mismos 3 CSVs de la OMS.

Para correr:
    pip install streamlit plotly pandas
    streamlit run covid_dashboard.py
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np

# ─── PAGE CONFIG ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="COVID-19 Global Dashboard",
    page_icon="🦠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CUSTOM CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
  .stApp { background-color: #0d1117; color: #e6edf3; }
  section[data-testid="stSidebar"] { background-color: #161b22; }
  .block-container { padding-top: 1rem; padding-bottom: 1rem; }
  .kpi-card {
    background: #161b22; border: 1px solid #21262d; border-radius: 8px;
    padding: 16px 20px; margin-bottom: 8px;
  }
  .kpi-title { color: #7d8590; font-size: 12px; font-weight: 600;
               text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 4px; }
  .kpi-value { color: #e6edf3; font-size: 24px; font-weight: 700; }
  .kpi-sub   { color: #7d8590; font-size: 11px; margin-top: 2px; }
  .section-header {
    color: #4cc9f0; font-size: 13px; font-weight: 700;
    text-transform: uppercase; letter-spacing: 1px;
    border-bottom: 1px solid #21262d; padding-bottom: 6px; margin-bottom: 12px;
  }
  #MainMenu, footer { visibility: hidden; }
  .stTabs [data-baseweb="tab-list"] { background: #161b22; border-radius: 8px; }
  .stTabs [data-baseweb="tab"] { color: #7d8590; }
  .stTabs [aria-selected="true"] { color: #4cc9f0 !important; }
</style>
""", unsafe_allow_html=True)

# ─── CONSTANTS ────────────────────────────────────────────────────────────────
DARK_LAYOUT = dict(
    paper_bgcolor="#161b22", plot_bgcolor="#0d1117",
    font=dict(color="#e6edf3", size=11),
    margin=dict(l=50, r=20, t=40, b=50),
    legend=dict(bgcolor="#161b22", bordercolor="#21262d", borderwidth=1),
    xaxis=dict(gridcolor="#21262d", zeroline=False),
    yaxis=dict(gridcolor="#21262d", zeroline=False),
)

HUB_NAMES = {
    "US": "United States", "GB": "United Kingdom", "FR": "France",
    "DE": "Germany",       "CN": "China",          "JP": "Japan",
    "IN": "India",         "AE": "UAE",             "SG": "Singapore",
    "AU": "Australia",     "BR": "Brazil",          "IT": "Italy",
    "ES": "Spain",         "ZA": "South Africa",    "TH": "Thailand",
}
# Vaccination CSV uses ISO-3
ISO2_TO_ISO3 = {
    "US":"USA","GB":"GBR","FR":"FRA","DE":"DEU","CN":"CHN",
    "JP":"JPN","IN":"IND","AE":"ARE","SG":"SGP","AU":"AUS",
    "BR":"BRA","IT":"ITA","ES":"ESP","ZA":"ZAF","TH":"THA",
}
ISO3_TO_ISO2 = {v: k for k, v in ISO2_TO_ISO3.items()}

HUB_COLORS = [
    "#4cc9f0","#e63946","#f4a261","#57c0a0","#9b5de5",
    "#f7b731","#06d6a0","#ff6b6b","#a8dadc","#ffd166",
    "#06d6a0","#ef476f","#118ab2","#ffd166","#073b4c",
]
REGION_FULL = {
    "EURO": "Europe", "AMRO": "Americas", "SEARO": "South-East Asia",
    "WPRO": "Western Pacific", "EMRO": "E. Mediterranean", "AFRO": "Africa",
}
REGION_COLORS = {
    "EURO":"#4cc9f0","AMRO":"#e63946","SEARO":"#f4a261",
    "WPRO":"#57c0a0","EMRO":"#9b5de5","AFRO":"#f7b731",
}
WAVE_EVENTS = [
    {"date": "2020-01-30", "label": "WHO Emergency",     "color": "#f4a261"},
    {"date": "2020-03-11", "label": "Pandemic Declared", "color": "#e63946"},
    {"date": "2020-12-01", "label": "Alpha Variant",     "color": "#4cc9f0"},
    {"date": "2021-04-01", "label": "Delta Wave",        "color": "#f4a261"},
    {"date": "2021-11-26", "label": "Omicron Detected",  "color": "#e63946"},
]

# ─── DATA LOADING ─────────────────────────────────────────────────────────────
@st.cache_data
def load_global():
    df = pd.read_csv("WHO-COVID-19-global-data.csv", parse_dates=["Date_reported"])
    df.columns = df.columns.str.strip()
    for c in ["New_cases","New_deaths","Cumulative_cases","Cumulative_deaths"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    return df

@st.cache_data
def load_hosp():
    df = pd.read_csv("WHO-COVID-19-global-hosp-icu-data.csv",
                     encoding="utf-8-sig", parse_dates=["Date_reported"])
    df.columns = df.columns.str.strip()
    return df

@st.cache_data
def load_vax():
    df = pd.read_csv("COV_VAC_UPTAKE_2021_2023.csv",
                     encoding="utf-8-sig", parse_dates=["DATE"])
    df.columns = df.columns.str.strip()
    # Map ISO-3 → ISO-2 for consistency
    df["Country_code"] = df["COUNTRY"].map(ISO3_TO_ISO2)
    for c in ["COVID_VACCINE_COV_TOT_CPS","COVID_VACCINE_COV_TOT_A1D","COVID_VACCINE_COV_TOT_BOOST"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

try:
    df_global = load_global()
    df_hosp   = load_hosp()
    df_vax    = load_vax()
except FileNotFoundError as e:
    st.error(f"❌ Archivo no encontrado: {e}\n\nCorre el script en la misma carpeta que los CSVs.")
    st.stop()

# ─── DERIVED ──────────────────────────────────────────────────────────────────
@st.cache_data
def make_world_weekly(df):
    w = df.groupby("Date_reported")[["New_cases","New_deaths","Cumulative_cases","Cumulative_deaths"]].sum().reset_index()
    w = w.sort_values("Date_reported")
    w["CFR"] = (w["Cumulative_deaths"] / w["Cumulative_cases"].replace(0,np.nan)*100).round(2)
    return w

@st.cache_data
def make_region_weekly(df):
    r = df.groupby(["Date_reported","WHO_region"])[["New_cases","New_deaths"]].sum().reset_index()
    return r.sort_values("Date_reported")

@st.cache_data
def make_hub_weekly(df):
    h = df[df["Country_code"].isin(list(HUB_NAMES.keys()))].copy()
    h = h.groupby(["Date_reported","Country_code","Country"])[["New_cases","New_deaths"]].sum().reset_index()
    return h.sort_values("Date_reported")

world_w  = make_world_weekly(df_global)
region_w = make_region_weekly(df_global)
hub_w    = make_hub_weekly(df_global)

# ─── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="section-header">🦠 COVID-19 Dashboard</div>', unsafe_allow_html=True)
    st.caption("WHO Global Dataset · 2020–2023")
    st.divider()

    st.markdown("**Países**")
    selected_hubs = st.multiselect(
        "Países", options=list(HUB_NAMES.keys()),
        default=["US","BR","IN","GB","DE"],
        format_func=lambda x: HUB_NAMES.get(x,x),
        label_visibility="collapsed",
    )
    if not selected_hubs:
        selected_hubs = ["US"]

    st.divider()
    date_range = st.date_input(
        "Rango de fechas",
        value=(pd.Timestamp("2020-01-01"), pd.Timestamp("2022-12-31")),
        min_value=pd.Timestamp("2020-01-01"),
        max_value=pd.Timestamp("2023-06-01"),
    )
    d_start = pd.Timestamp(date_range[0]) if len(date_range) >= 1 else pd.Timestamp("2020-01-01")
    d_end   = pd.Timestamp(date_range[1]) if len(date_range) == 2 else pd.Timestamp("2022-12-31")

    st.divider()
    show_events = st.toggle("Mostrar hitos pandémicos", value=True)
    log_scale   = st.toggle("Escala logarítmica", value=False)
    st.divider()
    st.caption("Gpo 102 · Team 3")

# ─── FILTER ───────────────────────────────────────────────────────────────────
world_f  = world_w[(world_w["Date_reported"]>=d_start) & (world_w["Date_reported"]<=d_end)]
region_f = region_w[(region_w["Date_reported"]>=d_start) & (region_w["Date_reported"]<=d_end)]
hub_f    = hub_w[
    (hub_w["Date_reported"]>=d_start) &
    (hub_w["Date_reported"]<=d_end) &
    (hub_w["Country_code"].isin(selected_hubs))
]

# ─── HELPER: add wave vlines ──────────────────────────────────────────────────
def add_waves(fig, d_start, d_end, secondary_y=False):
    if not show_events:
        return
    for i, ev in enumerate(WAVE_EVENTS):
        ed = pd.Timestamp(ev["date"])
        if d_start <= ed <= d_end:
            fig.add_vline(x=ed, line_dash="dot", line_color=ev["color"],
                          line_width=1.2, opacity=0.65)
            fig.add_annotation(
                x=ed, y=1, yref="paper", text=ev["label"],
                showarrow=False, textangle=-90, yanchor="top",
                font=dict(size=8, color=ev["color"]), xshift=6+i*2,
            )

# ─── KPIs ─────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">📊 Resumen Global</div>', unsafe_allow_html=True)

total_cases  = int(world_f["New_cases"].sum())
total_deaths = int(world_f["New_deaths"].sum())
peak_cases   = int(world_f["New_cases"].max()) if len(world_f) else 0
peak_week    = world_f.loc[world_f["New_cases"].idxmax(),"Date_reported"].strftime("%b %Y") if len(world_f) else "—"
last_cfr     = round(float(world_f["CFR"].dropna().iloc[-1]), 2) if len(world_f) else 0

k1,k2,k3,k4,k5 = st.columns(5)
for col, title, val, sub in [
    (k1, "Casos Totales",   f"{total_cases/1e6:.1f}M",  "en el período"),
    (k2, "Muertes Totales", f"{total_deaths/1e6:.2f}M", "en el período"),
    (k3, "Pico Semanal",    f"{peak_cases/1e6:.1f}M",   f"semana de {peak_week}"),
    (k4, "CFR Final",       f"{last_cfr}%",              "Case Fatality Rate"),
    (k5, "Países",          str(df_global["Country_code"].nunique()), "en el dataset"),
]:
    col.markdown(f"""
    <div class="kpi-card">
      <div class="kpi-title">{title}</div>
      <div class="kpi-value">{val}</div>
      <div class="kpi-sub">{sub}</div>
    </div>""", unsafe_allow_html=True)

st.divider()

# ─── TABS ─────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🌍 Tendencia Global",
    "🗺️ Por Región WHO",
    "📍 Países Clave",
    "💉 Vacunación",
    "🏥 Hosp & UCI",
])

# ═══════════════════════════ TAB 1 — GLOBAL ═══════════════════════════════════
with tab1:
    st.markdown('<div class="section-header">Casos y muertes semanales — Mundial</div>', unsafe_allow_html=True)

    c_chart, c_ctrl = st.columns([3,1])
    with c_ctrl:
        metric = st.radio("Métrica", ["Casos nuevos","Muertes nuevas","CFR (%)"])
    yfield = {"Casos nuevos":"New_cases","Muertes nuevas":"New_deaths","CFR (%)":"CFR"}[metric]
    ycolor = {"Casos nuevos":"#4cc9f0","Muertes nuevas":"#e63946","CFR (%)":"#f4a261"}[metric]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=world_f["Date_reported"], y=world_f[yfield],
        fill="tozeroy", fillcolor=ycolor.replace("#","rgba(").replace(")","") + ",0.12)",
        line=dict(color=ycolor, width=2), name=metric,
        hovertemplate="%{x|%b %d %Y}<br>" + metric + ": %{y:,.0f}<extra></extra>",
    ))
    add_waves(fig, d_start, d_end)
    fig.update_layout(**DARK_LAYOUT, height=300,
                      yaxis_type="log" if log_scale else "linear",
                      title=dict(text=f"Tendencia global — {metric}", font=dict(color="#7d8590",size=12)))
    with c_chart:
        st.plotly_chart(fig, use_container_width=True)

    # Dual axis: cases bar + deaths line
    st.markdown('<div class="section-header">Casos (barras) vs Muertes (línea)</div>', unsafe_allow_html=True)
    fig2 = make_subplots(specs=[[{"secondary_y": True}]])
    fig2.add_trace(go.Bar(x=world_f["Date_reported"], y=world_f["New_cases"],
                          name="Casos", marker_color="#4cc9f0", opacity=0.55), secondary_y=False)
    fig2.add_trace(go.Scatter(x=world_f["Date_reported"], y=world_f["New_deaths"],
                              name="Muertes", line=dict(color="#e63946",width=2)), secondary_y=True)
    add_waves(fig2, d_start, d_end)
    fig2.update_layout(**DARK_LAYOUT, height=270, barmode="overlay",
                       title=dict(text="Casos vs Muertes", font=dict(color="#7d8590",size=12)))
    fig2.update_yaxes(title_text="Casos", gridcolor="#21262d", secondary_y=False)
    fig2.update_yaxes(title_text="Muertes", gridcolor="#21262d", secondary_y=True)
    st.plotly_chart(fig2, use_container_width=True)

# ═══════════════════════════ TAB 2 — REGIONS ══════════════════════════════════
with tab2:
    st.markdown('<div class="section-header">Nuevos casos por región WHO</div>', unsafe_allow_html=True)

    region_pivot = region_f.pivot_table(
        index="Date_reported", columns="WHO_region", values="New_cases", aggfunc="sum"
    ).fillna(0)

    fig3 = go.Figure()
    for reg in region_pivot.columns:
        col = REGION_COLORS.get(reg, "#7d8590")
        fig3.add_trace(go.Scatter(
            x=region_pivot.index, y=region_pivot[reg],
            stackgroup="one", name=REGION_FULL.get(reg, reg),
            line=dict(color=col, width=0.5),
            fillcolor=col+"44",
            hovertemplate="%{x|%b %Y}<br>%{y:,.0f}<extra>" + REGION_FULL.get(reg,reg) + "</extra>",
        ))
    add_waves(fig3, d_start, d_end)
    fig3.update_layout(**DARK_LAYOUT, height=360,
                       yaxis_type="log" if log_scale else "linear",
                       title=dict(text="Casos apilados por región WHO", font=dict(color="#7d8590",size=12)))
    st.plotly_chart(fig3, use_container_width=True)

    # Pie
    reg_tot = region_f.groupby("WHO_region")["New_cases"].sum().reset_index()
    reg_tot["Región"] = reg_tot["WHO_region"].map(REGION_FULL).fillna(reg_tot["WHO_region"])
    fig_pie = px.pie(reg_tot, values="New_cases", names="Región",
                     color_discrete_sequence=list(REGION_COLORS.values()), hole=0.45)
    fig_pie.update_layout(**DARK_LAYOUT, height=300,
                          title=dict(text="% de casos por región", font=dict(color="#7d8590",size=12)))
    fig_pie.update_traces(textposition="inside", textinfo="percent+label")
    st.plotly_chart(fig_pie, use_container_width=True)

# ═══════════════════════════ TAB 3 — HUB COUNTRIES ════════════════════════════
with tab3:
    st.markdown('<div class="section-header">Tendencia por país</div>', unsafe_allow_html=True)

    fig4 = go.Figure()
    for i, cc in enumerate(selected_hubs):
        sub = hub_f[hub_f["Country_code"]==cc].sort_values("Date_reported")
        if sub.empty: continue
        col = HUB_COLORS[i % len(HUB_COLORS)]
        fig4.add_trace(go.Scatter(
            x=sub["Date_reported"], y=sub["New_cases"],
            name=HUB_NAMES.get(cc,cc), line=dict(color=col, width=1.8),
            hovertemplate="%{x|%b %d %Y}<br>%{y:,.0f}<extra>" + HUB_NAMES.get(cc,cc) + "</extra>",
        ))
    add_waves(fig4, d_start, d_end)
    fig4.update_layout(**DARK_LAYOUT, height=340,
                       yaxis_type="log" if log_scale else "linear",
                       title=dict(text="Nuevos casos semanales", font=dict(color="#7d8590",size=12)))
    st.plotly_chart(fig4, use_container_width=True)

    # Deaths
    st.markdown('<div class="section-header">Muertes por país</div>', unsafe_allow_html=True)
    fig4b = go.Figure()
    for i, cc in enumerate(selected_hubs):
        sub = hub_f[hub_f["Country_code"]==cc].sort_values("Date_reported")
        if sub.empty: continue
        col = HUB_COLORS[i % len(HUB_COLORS)]
        fig4b.add_trace(go.Scatter(
            x=sub["Date_reported"], y=sub["New_deaths"],
            name=HUB_NAMES.get(cc,cc), line=dict(color=col, width=1.6),
            hovertemplate="%{x|%b %d %Y}<br>%{y:,.0f} muertes<extra>" + HUB_NAMES.get(cc,cc) + "</extra>",
        ))
    add_waves(fig4b, d_start, d_end)
    fig4b.update_layout(**DARK_LAYOUT, height=280,
                        yaxis_type="log" if log_scale else "linear",
                        title=dict(text="Muertes semanales", font=dict(color="#7d8590",size=12)))
    st.plotly_chart(fig4b, use_container_width=True)

    # Summary table
    st.markdown('<div class="section-header">Ranking — período seleccionado</div>', unsafe_allow_html=True)
    rank = hub_f.groupby("Country_code")[["New_cases","New_deaths"]].sum().reset_index()
    rank["País"] = rank["Country_code"].map(HUB_NAMES)
    rank["CFR"] = (rank["New_deaths"] / rank["New_cases"].replace(0,np.nan)*100).round(2)
    rank = rank.sort_values("New_cases", ascending=False)
    rank["Casos"]   = rank["New_cases"].apply(lambda x: f"{x/1e6:.2f}M" if x>=1e6 else f"{x/1e3:.0f}K")
    rank["Muertes"] = rank["New_deaths"].apply(lambda x: f"{x/1e3:.1f}K")
    rank["CFR %"]   = rank["CFR"].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else "—")
    st.dataframe(rank[["País","Casos","Muertes","CFR %"]].reset_index(drop=True),
                 use_container_width=True, hide_index=True)

# ═══════════════════════════ TAB 4 — VACCINATION ══════════════════════════════
with tab4:
    st.markdown('<div class="section-header">Cobertura de vacunación completa (%)</div>', unsafe_allow_html=True)

    vax_sel = df_vax[df_vax["Country_code"].isin(selected_hubs)].copy()

    fig5 = go.Figure()
    for i, cc in enumerate(selected_hubs):
        sub = vax_sel[vax_sel["Country_code"]==cc].sort_values("DATE")
        if sub.empty: continue
        sub_cov = sub.dropna(subset=["COVID_VACCINE_COV_TOT_CPS"])
        if sub_cov.empty: continue
        col = HUB_COLORS[i % len(HUB_COLORS)]
        fig5.add_trace(go.Scatter(
            x=sub_cov["DATE"], y=sub_cov["COVID_VACCINE_COV_TOT_CPS"],
            name=HUB_NAMES.get(cc,cc), line=dict(color=col, width=2),
            hovertemplate="%{x|%b %Y}<br>%{y:.1f}%<extra>" + HUB_NAMES.get(cc,cc) + "</extra>",
        ))

    fig5.add_hline(y=70, line_dash="dash", line_color="#f4a261", line_width=1.2,
                   annotation_text="70% umbral inmunidad de rebaño",
                   annotation_font_color="#f4a261", annotation_font_size=9)
    fig5.update_layout(
        **DARK_LAYOUT, height=340,
        yaxis=dict(range=[0,110], title="% vacunados (CPS)", gridcolor="#21262d"),
        title=dict(text="% con vacunación completa (ambas dosis)", font=dict(color="#7d8590",size=12)),
    )
    st.plotly_chart(fig5, use_container_width=True)

    # Bar chart: latest coverage
    st.markdown('<div class="section-header">Cobertura más reciente por país</div>', unsafe_allow_html=True)
    latest = (vax_sel.dropna(subset=["COVID_VACCINE_COV_TOT_A1D"])
              .sort_values("DATE")
              .groupby("Country_code").last().reset_index())
    latest["País"] = latest["Country_code"].map(HUB_NAMES).fillna(latest["Country_code"])
    latest = latest.sort_values("COVID_VACCINE_COV_TOT_A1D", ascending=True)

    fig6 = go.Figure(go.Bar(
        x=latest["COVID_VACCINE_COV_TOT_A1D"], y=latest["País"],
        orientation="h", marker_color="#4cc9f0",
        text=latest["COVID_VACCINE_COV_TOT_A1D"].apply(lambda x: f"{x:.0f}%" if pd.notna(x) else ""),
        textposition="inside",
        hovertemplate="%{y}<br>%{x:.1f}%<extra></extra>",
    ))
    fig6.update_layout(
        **DARK_LAYOUT, height=max(280, len(latest)*38),
        xaxis=dict(range=[0,110], title="% al menos 1 dosis", gridcolor="#21262d"),
        title=dict(text="≥ 1 dosis — último reporte disponible", font=dict(color="#7d8590",size=12)),
    )
    st.plotly_chart(fig6, use_container_width=True)

# ═══════════════════════════ TAB 5 — HOSP / ICU ═══════════════════════════════
with tab5:
    st.markdown('<div class="section-header">Hospitalizaciones e ingresos a UCI</div>', unsafe_allow_html=True)

    if "Country_code" not in df_hosp.columns:
        # Try to find country column
        cc_col = next((c for c in df_hosp.columns if "country" in c.lower()), None)
        if cc_col:
            df_hosp = df_hosp.rename(columns={cc_col: "Country_code"})

    hosp_cols = [c for c in df_hosp.columns if "hospital" in c.lower()]
    icu_cols  = [c for c in df_hosp.columns if "icu" in c.lower()]

    if not hosp_cols:
        st.info("ℹ️ No se encontraron columnas de hospitalización en el CSV.")
        st.caption("Columnas disponibles: " + ", ".join(df_hosp.columns.tolist()[:10]))
    else:
        hosp_col = hosp_cols[0]
        icu_col  = icu_cols[0] if icu_cols else None

        hosp_hub = df_hosp[df_hosp["Country_code"].isin(selected_hubs)].copy() if "Country_code" in df_hosp.columns else pd.DataFrame()

        if hosp_hub.empty:
            st.info("ℹ️ No hay datos de hospitalización para los países seleccionados en el período.")
        else:
            df_hosp[hosp_col] = pd.to_numeric(df_hosp[hosp_col], errors="coerce")
            if icu_col:
                df_hosp[icu_col] = pd.to_numeric(df_hosp[icu_col], errors="coerce")

            fig7 = make_subplots(specs=[[{"secondary_y": bool(icu_col)}]])
            for i, cc in enumerate(selected_hubs):
                sub = hosp_hub[hosp_hub["Country_code"]==cc].sort_values("Date_reported")
                if sub.empty: continue
                col = HUB_COLORS[i % len(HUB_COLORS)]
                fig7.add_trace(go.Scatter(
                    x=sub["Date_reported"], y=sub[hosp_col],
                    name=f"{HUB_NAMES.get(cc,cc)} Hosp",
                    line=dict(color=col, width=2),
                ), secondary_y=False)
                if icu_col:
                    fig7.add_trace(go.Scatter(
                        x=sub["Date_reported"], y=sub[icu_col],
                        name=f"{HUB_NAMES.get(cc,cc)} UCI",
                        line=dict(color=col, width=1.4, dash="dot"),
                    ), secondary_y=True)

            fig7.update_layout(**DARK_LAYOUT, height=360,
                               title=dict(text="Hosp. 7 días (sólido) · UCI 7 días (punteado)",
                                          font=dict(color="#7d8590",size=12)))
            fig7.update_yaxes(title_text="Hospitalizaciones 7d", gridcolor="#21262d", secondary_y=False)
            if icu_col:
                fig7.update_yaxes(title_text="UCI 7d", gridcolor="#21262d", secondary_y=True)
            add_waves(fig7, d_start, d_end)
            st.plotly_chart(fig7, use_container_width=True)

# ─── FOOTER ───────────────────────────────────────────────────────────────────
st.divider()
st.caption("📊 Fuente: WHO Global COVID-19 Dataset · Gpo 102, Team 3 · Streamlit + Plotly")

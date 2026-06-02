import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

st.set_page_config(
    page_title="Sales Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #1e3a5f 0%, #2d6a9f 100%);
        border-radius: 12px;
        padding: 20px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    .metric-label {
        font-size: 13px;
        opacity: 0.85;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 6px;
    }
    .metric-value {
        font-size: 28px;
        font-weight: 700;
    }
    .section-header {
        font-size: 20px;
        font-weight: 600;
        color: #1e3a5f;
        border-left: 4px solid #2d6a9f;
        padding-left: 12px;
        margin: 24px 0 12px 0;
    }
    .stSelectbox label, .stMultiSelect label {
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    file_path = "sellers.xlsx"
    
    # Safety Check: Verify the data file exists on the server
    if not os.path.exists(file_path):
        st.error(f"❌ Critical Error: '{file_path}' was not found in your repository root directory. Please upload it to GitHub alongside app.py.")
        st.stop()
        
    # Fixed: Forcing the openpyxl engine avoids the invisible pyarrow system crash
    df = pd.read_excel(file_path, engine="openpyxl")
    df["FULL NAME"] = df["NAME"] + " " + df["LASTNAME"]
    df["SALES AVERAGE PCT"] = (df["SALES AVERAGE"] * 100).round(2)
    return df

df = load_data()

# ── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/combo-chart.png", width=60)
    st.title("Sales Dashboard")
    st.markdown("---")

    st.markdown("### 🔍 Filters")

    all_regions = sorted(df["REGION"].unique().tolist())
    selected_regions = st.multiselect(
        "Region",
        options=all_regions,
        default=all_regions,
        help="Select one or more regions"
    )

    st.markdown("---")
    st.markdown("### 👤 Vendor Lookup")
    vendor_list = ["— Select a vendor —"] + sorted(df["FULL NAME"].tolist())
    selected_vendor = st.selectbox("Vendor", vendor_list)

    st.markdown("---")
    st.caption("Data: sellers.xlsx  •  52 sellers")

# ── FILTER DATA ───────────────────────────────────────────────────────────────
filtered = df[df["REGION"].isin(selected_regions)] if selected_regions else df.copy()

# ── HEADER ────────────────────────────────────────────────────────────────────
st.markdown("## 📊 Sales Performance Dashboard")
st.markdown(f"Showing **{len(filtered)}** sellers across **{len(selected_regions)}** region(s)")

# ── KPI METRICS ───────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(f"""<div class="metric-card">
        <div class="metric-label">Total Sellers</div>
        <div class="metric-value">{len(filtered)}</div>
    </div>""", unsafe_allow_html=True)

with c2:
    st.markdown(f"""<div class="metric-card">
        <div class="metric-label">Total Units Sold</div>
        <div class="metric-value">{filtered['SOLD UNITS'].sum():,}</div>
    </div>""", unsafe_allow_html=True)

with c3:
    st.markdown(f"""<div class="metric-card">
        <div class="metric-label">Total Sales</div>
        <div class="metric-value">${filtered['TOTAL SALES'].sum():,}</div>
    </div>""", unsafe_allow_html=True)

with c4:
    avg_pct = filtered["SALES AVERAGE PCT"].mean()
    st.markdown(f"""<div class="metric-card">
        <div class="metric-label">Avg. Sales Rate</div>
        <div class="metric-value">{avg_pct:.2f}%</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── DATA TABLE ────────────────────────────────────────────────────────────────
with st.container(border=True):
    st.markdown('<div class="section-header">📋 Sellers Table</div>', unsafe_allow_html=True)

    col_search, col_sort = st.columns([2, 1])
    with col_search:
        search = st.text_input("Search by name or ID", placeholder="Type to search...")
    with col_sort:
        sort_col = st.selectbox("Sort by", ["FULL NAME", "REGION", "SOLD UNITS", "TOTAL SALES", "SALES AVERAGE PCT", "INCOME"])

    display_df = filtered.copy()
    if search:
        mask = (
            display_df["FULL NAME"].str.contains(search, case=False, na=False) |
            display_df["ID"].astype(str).str.contains(search)
        )
        display_df = display_df[mask]

    display_df = display_df.sort_values(sort_col, ascending=False)

    show_cols = ["REGION", "ID", "FULL NAME", "INCOME", "SOLD UNITS", "TOTAL SALES", "SALES AVERAGE PCT"]
    rename_map = {
        "FULL NAME": "Name", "REGION": "Region", "ID": "ID",
        "INCOME": "Income ($)", "SOLD UNITS": "Units Sold",
        "TOTAL SALES": "Total Sales ($)", "SALES AVERAGE PCT": "Avg Sales (%)"
    }

    st.dataframe(
        display_df[show_cols].rename(columns=rename_map),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Income ($)": st.column_config.NumberColumn(format="$%d"),
            "Total Sales ($)": st.column_config.NumberColumn(format="$%d"),
            "Units Sold": st.column_config.NumberColumn(format="%d"),
            "Avg Sales (%)": st.column_config.NumberColumn(format="%.2f%%"),
        }
    )
    st.caption(f"{len(display_df)} records shown")

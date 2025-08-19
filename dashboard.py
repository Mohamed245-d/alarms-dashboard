import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_autorefresh import st_autorefresh

# === DASHBOARD SETUP ===
st.set_page_config(page_title="Critical Alarms Dashboard", layout="wide")
st.title("Critical Alarms Dashboard (Excel-based)")

# === Load Data ===
@st.cache_data
def load_data():
    df = pd.read_excel("streamlit_data.xlsx")
    # Convert timestamp columns
    df["firstTimeDetected"] = pd.to_datetime(df["firstTimeDetected"], unit="ms", errors="coerce")
    if "lastTimeDetected" in df.columns:
        df["lastTimeDetected"] = pd.to_datetime(df["lastTimeDetected"], unit="ms", errors="coerce")
    df = df.dropna(subset=["firstTimeDetected"])
    return df

# Load alarms
df = load_data()

# === Sidebar controls ===
st.sidebar.title("Controls")
severity_filter = st.sidebar.multiselect(
    "Select Severities", ["critical", "major", "minor"], default=["critical"]
)
refresh_rate = st.sidebar.slider("Auto-refresh (seconds)", 10, 300, 60)

if st.sidebar.button("Reload Data"):
    st.cache_data.clear()

# Auto refresh every refresh_rate seconds
st_autorefresh(interval=refresh_rate * 1000, key="datarefresh")

# === Filter data ===
if severity_filter:
    df = df[df["severity"].str.lower().isin(severity_filter)]

# Build dynamic label for selected severities
if severity_filter:
    severity_label = " / ".join(severity_filter).title()
else:
    severity_label = "All Severities"

# === Aggregation ===
site_criticals = (
    df.groupby("neName")["numberOfOccurrences"]
    .sum()
    .reset_index()
    .sort_values(by="numberOfOccurrences", ascending=False)
)
# === Data Table ===
st.subheader("Alarm Details")

# 🚨 Mark top sites inside the Alarm Details table
if not site_criticals.empty:
    max_crit = site_criticals["numberOfOccurrences"].max()
    top_sites = site_criticals[site_criticals["numberOfOccurrences"] == max_crit]["neName"].tolist()
    
    # Make a copy to avoid modifying original df
    df_display = df.copy()
    df_display["neName"] = df_display["neName"].apply(
        lambda x: f"{x} 🚨" if x in top_sites else x
    )

    st.dataframe(df_display)
else:
    st.warning("No alarms to display.")
# === Summary Cards ===
col1, col2, col3 = st.columns(3)
col1.metric(f"Total {severity_label}", int(site_criticals["numberOfOccurrences"].sum()))
col2.metric(f"Average {severity_label} per Site", round(site_criticals["numberOfOccurrences"].mean(), 2))
col3.metric("Number of Sites", len(site_criticals))

# === Top Sites ===
if not site_criticals.empty:
    top_site = site_criticals.iloc[0]
    st.subheader(f"Most {severity_label} Site")
    st.success(f"{top_site['neName']} — {top_site['numberOfOccurrences']} {severity_label}")

    if len(site_criticals) > 1:
        next_site = site_criticals.iloc[1]
        st.subheader(f"Next Predicted {severity_label} Site")
        st.info(f"{next_site['neName']} — {next_site['numberOfOccurrences']} {severity_label}")

# === Charts ===
st.subheader("Charts")

# Horizontal Bar Chart
st.plotly_chart(px.bar(
    site_criticals, x="numberOfOccurrences", y="neName",
    orientation="h", title=f"{severity_label} by Site"
))
# === Heatmap (Months vertical, Sites horizontal) ===
df_time = (
    df.groupby([pd.Grouper(key="firstTimeDetected", freq="M"), "neName"])["numberOfOccurrences"]
    .sum()
    .reset_index()
)

df_time["month"] = df_time["firstTimeDetected"].dt.strftime("%Y-%m")

# Create pivot table
pivot_table = df_time.pivot(index="month", columns="neName", values="numberOfOccurrences").fillna(0)

# 🚨 Add warning to ALL top sites with max occurrences
if not site_criticals.empty:
    max_crit = site_criticals["numberOfOccurrences"].max()
    top_sites = site_criticals[site_criticals["numberOfOccurrences"] == max_crit]["neName"].tolist()
    rename_map = {site: f"{site} 🚨" for site in top_sites}
    pivot_table = pivot_table.rename(columns=rename_map)

# Plot heatmap
st.plotly_chart(
    px.imshow(
        pivot_table,
        aspect="auto",
        color_continuous_scale="Viridis",
        title=f"Heatmap of {severity_label} by Site (horizontal) and Month (vertical)",
        labels={"color": "Occurrences"}
    )
)

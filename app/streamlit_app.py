import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import json

st.set_page_config(page_title="Blinkit Review Intelligence", layout="wide")

@st.cache_data
def load_data():
    base = Path(__file__).parent.parent / "data" / "processed"
    
    def safe_read(name):
        p = base / name
        return pd.read_parquet(p) if p.exists() else pd.DataFrame()
        
    reviews = safe_read("reviews_scored.parquet")
    impact = safe_read("impact_results.parquet")
    versions = safe_read("version_theme.parquet")
    trends = safe_read("theme_trend.parquet")
    
    metrics_path = base / "metrics.json"
    if metrics_path.exists():
        with open(metrics_path, "r", encoding="utf-8") as f:
            metrics = json.load(f)
    else:
        metrics = {}
        
    dq_path = base / "dq_report.json"
    if dq_path.exists():
        with open(dq_path, "r", encoding="utf-8") as f:
            dq = json.load(f)
    else:
        dq = {}
        
    return reviews, impact, versions, trends, metrics, dq

reviews, impact, versions, trends, metrics, dq = load_data()

st.title("Blinkit Review Intelligence Engine")

if reviews.empty:
    st.warning("Processed data not found. Please run the pipeline first.")
    st.stop()

st.header("Overview")

avg_rating = reviews['rating'].mean()
review_count = len(reviews)
neg_share = (reviews['rating'] <= 2).mean() * 100
eng_share = dq.get('english_share', 0) * 100

col1, col2, col3, col4 = st.columns(4)
col1.metric("Average Rating", f"{avg_rating:.2f}")
col2.metric("Total Reviews (Sample)", f"{review_count:,}")
col3.metric("% Negative (1-2 Stars)", f"{neg_share:.1f}%")
col4.metric("% English Analyzed", f"{eng_share:.1f}%")

st.markdown(f"**Data Freshness:** {dq.get('max_date', 'Unknown')}")

st.subheader("Rating Trend")
if not trends.empty:
    fig = px.line(trends, x='review_week', y='avg_rating', title="Weekly Average Rating")
    st.plotly_chart(fig, use_container_width=True)
    
st.subheader("Top Complaint Themes")
if not impact.empty:
    top = impact.sort_values('prevalence', ascending=False).head(10)
    fig2 = px.bar(top, x='theme', y='prevalence', title="Theme Prevalence (%)")
    fig2.update_layout(yaxis_tickformat='.1%')
    st.plotly_chart(fig2, use_container_width=True)

import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import sys

# Hack for direct run of page if needed
sys.path.append(str(Path(__file__).parent.parent.parent))
from app.streamlit_app import load_data

st.title("Theme Trends")

reviews, impact, versions, trends, metrics, dq = load_data()

if trends.empty:
    st.warning("Trend data not found.")
    st.stop()
    
st.markdown("Weekly share per theme.")

theme_cols = [c for c in trends.columns if c.endswith('_share')]
selected_themes = st.multiselect("Select Themes", theme_cols, default=theme_cols[:3])

if selected_themes:
    fig = px.line(trends, x='review_week', y=selected_themes, title="Theme Mentions over Time")
    fig.update_layout(yaxis_tickformat='.1%')
    st.plotly_chart(fig, use_container_width=True)

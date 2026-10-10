import streamlit as st
import plotly.express as px
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent.parent))
from app.streamlit_app import load_data

st.title("Version Explorer")

reviews, impact, versions, trends, metrics, dq = load_data()

if versions.empty:
    st.warning("Version data not found.")
    st.stop()

fig = px.bar(versions, x='app_version', y='review_count', title="Review Volume by Version")
st.plotly_chart(fig, use_container_width=True)

fig2 = px.line(versions, x='app_version', y='avg_rating', title="Average Rating by Version")
st.plotly_chart(fig2, use_container_width=True)

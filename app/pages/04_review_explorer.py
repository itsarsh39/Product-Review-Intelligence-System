import streamlit as st
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent.parent))
from app.streamlit_app import load_data

st.title("Review Explorer")

reviews, impact, versions, trends, metrics, dq = load_data()

if reviews.empty:
    st.warning("Review data not found.")
    st.stop()

st.sidebar.header("Filters")
selected_rating = st.sidebar.multiselect("Rating", [1,2,3,4,5], default=[1,2,3,4,5])

filtered = reviews[reviews['rating'].isin(selected_rating)]

st.dataframe(filtered[['reviewed_at', 'rating', 'app_version', 'primary_theme', 'content']])

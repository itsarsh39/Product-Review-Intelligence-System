import streamlit as st
import json
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent.parent))
from app.streamlit_app import load_data

st.title("Methodology & Quality")

reviews, impact, versions, trends, metrics, dq = load_data()

st.header("Data Quality Report")
st.json(dq)

st.header("Validation Metrics")
st.json(metrics)

st.header("Limitations")
st.markdown("""
- **Observational Data**: Results establish association, not causation.
- **Self-Selection**: Reviewers are not a random sample of all users.
- **Hinglish**: Currently, the pipeline primarily analyzes English reviews.
""")

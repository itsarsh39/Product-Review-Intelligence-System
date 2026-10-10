import streamlit as st
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent.parent))
from app.streamlit_app import load_data

st.title("Fix Priorities")

reviews, impact, versions, trends, metrics, dq = load_data()

if impact.empty:
    st.warning("Impact data not found.")
    st.stop()
    
st.markdown("""
This page ranks the issues based on a **Priority Score**.
Priority Score = Prevalence × Estimated Rating Penalty.
""")

st.dataframe(
    impact[['theme', 'prevalence', 'rating_penalty', 'what_if_rating', 'priority_score']].style.format({
        'prevalence': '{:.1%}',
        'rating_penalty': '{:.2f}',
        'what_if_rating': '{:.2f}',
        'priority_score': '{:.4f}'
    })
)

st.subheader("Top 3 Recommendations")
top_3 = impact.head(3)
for i, row in top_3.iterrows():
    st.markdown(f"**{row['theme']}**: Affects {row['prevalence']*100:.1f}% of reviews. If fixed, average rating could improve to {row['what_if_rating']:.2f}.")

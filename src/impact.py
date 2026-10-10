import pandas as pd
import numpy as np
import statsmodels.api as sm
import statsmodels.formula.api as smf
import logging
from src.config import config, BASE_DIR
import yaml

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def compute_impact(df: pd.DataFrame) -> pd.DataFrame:
    df = df[df['lang'] == 'english'].copy()
    if len(df) == 0:
        logging.warning("No English reviews found for impact analysis.")
        return pd.DataFrame()

    with open(BASE_DIR / config['themes']['taxonomy_path'], "r", encoding="utf-8") as f:
        taxonomy = yaml.safe_load(f)['themes']

    theme_ids = [t['id'] for t in taxonomy]
    theme_cols = [f"theme_{t}" for t in theme_ids if f"theme_{t}" in df.columns]
    
    prevalence = {t: df[f"theme_{t}"].mean() for t in theme_ids if f"theme_{t}" in df.columns}
    
    # If there's only 1 version or 1 month, C(version_group) or C(review_month) can cause issues if everything is constant.
    # Protect against this for small sample sizes.
    top_versions = df['app_version'].value_counts().nlargest(5).index
    df['version_group'] = df['app_version'].apply(lambda x: x if x in top_versions else 'Other')
    
    formula_parts = ["rating ~ " + " + ".join(theme_cols) + " + word_count"]
    if df['version_group'].nunique() > 1:
        formula_parts.append("C(version_group)")
    if df['review_month'].nunique() > 1:
        formula_parts.append("C(review_month)")
        
    formula = " + ".join(formula_parts)
    
    try:
        model = smf.ols(formula, data=df).fit(cov_type='HC3')
        logging.info("OLS regression completed.")
        
        df['is_negative'] = (df['rating'] <= 2).astype(int)
        logit_formula_parts = ["is_negative ~ " + " + ".join(theme_cols) + " + word_count"]
        logit_formula = " + ".join(logit_formula_parts)
        logit_model = smf.logit(logit_formula, data=df).fit(disp=0)
        logging.info("Logit regression completed.")
        
    except Exception as e:
        logging.error(f"Regression failed: {e}")
        return pd.DataFrame()

    results = []
    for t in theme_ids:
        col = f"theme_{t}"
        if col in model.params:
            coef = model.params[col]
            p_val = model.pvalues[col]
            ci_lower = model.conf_int().loc[col, 0]
            ci_upper = model.conf_int().loc[col, 1]
            
            logit_coef = logit_model.params[col] if col in logit_model.params else 0
            
            prev = prevalence.get(t, 0)
            penalty = coef if coef < 0 else 0
            what_if = df['rating'].mean() - (prev * penalty)
            priority_score = prev * abs(penalty)
            
            results.append({
                "theme": t,
                "prevalence": prev,
                "rating_penalty": penalty,
                "penalty_p_value": p_val,
                "penalty_ci_lower": ci_lower,
                "penalty_ci_upper": ci_upper,
                "logit_coef": logit_coef,
                "what_if_rating": what_if,
                "priority_score": priority_score
            })
            
    res_df = pd.DataFrame(results).sort_values("priority_score", ascending=False)
    return res_df

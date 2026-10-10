import pandas as pd
import logging
import yaml
from src.config import config, BASE_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def analyze_versions(df: pd.DataFrame) -> (pd.DataFrame, pd.DataFrame):
    if len(df) == 0:
        return pd.DataFrame(), pd.DataFrame()
        
    min_reviews = config['impact'].get('min_reviews_per_version', 50)
    
    with open(BASE_DIR / config['themes']['taxonomy_path'], "r", encoding="utf-8") as f:
        taxonomy = yaml.safe_load(f)['themes']
    theme_ids = [t['id'] for t in taxonomy]
    theme_cols = [f"theme_{t}" for t in theme_ids if f"theme_{t}" in df.columns]
    
    version_counts = df['app_version'].value_counts()
    valid_versions = version_counts[version_counts >= min_reviews].index
    
    v_df = df[df['app_version'].isin(valid_versions)].copy()
    
    version_stats = v_df.groupby('app_version').agg(
        review_count=('review_id', 'count'),
        avg_rating=('rating', 'mean')
    )
    
    for tc in theme_cols:
        theme_share = v_df.groupby('app_version')[tc].mean()
        version_stats[tc + "_share"] = theme_share
        
    version_stats = version_stats.reset_index().sort_values('app_version')
    
    week_stats = df.groupby('review_week').agg(
        review_count=('review_id', 'count'),
        avg_rating=('rating', 'mean')
    )
    for tc in theme_cols:
        week_stats[tc + "_share"] = df.groupby('review_week')[tc].mean()
        
    week_stats = week_stats.reset_index().sort_values('review_week')
    
    return version_stats, week_stats

import pandas as pd
import logging
from pathlib import Path
from src.config import BASE_DIR, config

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def export_data(df: pd.DataFrame, impact_df: pd.DataFrame, version_df: pd.DataFrame, week_df: pd.DataFrame):
    out_dir = BASE_DIR / "data" / "processed"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    sample_size = config['app'].get('sample_size', 20000)
    out_df = df.sort_values("reviewed_at", ascending=False).head(sample_size)
    
    cols_to_keep = ['review_id', 'content', 'rating', 'reviewed_at', 'app_version', 'sentiment_label', 'sentiment_score', 'primary_theme']
    theme_cols = [c for c in df.columns if c.startswith('theme_')]
    cols_to_keep.extend(theme_cols)
    
    cols_to_keep = [c for c in cols_to_keep if c in out_df.columns]
    
    out_df[cols_to_keep].to_parquet(out_dir / "reviews_scored.parquet", index=False)
    
    if len(impact_df) > 0:
        impact_df.to_parquet(out_dir / "impact_results.parquet", index=False)
        
    if len(version_df) > 0:
        version_df.to_parquet(out_dir / "version_theme.parquet", index=False)
        
    if len(week_df) > 0:
        week_df.to_parquet(out_dir / "theme_trend.parquet", index=False)
        
    logging.info(f"Data exported to {out_dir}")

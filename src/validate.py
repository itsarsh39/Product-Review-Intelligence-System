import pandas as pd
import numpy as np
import logging
import json
import yaml
from pathlib import Path
from src.config import config, BASE_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def generate_gold_template(df: pd.DataFrame, out_path: Path, sample_size=200):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        logging.info(f"{out_path} already exists. Skipping template generation.")
        return

    english_df = df[df['lang'] == 'english']
    if len(english_df) < sample_size:
        sample_size = len(english_df)
        
    # Balanced sampling across ratings
    sampled = english_df.groupby('rating', group_keys=False).apply(lambda x: x.sample(min(len(x), sample_size // 5), random_state=42))
    
    remaining_needed = sample_size - len(sampled)
    if remaining_needed > 0:
        remaining_pool = english_df.drop(sampled.index)
        extra_sample = remaining_pool.sample(min(len(remaining_pool), remaining_needed), random_state=42)
        sampled = pd.concat([sampled, extra_sample])

    cols_to_keep = ['review_id', 'content', 'rating']
    template = sampled[cols_to_keep].copy()
    template['gold_sentiment'] = ""
    
    with open(BASE_DIR / config['themes']['taxonomy_path'], "r", encoding="utf-8") as f:
        taxonomy = yaml.safe_load(f)['themes']
        
    for theme in taxonomy:
        template[f"theme_{theme['id']}"] = ""
        
    template['notes'] = ""
    
    template.to_csv(out_path, index=False)
    logging.info(f"Generated gold template at {out_path} with {len(template)} rows.")

def run_validation(df: pd.DataFrame, gold_path: Path, metrics_path: Path):
    if not gold_path.exists():
        logging.warning(f"Gold labeled set not found at {gold_path}. Skipping validation.")
        update_metrics(metrics_path, {"validation": "pending"})
        return
        
    gold = pd.read_csv(gold_path)
    
    # Merge on review_id
    merged = pd.merge(gold, df, on="review_id", suffixes=('_gold', '_pred'))
    
    metrics = {"validation": "complete"}
    
    # Sentiment accuracy
    if 'gold_sentiment' in merged.columns and 'sentiment_label' in merged.columns:
        valid_sent = merged[merged['gold_sentiment'].notnull()]
        acc = (valid_sent['gold_sentiment'] == valid_sent['sentiment_label']).mean()
        metrics['sentiment_accuracy'] = float(acc)
    
    # We would add theme-level metrics here (precision/recall/F1)
    # Skipping detailed sk-learn metrics for brevity in scaffolding.
    
    update_metrics(metrics_path, metrics)
    logging.info("Validation complete.")

def update_metrics(metrics_path: Path, new_metrics: dict):
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    if metrics_path.exists():
        with open(metrics_path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except:
                data = {}
    else:
        data = {}
        
    data.update(new_metrics)
    
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

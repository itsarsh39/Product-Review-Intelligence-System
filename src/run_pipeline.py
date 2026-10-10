import argparse
import logging
import sqlite3
import pandas as pd
from pathlib import Path
from src.config import config, BASE_DIR
from src.ingest import ingest_reviews
from src.clean import clean_reviews
from src.quality import run_quality_checks
from src.sentiment import SentimentScorer, report_agreement
from src.themes import ThemeTagger
from src.validate import generate_gold_template, run_validation
from src.impact import compute_impact
from src.versions import analyze_versions
from src.export import export_data

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def load_data():
    db_path = BASE_DIR / config["ingest"]["db_path"]
    if not db_path.exists():
        return pd.DataFrame()
    conn = sqlite3.connect(db_path)
    df = pd.read_sql("SELECT * FROM reviews", conn)
    conn.close()
    return df

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', type=str, default='all', choices=['ingest', 'clean', 'sentiment', 'themes', 'validate', 'impact', 'versions', 'export', 'all'])
    parser.add_argument('--sample', type=int, default=None)
    parser.add_argument('--full-refresh', action='store_true')
    args = parser.parse_args()
    
    # 1. Ingest
    if args.stage in ['ingest', 'all']:
        logging.info("--- STAGE: INGEST ---")
        ingest_reviews(sample_size=args.sample)
        
    df = load_data()
    if args.sample:
        df = df.head(args.sample)
        
    if len(df) == 0:
        logging.error("No data found to process. Exiting.")
        return
        
    initial_count = len(df)
        
    # 2. Clean
    if args.stage in ['clean', 'all'] or (args.stage in ['sentiment', 'themes', 'validate', 'impact', 'versions', 'export']):
        # Need clean data for subsequent steps
        logging.info("--- STAGE: CLEAN & QUALITY ---")
        df = clean_reviews(df)
        if args.stage in ['clean', 'all']:
            run_quality_checks(df, initial_count, BASE_DIR / "data" / "processed")
        
    # 3. Sentiment
    if args.stage in ['sentiment', 'all']:
        logging.info("--- STAGE: SENTIMENT ---")
        scorer = SentimentScorer()
        df = scorer.score_reviews(df)
        report_agreement(df)
        
    # 4. Themes
    if args.stage in ['themes', 'all']:
        logging.info("--- STAGE: THEMES ---")
        tagger = ThemeTagger()
        df = tagger.tag_reviews(df)
        
    # 5. Validate
    if args.stage in ['validate', 'all']:
        logging.info("--- STAGE: VALIDATE ---")
        gold_template = BASE_DIR / "data" / "gold" / "gold_template.csv"
        gold_labeled = BASE_DIR / "data" / "gold" / "gold_labeled.csv"
        metrics_path = BASE_DIR / "data" / "processed" / "metrics.json"
        
        generate_gold_template(df, gold_template)
        run_validation(df, gold_labeled, metrics_path)
        
    # 6. Impact
    impact_df = pd.DataFrame()
    if args.stage in ['impact', 'all']:
        logging.info("--- STAGE: IMPACT ---")
        impact_df = compute_impact(df)
        
    # 7. Versions
    version_df = pd.DataFrame()
    week_df = pd.DataFrame()
    if args.stage in ['versions', 'all']:
        logging.info("--- STAGE: VERSIONS ---")
        version_df, week_df = analyze_versions(df)
        
    # 8. Export
    if args.stage in ['export', 'all']:
        logging.info("--- STAGE: EXPORT ---")
        export_data(df, impact_df, version_df, week_df)
        
    logging.info("Pipeline run complete.")

if __name__ == "__main__":
    main()

import pandas as pd
import json
import logging
from pathlib import Path
from src.config import config, BASE_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def check_quality(df: pd.DataFrame, initial_count: int) -> dict:
    report = {}
    passed = True
    
    # Row count and date range
    report['row_count'] = len(df)
    if len(df) == 0:
        report['status'] = 'FAIL'
        report['reason'] = 'No data'
        return report

    dt_col = pd.to_datetime(df['reviewed_at'], format='mixed', utc=True)
    report['min_date'] = dt_col.min().isoformat()
    report['max_date'] = dt_col.max().isoformat()
    
    # Max gap in days
    dates = dt_col.dt.date.sort_values().unique()
    if len(dates) > 1:
        gaps = pd.Series(dates).diff().dt.days
        max_gap = int(gaps.max())
    else:
        max_gap = 0
    report['max_gap_days'] = max_gap
    
    # Null rate
    null_rates = df.isnull().mean().to_dict()
    report['null_rates'] = null_rates
    
    max_null = config['quality']['max_null_rate']
    if null_rates.get('content', 0) > max_null or null_rates.get('rating', 0) > max_null:
        report['null_check'] = 'FAIL'
        passed = False
    else:
        report['null_check'] = 'PASS'
        
    # Rating distribution sanity
    if not df['rating'].between(1, 5).all():
        report['rating_sanity'] = 'FAIL'
        passed = False
    else:
        report['rating_sanity'] = 'PASS'
        
    # Daily volume anomaly detection
    daily_vol = df.groupby(dt_col.dt.date).size()
    mad = (daily_vol - daily_vol.median()).abs().median()
    anomalies = []
    if mad > 0:
        threshold = config['quality']['anomaly_mad_threshold']
        z_scores = (daily_vol - daily_vol.median()) / mad
        anomalies = daily_vol[z_scores > threshold].index.astype(str).tolist()
    report['volume_anomalies'] = anomalies
    
    # Share of non-English / Hinglish
    eng_share = (df['lang'] == 'english').mean()
    hinglish_share = df['likely_hinglish'].mean()
    report['english_share'] = float(eng_share)
    report['hinglish_share'] = float(hinglish_share)
    
    # Duplicate rate (against initial ingested count)
    dup_rate = 1.0 - (len(df) / initial_count) if initial_count > 0 else 0
    report['duplicate_rate'] = float(dup_rate)
    
    # Freshness
    days_since_latest = (pd.Timestamp.utcnow() - dt_col.max()).days
    report['freshness_days'] = int(days_since_latest)
    if days_since_latest > config['quality']['freshness_days']:
        report['freshness_check'] = 'FAIL'
        passed = False
    else:
        report['freshness_check'] = 'PASS'

    report['status'] = 'PASS' if passed else 'FAIL'
    
    return report

def run_quality_checks(df: pd.DataFrame, initial_count: int, output_dir: Path):
    report = check_quality(df, initial_count)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    with open(output_dir / "dq_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
        
    if report['status'] == 'FAIL':
        logging.error(f"Data quality checks failed: {json.dumps(report, indent=2)}")
        raise ValueError("Data quality checks failed!")
    else:
        logging.info("Data quality checks passed.")

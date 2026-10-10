import sqlite3
import logging
from datetime import datetime
from pathlib import Path
import time
from google_play_scraper import Sort, reviews

from src.config import config, BASE_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def init_db(db_path: Path):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            review_id TEXT PRIMARY KEY,
            app_id TEXT,
            content TEXT,
            rating INTEGER,
            thumbs_up INTEGER,
            app_version TEXT,
            reviewed_at TEXT,
            reply_text TEXT,
            ingested_at TEXT
        )
    ''')
    conn.commit()
    return conn

def ingest_reviews(sample_size=None):
    app_id = config["app_id"]
    lang = config["lang"]
    country = config["country"]
    max_reviews = sample_size if sample_size else config["ingest"]["max_reviews"]
    batch_size = config["ingest"]["batch_size"]
    sleep_seconds = config["ingest"]["sleep_seconds"]
    db_path = BASE_DIR / config["ingest"]["db_path"]

    conn = init_db(db_path)
    cursor = conn.cursor()

    logging.info(f"Starting ingestion for {app_id}, max {max_reviews} reviews.")

    continuation_token = None
    total_fetched = 0
    new_inserted = 0

    while total_fetched < max_reviews:
        try:
            result, continuation_token = reviews(
                app_id,
                lang=lang,
                country=country,
                sort=Sort.NEWEST,
                count=batch_size,
                continuation_token=continuation_token
            )
            
            if not result:
                logging.info("No more reviews found.")
                break

            records = []
            for r in result:
                records.append((
                    r["reviewId"],
                    app_id,
                    r["content"],
                    r["score"],
                    r["thumbsUpCount"],
                    r["reviewCreatedVersion"] or "unknown",
                    r["at"].isoformat() if hasattr(r["at"], "isoformat") else str(r["at"]),
                    r.get("replyContent"),
                    datetime.utcnow().isoformat()
                ))

            total_fetched += len(result)

            cursor.executemany('''
                INSERT OR IGNORE INTO reviews (
                    review_id, app_id, content, rating, thumbs_up, 
                    app_version, reviewed_at, reply_text, ingested_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', records)
            
            inserted_this_batch = cursor.rowcount
            new_inserted += inserted_this_batch
            conn.commit()
            
            logging.info(f"Fetched {len(result)}, inserted {inserted_this_batch}. Total fetched: {total_fetched}")

            # Stop early if all reviews in batch were already in DB (incremental update)
            # Assuming newest sort means we will eventually hit all old ones
            if inserted_this_batch == 0 and total_fetched > 0:
                logging.info("All reviews in this batch already exist. Stopping incremental run.")
                break

            if continuation_token is None or total_fetched >= max_reviews:
                break
                
            time.sleep(sleep_seconds)

        except Exception as e:
            logging.error(f"Error fetching reviews: {e}")
            time.sleep(sleep_seconds * 2) # Backoff
            break

    conn.close()
    logging.info(f"Ingestion complete. Total new inserted: {new_inserted}")
    return new_inserted

if __name__ == "__main__":
    import sys
    sample = int(sys.argv[1]) if len(sys.argv) > 1 else None
    ingest_reviews(sample)

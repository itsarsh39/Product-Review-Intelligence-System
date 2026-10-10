import pandas as pd
import re
import emoji
from lingua import Language, LanguageDetectorBuilder
import logging

from src.config import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

detector = LanguageDetectorBuilder.from_languages(Language.ENGLISH, Language.HINDI, Language.MARATHI, Language.BENGALI, Language.TELUGU, Language.TAMIL, Language.URDU).build()

def clean_reviews(df: pd.DataFrame) -> pd.DataFrame:
    initial_len = len(df)
    
    # 1. Deduplicate text + version + day
    df['review_date'] = pd.to_datetime(df['reviewed_at']).dt.date
    df = df.drop_duplicates(subset=['content', 'app_version', 'review_date'], keep='first').copy()
    logging.info(f"Dropped {initial_len - len(df)} duplicate reviews.")
    
    # 2. Normalize whitespace, strip control characters, handle emojis
    def normalize_text(text):
        if not isinstance(text, str):
            return ""
        # Remove control characters
        text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def check_emoji(text):
        return int(emoji.emoji_count(text) > 0)

    df['has_emoji'] = df['content'].apply(check_emoji)
    df['content'] = df['content'].apply(normalize_text)

    # 3. Word count & min words filter
    df['word_count'] = df['content'].apply(lambda x: len(x.split()))
    min_words = config['clean']['min_words']
    pre_min_words_len = len(df)
    df = df[df['word_count'] >= min_words]
    logging.info(f"Dropped {pre_min_words_len - len(df)} reviews with < {min_words} words.")

    # 4. Language detection
    def detect_lang(text):
        try:
            lang = detector.detect_language_of(text)
            return lang.name.lower() if lang else "unknown"
        except:
            return "unknown"
            
    df['lang'] = df['content'].apply(detect_lang)

    # 5. Hinglish heuristic
    stopwords = set(config['clean']['hindi_stopwords'])
    def is_hinglish(text, lang):
        if lang != "english" and lang != "unknown":
            return 0
        words = set(text.lower().split())
        return int(len(words.intersection(stopwords)) > 0)
        
    df['likely_hinglish'] = df.apply(lambda row: is_hinglish(row['content'], row['lang']), axis=1)

    # 6. Additional features
    # df['review_month'] = pd.to_datetime(df['reviewed_at']).dt.to_period('M').astype(str)
    # df['review_week'] = pd.to_datetime(df['reviewed_at']).dt.to_period('W').astype(str)
    # to_period can be problematic for serialization, better to use string formatting or truncate
    dt_col = pd.to_datetime(df['reviewed_at'])
    df['review_month'] = dt_col.dt.strftime('%Y-%m')
    df['review_week'] = (dt_col - pd.to_timedelta(dt_col.dt.dayofweek, unit='d')).dt.strftime('%Y-%m-%d')
    df['is_negative_rating'] = (df['rating'] <= 2).astype(int)

    logging.info(f"Final row count: {len(df)}")
    return df

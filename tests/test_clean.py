import pandas as pd
from src.clean import clean_reviews
from src.config import config

def test_clean_dedupe():
    data = [
        {"content": "This is the same text", "app_version": "1.0", "reviewed_at": "2024-01-01T10:00:00Z", "rating": 5},
        {"content": "This is the same text", "app_version": "1.0", "reviewed_at": "2024-01-01T11:00:00Z", "rating": 5}, # Duplicate
        {"content": "This is the same text", "app_version": "1.1", "reviewed_at": "2024-01-01T10:00:00Z", "rating": 5}, # Diff version
        {"content": "This is the same text", "app_version": "1.0", "reviewed_at": "2024-01-02T10:00:00Z", "rating": 5}, # Diff day
    ]
    df = pd.DataFrame(data)
    cleaned = clean_reviews(df)
    # The first one should be kept, the second dropped, the third and fourth kept
    assert len(cleaned) == 3

def test_clean_min_words():
    min_words = config['clean']['min_words']
    data = [
        {"content": "Good app", "app_version": "1.0", "reviewed_at": "2024-01-01T10:00:00Z", "rating": 5}, # 2 words, will drop if min is 3
        {"content": "This is a good app", "app_version": "1.0", "reviewed_at": "2024-01-01T10:00:00Z", "rating": 5}, # Keep
    ]
    df = pd.DataFrame(data)
    cleaned = clean_reviews(df)
    if min_words > 2:
        assert len(cleaned) == 1
    else:
        assert len(cleaned) == 2

def test_clean_language_and_hinglish():
    data = [
        {"content": "This is a very good application", "app_version": "1.0", "reviewed_at": "2024-01-01T10:00:00Z", "rating": 5}, # English
        {"content": "Yeh app bahut bekar hai aur nahi chal raha", "app_version": "1.0", "reviewed_at": "2024-01-01T10:00:00Z", "rating": 1}, # Hinglish
    ]
    df = pd.DataFrame(data)
    cleaned = clean_reviews(df)
    assert len(cleaned) == 2
    
    eng_row = cleaned.iloc[0]
    hing_row = cleaned.iloc[1]
    
    assert eng_row['lang'] == 'english'
    assert eng_row['likely_hinglish'] == 0
    assert hing_row['likely_hinglish'] == 1

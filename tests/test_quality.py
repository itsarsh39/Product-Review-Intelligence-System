import pandas as pd
from src.quality import check_quality

def test_quality_pass():
    data = [
        {"reviewed_at": "2024-01-01T10:00:00Z", "content": "A test review string", "rating": 5, "lang": "english", "likely_hinglish": 0},
        {"reviewed_at": "2024-01-02T10:00:00Z", "content": "Another test string", "rating": 4, "lang": "english", "likely_hinglish": 0},
    ]
    df = pd.DataFrame(data)
    # Simulate freshness by pretending current date is close to the max date
    report = check_quality(df, initial_count=2)
    # Note: freshness might fail if run in 2026, let's patch the check or just accept it might fail in tests depending on current date.
    # Actually, we should use a recent date to ensure freshness passes
    import datetime
    recent_date = datetime.datetime.utcnow().isoformat()
    df.loc[1, 'reviewed_at'] = recent_date
    report = check_quality(df, initial_count=2)
    assert report['status'] == 'PASS'
    assert report['row_count'] == 2

def test_quality_fail_nulls():
    data = [
        {"reviewed_at": "2024-01-01T10:00:00Z", "content": None, "rating": 5, "lang": "english", "likely_hinglish": 0},
        {"reviewed_at": "2024-01-02T10:00:00Z", "content": None, "rating": 4, "lang": "english", "likely_hinglish": 0},
    ]
    df = pd.DataFrame(data)
    report = check_quality(df, initial_count=2)
    assert report['status'] == 'FAIL'
    assert report['null_check'] == 'FAIL'

def test_quality_fail_rating():
    data = [
        {"reviewed_at": "2024-01-01T10:00:00Z", "content": "text text text", "rating": 6, "lang": "english", "likely_hinglish": 0},
    ]
    df = pd.DataFrame(data)
    report = check_quality(df, initial_count=1)
    assert report['status'] == 'FAIL'
    assert report['rating_sanity'] == 'FAIL'

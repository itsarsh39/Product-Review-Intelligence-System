import pandas as pd
import numpy as np
from src.impact import compute_impact

def test_impact_synthetic():
    np.random.seed(42)
    n = 1000
    
    # Generate synthetic data
    theme_1 = np.random.binomial(1, 0.3, n)
    theme_2 = np.random.binomial(1, 0.1, n)
    word_count = np.random.randint(5, 50, n)
    version_group = np.random.choice(['1.0', '1.1', 'Other'], n)
    review_month = np.random.choice(['2024-01', '2024-02'], n)
    
    # Plant a known effect: theme_1 penalty -1.0, theme_2 penalty -0.5
    base_rating = 4.5
    rating_continuous = base_rating - (1.0 * theme_1) - (0.5 * theme_2) + np.random.normal(0, 0.5, n)
    rating = np.clip(np.round(rating_continuous), 1, 5)
    
    df = pd.DataFrame({
        'lang': 'english',
        'rating': rating,
        'theme_theme_1': theme_1,
        'theme_theme_2': theme_2,
        'word_count': word_count,
        'app_version': version_group,
        'review_month': review_month
    })
    
    # Mock taxonomy
    import yaml
    from unittest.mock import patch, mock_open
    mock_yaml = "themes:\n  - id: theme_1\n  - id: theme_2\n"
    
    with patch("builtins.open", mock_open(read_data=mock_yaml)):
        res = compute_impact(df)
    
    assert len(res) == 2
    t1_res = res[res['theme'] == 'theme_1'].iloc[0]
    t2_res = res[res['theme'] == 'theme_2'].iloc[0]
    
    assert t1_res['rating_penalty'] < -0.7
    assert t2_res['rating_penalty'] < -0.2

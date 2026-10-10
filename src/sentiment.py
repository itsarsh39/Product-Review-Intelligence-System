import pandas as pd
import logging
from transformers import pipeline
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from src.config import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class SentimentScorer:
    def __init__(self):
        self.use_vader = config['sentiment'].get('use_vader_fallback', False)
        if self.use_vader:
            logging.info("Using VADER for sentiment analysis.")
            self.analyzer = SentimentIntensityAnalyzer()
        else:
            model_id = config['sentiment']['model_id']
            logging.info(f"Using {model_id} for sentiment analysis.")
            # return_all_scores is deprecated in favor of top_k=None, but we can just use top label if needed.
            # To get P(pos) - P(neg), we need top_k=None.
            self.nlp = pipeline("sentiment-analysis", model=model_id, tokenizer=model_id, truncation=True, max_length=config['sentiment']['max_tokens'], top_k=None)
            
    def score_vader(self, text):
        if not isinstance(text, str):
            return "neutral", 0.0
        scores = self.analyzer.polarity_scores(text)
        comp = scores['compound']
        if comp >= 0.05:
            label = "positive"
        elif comp <= -0.05:
            label = "negative"
        else:
            label = "neutral"
        return label, comp

    def score_roberta(self, texts):
        results = []
        try:
            # preds is a list of lists (each inner list has dicts for labels)
            preds = self.nlp(texts)
            for p_list in preds:
                scores_dict = {d['label'].lower(): d['score'] for d in p_list}
                p_pos = scores_dict.get('positive', 0)
                p_neg = scores_dict.get('negative', 0)
                
                signed_score = p_pos - p_neg
                
                # Determine top label manually
                top_label = max(scores_dict, key=scores_dict.get)
                results.append((top_label, signed_score))
        except Exception as e:
            logging.error(f"Error scoring batch: {e}")
            results = [("neutral", 0.0)] * len(texts)
        return results

    def score_reviews(self, df: pd.DataFrame) -> pd.DataFrame:
        if len(df) == 0:
            return df
            
        texts = df['content'].fillna("").tolist()
        labels = []
        scores = []
        
        if self.use_vader:
            for text in texts:
                l, s = self.score_vader(text)
                labels.append(l)
                scores.append(s)
        else:
            batch_size = config['sentiment']['batch_size']
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i+batch_size]
                res = self.score_roberta(batch)
                for l, s in res:
                    labels.append(l)
                    scores.append(s)
                    
        df['sentiment_label'] = labels
        df['sentiment_score'] = scores
        return df
        
def report_agreement(df: pd.DataFrame):
    if len(df) == 0:
        return
        
    def rating_bucket(r):
        if r <= 2: return "1-2"
        if r == 3: return "3"
        return "4-5"
        
    df['rating_bucket'] = df['rating'].apply(rating_bucket)
    cm = pd.crosstab(df['sentiment_label'], df['rating_bucket'])
    logging.info(f"\nConfusion Matrix (Sentiment vs Rating):\n{cm}")
    
    mismatch_pos = df[(df['sentiment_label'] == 'positive') & (df['rating'] <= 2)]
    mismatch_neg = df[(df['sentiment_label'] == 'negative') & (df['rating'] >= 4)]
    
    if len(mismatch_pos) > 0:
        logging.info(f"Mismatch (Pos Sentiment, Low Rating) Sample:\n{mismatch_pos[['content', 'rating']].head(3).to_dict('records')}")
    if len(mismatch_neg) > 0:
        logging.info(f"Mismatch (Neg Sentiment, High Rating) Sample:\n{mismatch_neg[['content', 'rating']].head(3).to_dict('records')}")

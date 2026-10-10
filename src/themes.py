import pandas as pd
import yaml
import re
import numpy as np
import logging
from pathlib import Path
from sentence_transformers import SentenceTransformer
from src.config import config, BASE_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class ThemeTagger:
    def __init__(self):
        self.taxonomy_path = BASE_DIR / config['themes']['taxonomy_path']
        with open(self.taxonomy_path, "r", encoding="utf-8") as f:
            self.taxonomy = yaml.safe_load(f)['themes']
            
        model_id = config['themes']['embedding_model']
        logging.info(f"Loading SentenceTransformer: {model_id}")
        self.model = SentenceTransformer(model_id)
        self.threshold = config['themes']['similarity_threshold']
        
        self.theme_embeddings = {}
        for theme in self.taxonomy:
            embeddings = self.model.encode(theme['seed_phrases'])
            self.theme_embeddings[theme['id']] = np.mean(embeddings, axis=0)
            
    def compute_cosine(self, vec1, vec2):
        if np.linalg.norm(vec1) == 0 or np.linalg.norm(vec2) == 0:
            return 0.0
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
        
    def tag_reviews(self, df: pd.DataFrame) -> pd.DataFrame:
        if len(df) == 0:
            return df
            
        texts = df['content'].fillna("").tolist()
        logging.info("Encoding reviews...")
        review_embeddings = self.model.encode(texts, show_progress_bar=True)
        
        for theme in self.taxonomy:
            theme_id = theme['id']
            df[f'theme_{theme_id}'] = 0
            
            keywords = theme.get('keywords', [])
            if keywords:
                pattern = re.compile(r'\b(' + '|'.join(keywords) + r')\b', re.IGNORECASE)
            else:
                pattern = None
                
            theme_vec = self.theme_embeddings[theme_id]
            
            for i, text in enumerate(texts):
                score = self.compute_cosine(review_embeddings[i], theme_vec)
                
                has_keyword = False
                if pattern and pattern.search(text):
                    has_keyword = True
                    
                if score >= self.threshold or has_keyword:
                    df.at[df.index[i], f'theme_{theme_id}'] = 1
                    
        primary_themes = []
        for i in range(len(texts)):
            max_score = 0
            best_theme = "Other"
            
            for theme in self.taxonomy:
                theme_id = theme['id']
                if df.at[df.index[i], f'theme_{theme_id}'] == 1:
                    score = self.compute_cosine(review_embeddings[i], self.theme_embeddings[theme_id])
                    if score > max_score:
                        max_score = score
                        best_theme = theme_id
            primary_themes.append(best_theme)
            
        df['primary_theme'] = primary_themes
        return df

import json
from pathlib import Path
import os
import sys

BASE_DIR = Path(__file__).parent.parent

def render_readme():
    metrics_path = BASE_DIR / "data" / "processed" / "metrics.json"
    readme_path = BASE_DIR / "README.md"
    
    if not metrics_path.exists() or not readme_path.exists():
        return
        
    with open(metrics_path, "r", encoding="utf-8") as f:
        metrics = json.load(f)
        
    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    # Validation results
    val_status = metrics.get('validation', 'pending: gold set not yet labeled')
    if val_status == 'complete':
        acc = metrics.get('sentiment_accuracy', 0)
        val_text = f"Sentiment Accuracy: {acc:.1%}"
    else:
        val_text = val_status
        
    content = content.replace("{{VALIDATION_RESULTS}}", val_text)
    
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(content)

if __name__ == "__main__":
    render_readme()

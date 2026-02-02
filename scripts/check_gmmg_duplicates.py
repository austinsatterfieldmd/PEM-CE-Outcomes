"""Quick check for GMMG-CONCEPT duplicates."""
import json
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import os
import requests
from dotenv import load_dotenv

load_dotenv()

with open('data/checkpoints/stage2_tagged_multiple_myeloma.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

def build_text(q):
    parts = []
    stem = q.get('question_stem', '')
    if stem:
        parts.append(f'Question: {stem}')
    correct = q.get('correct_answer', '')
    if correct:
        parts.append(f'Correct: {correct}')
    incorrect = q.get('incorrect_answers', [])
    for ans in incorrect:
        if ans:
            parts.append(f'Incorrect: {ans}')
    return ' | '.join(parts)

texts = [build_text(q) for q in data]
api_key = os.getenv('OPENROUTER_API_KEY')
headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
all_embeddings = []
print("Getting embeddings...")
for i in range(0, len(texts), 100):
    batch = texts[i:i + 100]
    response = requests.post('https://openrouter.ai/api/v1/embeddings', headers=headers,
                            json={'input': batch, 'model': 'openai/text-embedding-3-small'}, timeout=60)
    all_embeddings.extend([item['embedding'] for item in response.json()['data']])

embeddings = np.array(all_embeddings)
sim_matrix = cosine_similarity(embeddings)
qid_to_idx = {q['question_id']: i for i, q in enumerate(data)}

print("\nChecking GMMG-CONCEPT questions (Q2223, Q2224, Q2226):")
for qid in [2223, 2224, 2226]:
    idx = qid_to_idx[qid]
    similar = np.where(sim_matrix[idx] >= 0.90)[0]
    if len(similar) > 1:
        print(f'\nQ{qid} is >= 90% similar to:')
        for sim_idx in similar:
            if sim_idx != idx:
                sim_qid = data[sim_idx]['question_id']
                print(f'  Q{sim_qid}: {sim_matrix[idx][sim_idx]:.3f}')

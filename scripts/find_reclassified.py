"""Find questions where Stage 1 reclassified the disease differently than Excel."""
import json

with open('data/checkpoints/heme_tagged_20260202_205405.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

results = data['results']

# Find questions where Stage 1 changed the disease classification
reclassified = []
for q in results:
    original = q.get('disease_state')  # From Excel STAGE1_disease_state

    # Check models' disease_state tags
    gpt = q.get('gpt_tags', {})
    claude = q.get('claude_tags', {})
    gemini = q.get('gemini_tags', {})

    gpt_disease = gpt.get('disease_state')
    claude_disease = claude.get('disease_state')
    gemini_disease = gemini.get('disease_state')

    # Check final_tags disease_state
    final = q.get('final_tags', {}).get('disease_state')

    # Look for cases where models tagged a different disease than original
    all_diseases = [gpt_disease, claude_disease, gemini_disease, final]
    different_diseases = [d for d in all_diseases if d and d != original]

    if different_diseases:
        reclassified.append({
            'source_id': q.get('source_id'),
            'original': original,
            'gpt_disease': gpt_disease,
            'claude_disease': claude_disease,
            'gemini_disease': gemini_disease,
            'final_disease': final,
            'activities': q.get('activities', ''),
            'question_stem': q.get('question_stem', ''),
            'correct_answer': q.get('correct_answer', ''),
            'incorrect_answers': q.get('incorrect_answers', [])
        })

print(f'Questions where disease was reclassified by models: {len(reclassified)}')

for q in reclassified:
    print()
    print('=' * 80)
    print(f'Source ID: {q["source_id"]}')
    print(f'Original (Excel): {q["original"]}')
    print(f'GPT: {q["gpt_disease"]} | Claude: {q["claude_disease"]} | Gemini: {q["gemini_disease"]}')
    print(f'Final disease_state: {q["final_disease"]}')
    act = q['activities']
    if len(act) > 120:
        print(f'Activity: {act[:120]}...')
    else:
        print(f'Activity: {act}')
    stem = q['question_stem']
    if len(stem) > 500:
        print(f'Stem: {stem[:500]}...')
    else:
        print(f'Stem: {stem}')
    print(f'Correct: {q["correct_answer"]}')
    for i, ans in enumerate(q['incorrect_answers'][:4], 1):
        if len(ans) > 80:
            print(f'Wrong {i}: {ans[:80]}...')
        else:
            print(f'Wrong {i}: {ans}')

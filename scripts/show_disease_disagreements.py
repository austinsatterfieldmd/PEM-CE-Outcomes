"""Quick script to show disease field disagreements in heme batch."""
import json

with open('data/checkpoints/heme_tagged_20260202_205405.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

results = data['results']

# Check review_reason for disease-related flags
disease_issues = []
for q in results:
    review_reason = q.get('review_reason', '')
    if review_reason and ('disease' in review_reason.lower()):
        disease_issues.append(q)

print(f'Questions with disease-related review flags: {len(disease_issues)}')

for q in disease_issues:
    print()
    print('=' * 80)
    print(f'Source ID: {q.get("source_id")}')
    print(f'Disease State: {q.get("disease_state")}')
    print(f'Review Reason: {q.get("review_reason")}')

    # Show the specific disease field disagreements
    field_votes = q.get('field_votes', {})
    for field_name in ['disease_type_1', 'disease_type_2', 'disease_stage']:
        fv = field_votes.get(field_name)
        if fv and fv.get('agreement') != 'unanimous':
            print(f'  {field_name}: GPT={fv.get("gpt_value")} | Claude={fv.get("claude_value")} | Gemini={fv.get("gemini_value")} -> Final={fv.get("final_value")}')

    act = q.get('activities', '')
    if len(act) > 120:
        print(f'Activity: {act[:120]}...')
    else:
        print(f'Activity: {act}')

    stem = q.get('question_stem', '')
    if len(stem) > 400:
        print(f'Stem: {stem[:400]}...')
    else:
        print(f'Stem: {stem}')

    print(f'Correct: {q.get("correct_answer", "")}')

    for i, ans in enumerate(q.get('incorrect_answers', []), 1):
        if len(ans) > 100:
            print(f'Wrong {i}: {ans[:100]}...')
        else:
            print(f'Wrong {i}: {ans}')

import json
from collections import Counter

# Load the checkpoint
with open('data/checkpoints/stage2_tagged_multiple_myeloma.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Get last 25 questions
last_25 = data[-25:]

# Track correction patterns
llm_wrong_you_fixed = []  # LLM had a value, you changed it
llm_null_you_added = []   # LLM had null, you added value
llm_value_you_cleared = [] # LLM had value, you cleared it

for q in last_25:
    if not q.get('human_reviewed', False):
        continue

    edited_fields = q.get('human_edited_fields', []) or []
    if not edited_fields:
        continue

    qid = q.get('question_id', 'unknown')

    gpt = q.get('gpt_tags', {}) or {}
    claude = q.get('claude_tags', {}) or {}
    gemini = q.get('gemini_tags', {}) or {}
    final = q.get('final_tags', {}) or {}

    for field in edited_fields:
        g_val = gpt.get(field)
        c_val = claude.get(field)
        ge_val = gemini.get(field)
        f_val = final.get(field)

        # Determine LLM consensus
        votes = [g_val, c_val, ge_val]
        non_null = [v for v in votes if v]

        # What would the system have picked?
        if non_null:
            vote_counts = Counter(non_null)
            llm_pick = vote_counts.most_common(1)[0][0] if vote_counts else None
        else:
            llm_pick = None

        entry = {
            'qid': qid,
            'field': field,
            'gpt': g_val,
            'claude': c_val,
            'gemini': ge_val,
            'llm_consensus': llm_pick,
            'your_value': f_val
        }

        if llm_pick and f_val and str(llm_pick) != str(f_val):
            llm_wrong_you_fixed.append(entry)
        elif not llm_pick and f_val:
            llm_null_you_added.append(entry)
        elif llm_pick and not f_val:
            llm_value_you_cleared.append(entry)

print('='*90)
print('CATEGORY 1: LLM HAD A VALUE, YOU CHANGED IT (%d cases)' % len(llm_wrong_you_fixed))
print('='*90)
for e in llm_wrong_you_fixed:
    print('')
    print('Q%s - %s:' % (e['qid'], e['field']))
    print('  LLM consensus: %r' % e['llm_consensus'])
    print('  YOUR fix:      %r' % e['your_value'])
    print('  (GPT=%r | Claude=%r | Gemini=%r)' % (e['gpt'], e['claude'], e['gemini']))

print('')
print('='*90)
print('CATEGORY 2: LLM HAD NULL, YOU ADDED A VALUE (%d cases)' % len(llm_null_you_added))
print('='*90)
for e in llm_null_you_added:
    print('')
    print('Q%s - %s:' % (e['qid'], e['field']))
    print('  LLM consensus: NULL')
    print('  YOUR value:    %r' % e['your_value'])

print('')
print('='*90)
print('CATEGORY 3: LLM HAD A VALUE, YOU CLEARED IT (%d cases)' % len(llm_value_you_cleared))
print('='*90)
for e in llm_value_you_cleared:
    print('')
    print('Q%s - %s:' % (e['qid'], e['field']))
    print('  LLM consensus: %r' % e['llm_consensus'])
    print('  YOU cleared to: (empty)')
    print('  (GPT=%r | Claude=%r | Gemini=%r)' % (e['gpt'], e['claude'], e['gemini']))

print('')
print('='*90)
print('SUMMARY')
print('='*90)
print('LLM wrong, you fixed:   %d' % len(llm_wrong_you_fixed))
print('LLM null, you added:    %d' % len(llm_null_you_added))
print('LLM value, you cleared: %d' % len(llm_value_you_cleared))
print('TOTAL YOUR DISAGREEMENTS: %d' % (len(llm_wrong_you_fixed) + len(llm_null_you_added) + len(llm_value_you_cleared)))

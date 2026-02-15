"""Normalize tag values in Supabase to collapse duplicates."""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from supabase import create_client
import os
from dotenv import load_dotenv
load_dotenv()

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_KEY') or os.getenv('SUPABASE_KEY')
sb = create_client(url, key)

DRY_RUN = '--apply' not in sys.argv

if DRY_RUN:
    print("=== DRY RUN (pass --apply to execute) ===\n")

total_updates = 0

def normalize_field(field: str, old_value: str, new_value: str):
    """Update all rows where field == old_value to new_value."""
    global total_updates
    r = sb.table('tags').select('question_id').eq(field, old_value).execute()
    count = len(r.data)
    if count == 0:
        return
    print(f"  {field}: '{old_value}' -> '{new_value}' ({count} rows)")
    total_updates += count
    if not DRY_RUN:
        # Update in batches
        for row in r.data:
            sb.table('tags').update({field: new_value}).eq('question_id', row['question_id']).eq(field, old_value).execute()


def normalize_specific(field: str, question_id: int, new_value: str):
    """Update a specific question's field."""
    global total_updates
    if not DRY_RUN:
        sb.table('tags').update({field: new_value}).eq('question_id', question_id).execute()
    print(f"  QID {question_id} {field} -> '{new_value}'")
    total_updates += 1


# ============================================================
# DRUG CLASS NORMALIZATIONS
# ============================================================
print("=" * 60)
print("DRUG CLASS NORMALIZATIONS")
print("=" * 60)

# 1. Immune checkpoint inhibitor variants -> Immune checkpoint inhibitor
print("\n--- Immune checkpoint inhibitor ---")
ici_variants = [
    'Immune checkpoint inhibitor (PD-L1)',
    'Immune checkpoint inhibitor (PD-1)',
    'Immune checkpoint inhibitor (CTLA-4)',
    'Anti-PD-1/PD-L1',
    'Anti-PD-L1',
]
for variant in ici_variants:
    for field in ['drug_class_1', 'drug_class_2', 'drug_class_3']:
        normalize_field(field, variant, 'Immune checkpoint inhibitor')

# 2. All CAR-T variants -> CAR-T cell therapy
print("\n--- CAR-T cell therapy ---")
for variant in ['CAR-T therapy', 'Cell therapy']:
    for field in ['drug_class_1', 'drug_class_2', 'drug_class_3']:
        normalize_field(field, variant, 'CAR-T cell therapy')

# 3. JAK inhibitor variants -> JAK inhibitor
print("\n--- JAK inhibitor ---")
jak_variants = ['JAK1/2 inhibitor', 'JAK1/JAK2 inhibitor', 'JAK1 inhibitor', 'JAK2/ACVR1 inhibitor']
for variant in jak_variants:
    for field in ['drug_class_1', 'drug_class_2', 'drug_class_3']:
        normalize_field(field, variant, 'JAK inhibitor')

# 4. IMiD variant (NOT CELMoD)
print("\n--- IMiD ---")
for field in ['drug_class_1', 'drug_class_2', 'drug_class_3']:
    normalize_field(field, 'Immunomodulatory drug (IMiD)', 'IMiD')

# 5. HMA -> Hypomethylating agent (HMA)
print("\n--- HMA ---")
for field in ['drug_class_1', 'drug_class_2', 'drug_class_3']:
    normalize_field(field, 'HMA', 'Hypomethylating agent (HMA)')

# 6. TKI case normalization
print("\n--- Tyrosine kinase inhibitor ---")
for field in ['drug_class_1', 'drug_class_2', 'drug_class_3']:
    normalize_field(field, 'tyrosine kinase inhibitor', 'Tyrosine kinase inhibitor')

# 7. E-selectin
print("\n--- E-selectin antagonist ---")
for field in ['drug_class_1', 'drug_class_2', 'drug_class_3']:
    normalize_field(field, 'E-selectin inhibitor', 'E-selectin antagonist')

# 8. BTK inhibitor -> Covalent or Non-covalent
print("\n--- BTK inhibitor reclassification ---")
covalent_qids = [4972, 5082, 5186, 5193, 5194, 5195, 5196, 5478, 5482, 5487, 5506, 5514, 5613, 5626]
noncovalent_qids = [4844, 4859, 5266]

for qid in covalent_qids:
    normalize_specific('drug_class_1', qid, 'Covalent BTKi')
for qid in noncovalent_qids:
    normalize_specific('drug_class_1', qid, 'Non-covalent BTKi')

# ============================================================
# TOPIC NORMALIZATIONS
# ============================================================
print("\n" + "=" * 60)
print("TOPIC NORMALIZATIONS")
print("=" * 60)

# Dosing -> Dose optimization
print("\n--- Dose optimization ---")
normalize_field('topic', 'Dosing', 'Dose optimization')

# Imaging interpretation -> Imaging
print("\n--- Imaging ---")
normalize_field('topic', 'Imaging interpretation', 'Imaging')

# ============================================================
# MOVE NON-ONCOLOGY NEUROENDOCRINE TO TOP OF QUEUE
# ============================================================
print("\n" + "=" * 60)
print("NON-ONCOLOGY NEUROENDOCRINE -> TOP OF REVIEW QUEUE")
print("=" * 60)

r = sb.table('tags').select('question_id').eq('topic', 'Non-oncology - Neuroendocrine').execute()
if r.data:
    qid = r.data[0]['question_id']
    print(f"  QID {qid}: setting needs_review=true, review_reason='non-oncology topic flagged for verification'")
    if not DRY_RUN:
        sb.table('tags').update({
            'needs_review': True,
            'review_reason': 'non-oncology topic flagged for verification',
        }).eq('question_id', qid).execute()
    total_updates += 1

print(f"\n{'=' * 60}")
print(f"TOTAL UPDATES: {total_updates}")
if DRY_RUN:
    print("(DRY RUN - no changes made. Pass --apply to execute)")

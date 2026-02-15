"""Round 2: Normalize tag values across all fields in Supabase."""
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
        for row in r.data:
            sb.table('tags').update({field: new_value}).eq('question_id', row['question_id']).eq(field, old_value).execute()


# ============================================================
# 1. METASTATIC SITE: Brain/CNS -> CNS metastases
# ============================================================
print("=" * 60)
print("METASTATIC SITE NORMALIZATIONS")
print("=" * 60)

print("\n--- Brain/CNS -> CNS metastases ---")
for variant in ['Brain', 'Brain metastases', 'CNS']:
    for field in ['metastatic_site_1', 'metastatic_site_2', 'metastatic_site_3']:
        normalize_field(field, variant, 'CNS metastases')

# ============================================================
# 2. TOXICITY TYPE NORMALIZATIONS
# ============================================================
print("\n" + "=" * 60)
print("TOXICITY TYPE NORMALIZATIONS")
print("=" * 60)

tox_fields = ['toxicity_type_1', 'toxicity_type_2', 'toxicity_type_3', 'toxicity_type_4', 'toxicity_type_5']

print("\n--- Cytokine release syndrome (CRS) ---")
for variant in ['CRS', 'Cytokine release syndrome']:
    for field in tox_fields:
        normalize_field(field, variant, 'Cytokine release syndrome (CRS)')

print("\n--- Infusion-related reaction ---")
for variant in ['Infusion reaction', 'Infusion reactions', 'Infusion-related reactions']:
    for field in tox_fields:
        normalize_field(field, variant, 'Infusion-related reaction')

print("\n--- Mucositis/stomatitis ---")
for variant in ['Stomatitis', 'Mucositis']:
    for field in tox_fields:
        normalize_field(field, variant, 'Mucositis/stomatitis')

print("\n--- QTc prolongation ---")
for field in tox_fields:
    normalize_field(field, 'QT prolongation', 'QTc prolongation')

print("\n--- Arthralgias ---")
for field in tox_fields:
    normalize_field(field, 'Arthralgia', 'Arthralgias')

print("\n--- Bone fractures ---")
for field in tox_fields:
    normalize_field(field, 'Bone fracture', 'Bone fractures')

print("\n--- Lipase elevations ---")
for field in tox_fields:
    normalize_field(field, 'Lipase elevation', 'Lipase elevations')

print("\n--- GI toxicity ---")
for field in tox_fields:
    normalize_field(field, 'Gastrointestinal toxicity', 'GI toxicity')

print("\n--- Cardiac toxicity ---")
for field in tox_fields:
    normalize_field(field, 'Cardiotoxicity', 'Cardiac toxicity')

print("\n--- Hypersensitivity reaction ---")
for variant in ['Hypersensitivity', 'Hypersensitivity reactions']:
    for field in tox_fields:
        normalize_field(field, variant, 'Hypersensitivity reaction')

# ============================================================
# 3. TOXICITY ORGAN NORMALIZATIONS
# ============================================================
print("\n" + "=" * 60)
print("TOXICITY ORGAN NORMALIZATIONS")
print("=" * 60)

print("\n--- GI -> Gastrointestinal ---")
normalize_field('toxicity_organ', 'GI', 'Gastrointestinal')

print("\n--- Cardiac -> Cardiovascular ---")
normalize_field('toxicity_organ', 'Cardiac', 'Cardiovascular')

# ============================================================
# 4. DRUG CLASS: SERD -> Oral SERD
# ============================================================
print("\n" + "=" * 60)
print("DRUG CLASS NORMALIZATIONS (Round 2)")
print("=" * 60)

print("\n--- SERD -> Oral SERD ---")
for field in ['drug_class_1', 'drug_class_2', 'drug_class_3']:
    normalize_field(field, 'SERD', 'Oral SERD')

# ============================================================
# 5. DRUG TARGET NORMALIZATIONS
# ============================================================
print("\n" + "=" * 60)
print("DRUG TARGET NORMALIZATIONS")
print("=" * 60)

target_fields = ['drug_target_1', 'drug_target_2', 'drug_target_3']

print("\n--- Trop-2 -> TROP-2 ---")
for field in target_fields:
    normalize_field(field, 'Trop-2', 'TROP-2')

print("\n--- BCR-ABL -> BCR-ABL1 ---")
for field in target_fields:
    normalize_field(field, 'BCR-ABL', 'BCR-ABL1')

print("\n--- BCR-ABL myristoyl pocket -> BCR-ABL1 myristoyl pocket ---")
for field in target_fields:
    normalize_field(field, 'BCR-ABL myristoyl pocket', 'BCR-ABL1 myristoyl pocket')

print("\n--- Sodium channel -> Sodium channels ---")
for field in target_fields:
    normalize_field(field, 'Sodium channel', 'Sodium channels')

print("\n--- PI3K delta -> PI3K\u03b4 ---")
for field in target_fields:
    normalize_field(field, 'PI3K delta', 'PI3K\u03b4')

print("\n--- BCL2 -> BCL-2 ---")
for field in target_fields:
    normalize_field(field, 'BCL2', 'BCL-2')

# ============================================================
# 6. BIOMARKER NORMALIZATIONS
# ============================================================
print("\n" + "=" * 60)
print("BIOMARKER NORMALIZATIONS")
print("=" * 60)

bio_fields = ['biomarker_1', 'biomarker_2', 'biomarker_3', 'biomarker_4', 'biomarker_5']

print("\n--- Ki67-high -> Ki-67-high ---")
for field in bio_fields:
    normalize_field(field, 'Ki67-high', 'Ki-67-high')

print("\n--- TP53 mutated -> TP53 mutation ---")
for field in bio_fields:
    normalize_field(field, 'TP53 mutated', 'TP53 mutation')

print("\n--- IDH1 mutated -> IDH1 mutation ---")
for field in bio_fields:
    normalize_field(field, 'IDH1 mutated', 'IDH1 mutation')

print("\n--- KMT2A rearrangement -> KMT2Ar (MLL-rearranged) ---")
for field in bio_fields:
    normalize_field(field, 'KMT2A rearrangement', 'KMT2Ar (MLL-rearranged)')

print("\n--- Circulating tumor DNA (ctDNA) -> ctDNA ---")
for field in bio_fields:
    normalize_field(field, 'Circulating tumor DNA (ctDNA)', 'ctDNA')

# ============================================================
# 7. DISEASE STAGE NORMALIZATIONS
# ============================================================
print("\n" + "=" * 60)
print("DISEASE STAGE NORMALIZATIONS")
print("=" * 60)

print("\n--- Advanced stage -> Advanced-stage ---")
normalize_field('disease_stage', 'Advanced stage', 'Advanced-stage')

print("\n--- Limited stage -> Limited-stage ---")
normalize_field('disease_stage', 'Limited stage', 'Limited-stage')

# ============================================================
# 8. EFFICACY ENDPOINT NORMALIZATIONS
# ============================================================
print("\n" + "=" * 60)
print("EFFICACY ENDPOINT NORMALIZATIONS")
print("=" * 60)

eff_fields = ['efficacy_endpoint_1', 'efficacy_endpoint_2', 'efficacy_endpoint_3']

print("\n--- PFS -> Progression-free survival (PFS) ---")
for field in eff_fields:
    normalize_field(field, 'PFS', 'Progression-free survival (PFS)')

print("\n--- OS -> Overall survival (OS) ---")
for field in eff_fields:
    normalize_field(field, 'OS', 'Overall survival (OS)')

print("\n--- ORR -> Overall response rate (ORR) ---")
for field in eff_fields:
    normalize_field(field, 'ORR', 'Overall response rate (ORR)')

print("\n--- Objective response rate (ORR) -> Overall response rate (ORR) ---")
for field in eff_fields:
    normalize_field(field, 'Objective response rate (ORR)', 'Overall response rate (ORR)')

print("\n--- Invasive disease-free survival (IDFS) -> (iDFS) ---")
for field in eff_fields:
    normalize_field(field, 'Invasive disease-free survival (IDFS)', 'Invasive disease-free survival (iDFS)')

# ============================================================
# 9. RESISTANCE MECHANISM NORMALIZATIONS
# ============================================================
print("\n" + "=" * 60)
print("RESISTANCE MECHANISM NORMALIZATIONS")
print("=" * 60)

print("\n--- BTK-C481S mutation / C481S -> C481S mutation ---")
for variant in ['BTK-C481S mutation', 'C481S']:
    normalize_field('resistance_mechanism', variant, 'C481S mutation')

# ============================================================
# SUMMARY
# ============================================================
print(f"\n{'=' * 60}")
print(f"TOTAL UPDATES: {total_updates}")
if DRY_RUN:
    print("(DRY RUN - no changes made. Pass --apply to execute)")

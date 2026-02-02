"""
Check tagging status for a disease checkpoint.
Properly accounts for non-oncology questions and unanimous auto-accepts.
"""
import json
import sys
from pathlib import Path

def check_status(disease_state: str = "multiple_myeloma"):
    checkpoint_path = Path(f"data/checkpoints/stage2_tagged_{disease_state}.json")

    if not checkpoint_path.exists():
        print(f"Checkpoint not found: {checkpoint_path}")
        return

    data = json.load(open(checkpoint_path, encoding='utf-8'))

    # Categorize questions
    active = []
    non_oncology = []

    for q in data:
        # Check if non-oncology
        if q.get('is_oncology') == False:
            non_oncology.append(q)
            continue

        # Check if topic is non-oncology
        topic = q.get('final_tags', {}).get('topic', '') or ''
        if 'Non-oncology' in topic:
            non_oncology.append(q)
            continue

        active.append(q)

    # Categorize active questions
    reviewed = [q for q in active if q.get('human_reviewed', False)]
    unanimous_auto = [q for q in active if not q.get('human_reviewed', False) and not q.get('needs_review', True)]
    needs_review = [q for q in active if not q.get('human_reviewed', False) and q.get('needs_review', True)]

    print('=' * 60)
    print(f'{disease_state.upper().replace("_", " ")} TAGGING STATUS')
    print('=' * 60)
    print(f'Total in checkpoint: {len(data)}')
    print(f'  - Removed (non-oncology): {len(non_oncology)}')
    print(f'  - Active oncology: {len(active)}')
    print()
    print(f'Active question status:')
    print(f'  - Human reviewed: {len(reviewed)}')
    print(f'  - Unanimous (auto-accepted): {len(unanimous_auto)}')
    print(f'  - NEEDS REVIEW: {len(needs_review)}')

    if needs_review:
        print()
        print('Questions needing review:')
        for q in needs_review:
            print(f'  - Q{q.get("question_id")} (agreement: {q.get("agreement_level", "?")})')

    print('=' * 60)

    # Return summary for programmatic use
    return {
        'total': len(data),
        'non_oncology': len(non_oncology),
        'active': len(active),
        'reviewed': len(reviewed),
        'unanimous': len(unanimous_auto),
        'needs_review': len(needs_review)
    }

if __name__ == "__main__":
    disease = sys.argv[1] if len(sys.argv) > 1 else "multiple_myeloma"
    check_status(disease)

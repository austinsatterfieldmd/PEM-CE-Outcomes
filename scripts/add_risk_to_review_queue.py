"""
Add risk stratification questions to review queue.

Updates the checkpoint to mark the 5 single-model risk stratification
questions as needing review, then syncs with the dashboard database.
"""

import json
import shutil
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

def main():
    # Load the review items
    review_file = PROJECT_ROOT / "data" / "checkpoints" / "risk_stratification_needs_review.json"
    with open(review_file, 'r', encoding='utf-8') as f:
        review_items = json.load(f)

    print(f"Found {len(review_items)} questions to add to review queue")

    # Load checkpoint
    checkpoint_path = PROJECT_ROOT / "data" / "checkpoints" / "stage2_tagged_multiple_myeloma.json"
    with open(checkpoint_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Create question_id lookup
    qid_to_idx = {q['question_id']: i for i, q in enumerate(data)}

    # Update questions to need review
    updated = 0
    for item in review_items:
        qid = item['question_id']
        if qid in qid_to_idx:
            idx = qid_to_idx[qid]
            data[idx]['needs_review'] = True
            data[idx]['review_reason'] = f"risk_stratification_single_model|{item['model_votes']}"

            # Also add the suggested risk value to final_tags.disease_type_1 if empty
            suggested_value = item['final_value']
            final_tags = data[idx].get('final_tags', {})
            current_dt1 = final_tags.get('disease_type_1')

            if not current_dt1 or not str(current_dt1).strip():
                if 'final_tags' not in data[idx]:
                    data[idx]['final_tags'] = {}
                data[idx]['final_tags']['disease_type_1'] = suggested_value
                print(f"  Q{qid}: Added suggested risk '{suggested_value}' to disease_type_1")

            updated += 1
            print(f"  Q{qid}: Marked for review (suggested: {suggested_value})")

    # Backup and save
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = checkpoint_path.with_suffix(f'.pre_review_queue_{timestamp}.json')
    shutil.copy(checkpoint_path, backup_path)
    print(f"\nBackup created: {backup_path}")

    with open(checkpoint_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Updated checkpoint: {checkpoint_path}")

    print(f"\nDone! {updated} questions marked for review.")
    print("Restart the dashboard backend to sync with database.")
    return 0


if __name__ == '__main__':
    exit(main())

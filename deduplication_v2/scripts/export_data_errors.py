"""
Export oncology data errors for manual review.
"""

import json
import pandas as pd
from pathlib import Path

# Paths
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"
PROJECT_ROOT = SCRIPT_DIR.parent.parent

# Load oncology QGDs
with open(DATA_DIR / "oncology_qgds.txt", "r") as f:
    oncology_qgds = set(int(line.strip()) for line in f if line.strip())

print(f"Loaded {len(oncology_qgds)} oncology QGDs")

# Load LLM triage results
with open(DATA_DIR / "llm_triage_results.json", "r", encoding="utf-8") as f:
    triage_data = json.load(f)

# Load source data for question details
source_df = pd.read_excel(PROJECT_ROOT / "data/raw/questions_deduplicated_collated_20260121_221852.xlsx")
qgd_to_row = {
    int(row["QUESTIONGROUPDESIGNATION"]): row
    for _, row in source_df.iterrows()
    if pd.notna(row["QUESTIONGROUPDESIGNATION"])
}

print(f"Loaded {len(qgd_to_row)} QGD rows")


def get_answers(row):
    """Extract correct and incorrect answers from a row."""
    if row is None or (isinstance(row, dict) and len(row) == 0):
        return "", []
    correct = str(row.get("OPTIMIZEDCORRECTANSWER", "")) if pd.notna(row.get("OPTIMIZEDCORRECTANSWER")) else ""
    incorrect = []
    for i in range(1, 10):
        col = f"IANSWER{i}"
        if col in row and pd.notna(row.get(col)):
            incorrect.append(str(row[col]))
    return correct, incorrect


# Find oncology data errors
data_error_rows = []

for result in triage_data["triage_results"]:
    verdict = result.get("llm_response", {}).get("verdict", "")
    if verdict != "SAME_QUESTION_DATA_ERROR":
        continue

    qgd_1 = result["qgd_1"]
    qgd_2 = result["qgd_2"]

    # Check if either QGD is oncology
    if qgd_1 not in oncology_qgds and qgd_2 not in oncology_qgds:
        continue

    row_1 = qgd_to_row.get(qgd_1, {})
    row_2 = qgd_to_row.get(qgd_2, {})

    correct_1, incorrect_1 = get_answers(row_1)
    correct_2, incorrect_2 = get_answers(row_2)

    # Get full stem from source data
    full_stem = ""
    if row_1 is not None:
        full_stem = str(row_1.get("OPTIMIZEDQUESTION", "")) if pd.notna(row_1.get("OPTIMIZEDQUESTION")) else ""

    data_error_rows.append({
        "QGD_A": qgd_1,
        "QGD_B": qgd_2,
        "Is_Oncology_A": "Yes" if qgd_1 in oncology_qgds else "No",
        "Is_Oncology_B": "Yes" if qgd_2 in oncology_qgds else "No",
        "Question_Stem": full_stem,
        "Answer_Similarity": result.get("answer_similarity", 0),
        "LLM_Reasoning": result.get("llm_response", {}).get("reasoning", ""),
        "Correct_Answer_A": correct_1,
        "Correct_Answer_B": correct_2,
        "Incorrect_Answers_A": " | ".join(incorrect_1),
        "Incorrect_Answers_B": " | ".join(incorrect_2),
    })

# Create DataFrame and save
df = pd.DataFrame(data_error_rows)
output_path = DATA_DIR / "oncology_data_errors_for_review_v2.xlsx"
df.to_excel(output_path, index=False)

print(f"\nExported {len(df)} oncology data error pairs to:")
print(f"  {output_path}")

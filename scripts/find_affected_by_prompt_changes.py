"""
Find questions most likely affected by the recent prompt changes to heme malignancy prompts.

Prompt changes made:
1. Trial inference rules - ALLOWED only for "Clinical efficacy" or "Study design" topics
2. Negative lead-in rules - For EXCEPT/NOT questions, tag INCORRECT options (not correct answer)
3. efficacy_endpoint conditional rules - Don't tag endpoints from distractors
4. Prophylaxis treatment tagging - Tag drug causing toxicity, not prophylactic agent
5. Medical terminology guidance - Use medical terms like "Dysgeusia" not "taste changes"

Usage:
    python scripts/find_affected_by_prompt_changes.py
    python scripts/find_affected_by_prompt_changes.py --output affected_questions.json
"""

import sqlite3
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "dashboard" / "data" / "questions.db"

# Heme malignancies we updated
HEME_DISEASES = ["CLL", "DLBCL", "FL", "MCL", "ALL",
                 "Chronic lymphocytic leukemia", "Diffuse large B-cell lymphoma",
                 "Follicular lymphoma", "Mantle cell lymphoma",
                 "Acute lymphoblastic leukemia"]

# Topics where trial inference IS allowed
TRIAL_INFERENCE_ALLOWED_TOPICS = ["Clinical efficacy", "Study design"]

# Lay terms that should be medical terms
LAY_TO_MEDICAL_TERMS = {
    "taste changes": "Dysgeusia",
    "hair loss": "Alopecia",
    "numbness": "Peripheral neuropathy",
    "tingling": "Peripheral neuropathy",
    "low blood counts": "Cytopenias",
}


def get_heme_questions(conn) -> List[Dict]:
    """Get all heme malignancy questions from the database."""
    cursor = conn.cursor()

    # Build disease filter
    disease_placeholders = ",".join(["?" for _ in HEME_DISEASES])

    query = f"""
        SELECT
            q.id,
            q.source_id,
            q.question_stem,
            q.correct_answer,
            q.incorrect_answers,
            t.topic,
            t.disease_state,
            t.disease_state_1,
            t.lead_in_type,
            t.trial_1, t.trial_2, t.trial_3, t.trial_4, t.trial_5,
            t.efficacy_endpoint_1, t.efficacy_endpoint_2, t.efficacy_endpoint_3,
            t.toxicity_type_1, t.toxicity_type_2, t.toxicity_type_3,
            t.toxicity_type_4, t.toxicity_type_5,
            t.treatment_1, t.treatment_2, t.treatment_3, t.treatment_4, t.treatment_5,
            t.needs_review,
            t.edited_by_user
        FROM questions q
        JOIN tags t ON q.id = t.question_id
        WHERE t.disease_state IN ({disease_placeholders})
           OR t.disease_state_1 IN ({disease_placeholders})
    """

    cursor.execute(query, HEME_DISEASES + HEME_DISEASES)

    columns = [desc[0] for desc in cursor.description]
    questions = [dict(zip(columns, row)) for row in cursor.fetchall()]

    return questions


def check_trial_inference_issue(q: Dict) -> Dict[str, Any]:
    """
    Check if question has trial tagged but topic doesn't allow inference.

    Issue: Trial was inferred for a topic where inference is NOT allowed.
    """
    topic = q.get("topic")
    trials = [q.get(f"trial_{i}") for i in range(1, 6)]
    trials = [t for t in trials if t]  # Filter None/empty

    if not trials:
        return None

    if topic and topic not in TRIAL_INFERENCE_ALLOWED_TOPICS:
        # Check if trial is actually in the question stem (explicit mention is OK)
        stem = (q.get("question_stem") or "").lower()

        # Check if any trial is NOT mentioned in stem (was inferred)
        inferred_trials = []
        for trial in trials:
            if trial.lower() not in stem:
                inferred_trials.append(trial)

        if inferred_trials:
            return {
                "issue": "trial_inference",
                "severity": "HIGH",
                "description": f"Trial '{', '.join(inferred_trials)}' inferred for topic '{topic}' - inference only allowed for Clinical efficacy/Study design",
                "trials": inferred_trials,
                "topic": topic
            }

    return None


def check_negative_leadin_issue(q: Dict) -> Dict[str, Any]:
    """
    Check if question has negative lead-in that might have tagging issues.

    Issue: For EXCEPT/NOT questions, we should tag INCORRECT options, not correct answer.
    This is hard to verify without re-tagging, so we flag all negative lead-ins for review.
    """
    lead_in = q.get("lead_in_type")

    if lead_in and "Negative" in lead_in:
        return {
            "issue": "negative_leadin",
            "severity": "MEDIUM",
            "description": f"Negative lead-in question - verify that INCORRECT options were tagged (not just correct answer)",
            "lead_in_type": lead_in
        }

    return None


def check_efficacy_endpoint_issue(q: Dict) -> Dict[str, Any]:
    """
    Check if efficacy_endpoint is tagged but topic is not Clinical efficacy.

    Issue: Endpoint may have been tagged from distractors instead of stem/correct answer.
    """
    topic = q.get("topic")
    endpoints = [q.get(f"efficacy_endpoint_{i}") for i in range(1, 4)]
    endpoints = [e for e in endpoints if e]

    if not endpoints:
        return None

    # If topic is not Clinical efficacy, endpoints should only be tagged if explicitly in stem
    if topic and topic != "Clinical efficacy":
        stem = (q.get("question_stem") or "").lower()
        correct = (q.get("correct_answer") or "").lower()

        # Check if any endpoint might have come from distractors
        potentially_from_distractors = []
        for endpoint in endpoints:
            endpoint_lower = endpoint.lower()
            # Check common endpoint abbreviations
            endpoint_terms = [endpoint_lower]
            if "pfs" in endpoint_lower or "progression" in endpoint_lower:
                endpoint_terms.extend(["pfs", "progression-free", "progression free"])
            if "os" in endpoint_lower or "overall survival" in endpoint_lower:
                endpoint_terms.extend(["os", "overall survival"])
            if "orr" in endpoint_lower or "response rate" in endpoint_lower:
                endpoint_terms.extend(["orr", "response rate", "overall response"])

            found_in_stem_or_correct = any(term in stem or term in correct for term in endpoint_terms)

            if not found_in_stem_or_correct:
                potentially_from_distractors.append(endpoint)

        if potentially_from_distractors:
            return {
                "issue": "efficacy_endpoint_source",
                "severity": "MEDIUM",
                "description": f"Endpoint '{', '.join(potentially_from_distractors)}' tagged for non-Clinical efficacy topic '{topic}' - verify it's from stem/correct answer, not distractors",
                "endpoints": potentially_from_distractors,
                "topic": topic
            }

    return None


def check_prophylaxis_treatment_issue(q: Dict) -> Dict[str, Any]:
    """
    Check if question is about Prophylaxis and might have wrong treatment tagged.

    Issue: Should tag drug CAUSING toxicity, not the prophylactic agent.
    """
    topic = q.get("topic")

    if topic and topic.lower() == "prophylaxis":
        treatments = [q.get(f"treatment_{i}") for i in range(1, 6)]
        treatments = [t for t in treatments if t]

        # Common prophylactic agents that should NOT be tagged
        prophylactic_agents = [
            "acyclovir", "valacyclovir", "rasburicase", "allopurinol",
            "tmp-smx", "bactrim", "septra", "dexrazoxane", "tocilizumab",
            "ivig", "g-csf", "filgrastim", "pegfilgrastim"
        ]

        flagged_treatments = []
        for t in treatments:
            if t and any(agent in t.lower() for agent in prophylactic_agents):
                flagged_treatments.append(t)

        if flagged_treatments:
            return {
                "issue": "prophylaxis_treatment",
                "severity": "HIGH",
                "description": f"Prophylaxis topic with prophylactic agent '{', '.join(flagged_treatments)}' tagged - should tag drug CAUSING toxicity instead",
                "treatments": flagged_treatments
            }
        elif treatments:
            return {
                "issue": "prophylaxis_review",
                "severity": "LOW",
                "description": f"Prophylaxis topic - verify treatment '{', '.join(treatments)}' is the drug causing toxicity, not the prophylactic",
                "treatments": treatments
            }

    return None


def check_medical_terminology_issue(q: Dict) -> Dict[str, Any]:
    """
    Check if toxicity fields contain lay terms instead of medical terminology.
    """
    toxicities = [q.get(f"toxicity_type_{i}") for i in range(1, 6)]
    toxicities = [t for t in toxicities if t]

    lay_terms_found = []
    for tox in toxicities:
        tox_lower = tox.lower()
        for lay_term, medical_term in LAY_TO_MEDICAL_TERMS.items():
            if lay_term in tox_lower and medical_term.lower() not in tox_lower:
                lay_terms_found.append((tox, lay_term, medical_term))

    if lay_terms_found:
        return {
            "issue": "medical_terminology",
            "severity": "LOW",
            "description": f"Lay terms in toxicity fields - should use medical terminology",
            "lay_terms": [(t[0], f"'{t[1]}' → '{t[2]}'") for t in lay_terms_found]
        }

    return None


def analyze_questions(questions: List[Dict]) -> Dict[str, Any]:
    """Analyze all questions and identify those affected by prompt changes."""

    affected = []

    for q in questions:
        issues = []

        # Run all checks
        checks = [
            check_trial_inference_issue,
            check_negative_leadin_issue,
            check_efficacy_endpoint_issue,
            check_prophylaxis_treatment_issue,
            check_medical_terminology_issue,
        ]

        for check in checks:
            result = check(q)
            if result:
                issues.append(result)

        if issues:
            # Calculate priority based on severity
            severity_weights = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
            priority_score = sum(severity_weights.get(i["severity"], 0) for i in issues)

            affected.append({
                "question_id": q["id"],
                "source_id": q.get("source_id"),
                "disease_state": q.get("disease_state") or q.get("disease_state_1"),
                "topic": q.get("topic"),
                "question_stem_preview": (q.get("question_stem") or "")[:100] + "...",
                "issues": issues,
                "priority_score": priority_score,
                "already_edited": q.get("edited_by_user", False),
                "needs_review": q.get("needs_review", False)
            })

    # Sort by priority score (highest first)
    affected.sort(key=lambda x: (-x["priority_score"], x["question_id"]))

    return affected


def print_summary(affected: List[Dict], total_questions: int):
    """Print summary of affected questions."""

    print("\n" + "=" * 70)
    print("PROMPT CHANGE IMPACT ANALYSIS")
    print("=" * 70)
    print(f"\nTotal heme malignancy questions analyzed: {total_questions}")
    print(f"Questions with potential issues: {len(affected)}")

    if not affected:
        print("\nNo questions appear to be affected by the prompt changes!")
        return

    # Count by issue type
    issue_counts = {}
    severity_counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}

    for q in affected:
        for issue in q["issues"]:
            issue_type = issue["issue"]
            issue_counts[issue_type] = issue_counts.get(issue_type, 0) + 1
            severity_counts[issue["severity"]] += 1

    print(f"\nBy Severity:")
    print(f"  HIGH:   {severity_counts['HIGH']} issues")
    print(f"  MEDIUM: {severity_counts['MEDIUM']} issues")
    print(f"  LOW:    {severity_counts['LOW']} issues")

    print(f"\nBy Issue Type:")
    for issue_type, count in sorted(issue_counts.items(), key=lambda x: -x[1]):
        print(f"  {issue_type}: {count}")

    # Show top 10 highest priority questions
    print(f"\n" + "-" * 70)
    print("TOP 10 QUESTIONS TO REVIEW (by priority)")
    print("-" * 70)

    for i, q in enumerate(affected[:10], 1):
        print(f"\n{i}. Question ID: {q['question_id']} (Priority: {q['priority_score']})")
        print(f"   Disease: {q['disease_state']}, Topic: {q['topic']}")
        print(f"   Preview: {q['question_stem_preview']}")
        print(f"   Issues:")
        for issue in q["issues"]:
            print(f"     [{issue['severity']}] {issue['description']}")
        if q["already_edited"]:
            print(f"   ⚠️  Already manually edited - review carefully")


def main():
    parser = argparse.ArgumentParser(description="Find questions affected by prompt changes")
    parser.add_argument("--output", "-o", help="Output JSON file path")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show all affected questions")
    args = parser.parse_args()

    if not DB_PATH.exists():
        print(f"Database not found: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        # Get all heme questions
        questions = get_heme_questions(conn)
        print(f"Found {len(questions)} heme malignancy questions in database")

        if not questions:
            print("No heme malignancy questions found. Have you imported data?")
            return

        # Analyze
        affected = analyze_questions(questions)

        # Print summary
        print_summary(affected, len(questions))

        # Show all if verbose
        if args.verbose and len(affected) > 10:
            print(f"\n" + "-" * 70)
            print(f"ALL AFFECTED QUESTIONS ({len(affected)} total)")
            print("-" * 70)
            for i, q in enumerate(affected[10:], 11):
                print(f"\n{i}. ID: {q['question_id']}, Disease: {q['disease_state']}, Topic: {q['topic']}")
                for issue in q["issues"]:
                    print(f"   [{issue['severity']}] {issue['issue']}")

        # Save to JSON if requested
        if args.output:
            output_path = Path(args.output)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "analysis_timestamp": datetime.now().isoformat(),
                    "total_questions_analyzed": len(questions),
                    "affected_count": len(affected),
                    "affected_questions": affected
                }, f, indent=2, ensure_ascii=False)
            print(f"\nFull results saved to: {output_path}")

    finally:
        conn.close()


if __name__ == "__main__":
    main()

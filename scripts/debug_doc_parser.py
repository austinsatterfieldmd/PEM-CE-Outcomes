"""Test the parser with list marker extraction."""
import sys
sys.path.insert(0, r"C:\Users\snair\OneDrive - MJH\Documents\GitHub\Steve-V2-Outcomes-Tagger\Automated-CE-Outcomes-Dashboard")

from src.core.services.outcomes_doc_parser import parse_outcomes_document

doc_path = r"C:\Users\snair\OneDrive - MJH\Documents\GitHub\Steve-V2-Outcomes-Tagger\Automated-CE-Outcomes-Dashboard\docs\PER Med Affairs _Outcomes Questions Review_Example.docx"

print(f"Parsing document: {doc_path}")
result = parse_outcomes_document(doc_path)

print(f"\nFilename: {result.filename}")
print(f"Questions Found: {len(result.questions)}")

if result.parse_warnings:
    print(f"\nWarnings ({len(result.parse_warnings)}):")
    for w in result.parse_warnings:
        print(f"  - {w}")

print("\n" + "="*60)
for q in result.questions:
    print(f"\nQuestion {q.question_number}:")
    print(f"  Stem: {q.question_stem[:70]}...")
    print(f"  Correct Answer: {q.correct_answer}")
    print(f"  Options ({len(q.options)}):")
    for opt in q.options:
        marker = " <-- CORRECT" if opt.startswith(f"{q.correct_answer}.") else ""
        # Truncate long options
        display = opt[:70] + "..." if len(opt) > 70 else opt
        print(f"    {display}{marker}")

print("\n\nDone!")

import sqlite3

db_path = r'c:\Users\snair\OneDrive - MJH\Documents\GitHub\Steve-V2-Outcomes-Tagger\Automated-CE-Outcomes-Dashboard\dashboard\data\questions.db'
conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute("SELECT question_id, disease_state_1, disease_state_2 FROM tags WHERE disease_state_2 IS NOT NULL AND disease_state_2 != ''")
rows = cur.fetchall()
print(f"Questions with disease_state_2 set: {len(rows)}")
for row in rows:
    print(f"  Q{row[0]}: disease_state_1={row[1]!r}, disease_state_2={row[2]!r}")

conn.close()

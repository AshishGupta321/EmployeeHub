
import os
import sqlite3
from pathlib import Path

import psycopg
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
SQLITE_DB = BASE_DIR / "EmployeeDB.db"

load_dotenv(BASE_DIR / ".env")
DATABASE_URL = os.environ["DATABASE_URL"]

# Read the original SQLite records
if not SQLITE_DB.exists():
    raise FileNotFoundError(f"Database not found: {SQLITE_DB}")

sqlite_conn = sqlite3.connect(SQLITE_DB)
sqlite_conn.row_factory = sqlite3.Row

columns = {
    row["name"]
    for row in sqlite_conn.execute("PRAGMA table_info(employees)")
}

if not columns:
    sqlite_conn.close()
    raise RuntimeError("The employees table was not found in EmployeeDB.db")

designation_column = (
    "desig" if "desig" in columns else "designation"
)

rows = sqlite_conn.execute(
    f"""
    SELECT id, name, age, salary, {designation_column}
    FROM employees
    ORDER BY id
    """
).fetchall()

sqlite_conn.close()

print(f"Found {len(rows)} records in SQLite.")

if not rows:
    raise RuntimeError(
        "No records found. Check that EmployeeDB.db is your original database."
    )

# Copy records to Neon without overwriting existing IDs
with psycopg.connect(DATABASE_URL) as pg_conn:
    with pg_conn.cursor() as cur:
        for row in rows:
            cur.execute(
                """
                INSERT INTO employees (id, name, age, salary, desig)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
                """,
                (
                    row["id"],
                    row["name"],
                    row["age"],
                    row["salary"],
                    row[designation_column],
                ),
            )

        cur.execute("SELECT COUNT(*) FROM employees")
        total = cur.fetchone()[0]

print(f"Migration finished. Neon now contains {total} employee records.")

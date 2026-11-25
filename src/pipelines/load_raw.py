import os
from datetime import date
import json
import argparse
import duckdb
from dotenv import load_dotenv

load_dotenv()

db_path = os.getenv("DUCKDB_PATH", "data/warehouse.duckdb")

def valid_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid date format: '{value}'. Expected format: YYYY-MM-DD")

parser = argparse.ArgumentParser(description="Load raw data into DuckDB")
parser.add_argument("--run-date", type=valid_date, required=True, help="Run date (YYYY-MM-DD)")
args = parser.parse_args()

run_date_str = str(args.run_date)
input_path = os.path.join("data", "raw", "orders", f"dt={run_date_str}", "orders.jsonl")
report_path = os.path.join("data", "staging", "orders", f"dt={run_date_str}", "validation_report.json")
safe_input_path = input_path.replace("\\","/")

if not os.path.exists(input_path):
    raise FileNotFoundError(f"Raw file not found: {input_path}")

if not os.path.exists(report_path):
    raise FileNotFoundError(
        f"Validation report not found: {report_path}. Run validate_orders.py first."
    )

with open(report_path, "r", encoding="utf-8") as f:
    report = json.load(f)

if report.get("status") != "PASSED":
    raise ValueError(
        f"Validation status is '{report.get('status')}'. Refusing to load unvalidated data."
    )

#duckdb connection and create empty table
os.makedirs(os.path.dirname(db_path), exist_ok=True)
conn = duckdb.connect(db_path)

try:
    conn.execute(f"""
    CREATE TABLE IF NOT EXISTS raw_orders AS
    SELECT
        *,
        CAST('2000-01-01' AS DATE) AS run_date,
        CURRENT_TIMESTAMP AS ingested_at
    FROM read_json_auto('{safe_input_path}')
    WHERE 1 = 0
    """)

    #Delete-Insert Partition Overwrite
    try:
        conn.begin()
        conn.execute(
            "DELETE FROM raw_orders WHERE run_date = CAST(? AS DATE)",
            [run_date_str],
        )
        conn.execute(
            f"""
            INSERT INTO raw_orders
            SELECT
                *,
                CAST(? AS DATE) AS run_date,
                CURRENT_TIMESTAMP AS ingested_at
            FROM read_json_auto('{safe_input_path}')
            """,
            [run_date_str],
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Load failed, rolled back transaction: {e}")
        raise

    row_count = conn.execute(
        "SELECT COUNT(*) FROM raw_orders WHERE run_date = CAST(? AS DATE)",
        [run_date_str],
    ).fetchone()[0]
    print(f"Loaded {row_count} rows into raw_orders for run_date={run_date_str} ({db_path})")
    
finally:
    conn.close()
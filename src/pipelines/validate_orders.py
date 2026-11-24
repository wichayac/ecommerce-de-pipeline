import os
from datetime import date
import argparse
import json
def valid_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid date format: '{value}'. Expected format: YYYY-MM-DD")

parser = argparse.ArgumentParser(description="Validate orders from the extracted data.")
parser.add_argument("--run-date", type=valid_date, required=True, help="date for order validation (YYYY-MM-DD)")
args = parser.parse_args()

input_path = f"data/raw/orders/dt={args.run_date}/orders.jsonl"
report_path = f"data/staging/orders/dt={args.run_date}/validation_reports.json"

if os.path.exists(input_path):
    print(f"Validating orders for date: {args.run_date} from input path: {input_path} and saving reports to: {report_path}")
else:
    raise FileNotFoundError(f"Input file not found at {input_path}. Please ensure the extraction step has been completed for the specified run date.")

total_rows = 0
seen_ids = set()
errors = []
required_fields = ["id", "userId", "total", "products"]

with open(input_path, "r", encoding="utf-8") as f:
    for line_num, line in enumerate(f, start=1):
        total_rows += 1
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            errors.append({f"Line {line_num}: Invalid JSON format"})
            continue

        # Check for required fields
        for field in required_fields:
            if field not in record or record[field] is None:
                errors.append({f"Line {line_num}: missing or null field '{field}'"})

        # Check for duplicate IDs
        order_id = record.get("id")
        if order_id in seen_ids:
            errors.append({f"Line {line_num}: duplicate id {order_id}"})
        else:
            seen_ids.add(order_id)

        total = record.get("total")
        if total is not None:
            if not isinstance(total, (int, float)) or total < 0:
                errors.append({f"Line {line_num}: invalid total {total}"})

        products = record.get("products")
        if products is not None:
            if not isinstance(products, list) or len(products) == 0:
                errors.append({f"Line {line_num}: products should must be a non-empty list"})
            
if total_rows == 0:
    errors.append("Input file is empty (0 rows)")

status = "PASSED" if len(errors) == 0 else "FAILED"

report = {
    "run_date": str(args.run_date),
    "input_path": input_path,
    "total_rows": total_rows,
    "error_count": len(errors),
    "status": status,
    "errors": errors,
}

os.makedirs(os.path.dirname(report_path), exist_ok=True)
with open(report_path, "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2)

print(f"Validation {status}: {total_rows} rows checked, {len(errors)} errors found.")
print(f"Report saved to {report_path}")

if status == "FAILED":
    raise ValueError(f"Validation failed with {len(errors)} errors. See {report_path}")
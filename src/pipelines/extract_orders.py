import os
from dotenv import load_dotenv
import argparse
from datetime import date
import requests
import json

load_dotenv()  # Load environment variables from .env file

api_url = os.getenv("SOURCE_API_URL")
timeout = int(os.getenv("SOURCE_TIMEOUT_SECONDS", "15"))  # Default timeout is 15 seconds if not set

if not api_url:
    raise ValueError("SOURCE_API_URL is missing from environment variables")

def valid_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid date format: '{value}'. Expected format: YYYY-MM-DD")

parser = argparse.ArgumentParser(description="Extract orders from the source API.")
parser.add_argument("--run-date", type=valid_date, required=True, help="date for order extraction (YYYY-MM-DD)")
args = parser.parse_args()
print(f"Extracting orders for date: {args.run_date} from API: {api_url} with timeout: {timeout}")

try:
    response = requests.get(api_url, timeout=timeout)
    response.raise_for_status()  # for error HTTP such as 404, 500
    data = response.json()  # the API returns JSON data
    carts_list = data["carts"]
except requests.exceptions.Timeout:
    print(f"Request to {api_url} timed out after {timeout} seconds.")
    raise
except requests.exceptions.RequestException as e:
    print(f"An error occurred while making the request to {api_url}: {e}")
    raise

target_dir = os.path.join("data", "raw", "orders", f"dt={args.run_date}")
os.makedirs(target_dir, exist_ok=True)

with open(os.path.join(target_dir, "orders.jsonl"), "w") as f:
    for cart in carts_list:
        line = json.dumps(cart)
        f.write(line + "\n")  # Write each cart on a new line
import csv
from pathlib import Path

csv_path = Path(__file__).resolve().parents[1] / "data" / "diabetic_data.csv"
with csv_path.open(encoding="utf-8", newline="") as file:
    reader = csv.DictReader(file)
    first_row = next(reader)
    print(first_row)
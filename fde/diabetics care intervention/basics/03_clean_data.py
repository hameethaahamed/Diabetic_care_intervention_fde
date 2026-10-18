import csv
from pathlib import Path


CSV_PATH = Path(__file__).resolve().parents[1] / "data" / "diabetic_data.csv"
INTEGER_FIELDS = (
    "encounter_id",
    "patient_nbr",
    "time_in_hospital",
    "number_inpatient",
    "number_emergency",
    "number_outpatient",
    "num_medications",
)


def clean_row(row: dict[str, str]) -> dict[str, int | str]:
    cleaned_row: dict[str, int | str] = row.copy()
    for field in INTEGER_FIELDS:
        cleaned_row[field] = int(row[field])
    return cleaned_row


with CSV_PATH.open(encoding="utf-8", newline="") as file:
    reader = csv.DictReader(file)
    first_cleaned_row = None
    row_count = 0

    for row in reader:
        cleaned_row = clean_row(row)
        row_count += 1
        if first_cleaned_row is None:
            first_cleaned_row = cleaned_row

if first_cleaned_row is None:
    raise ValueError(f"No data rows found in {CSV_PATH}")

print(f"Cleaned {row_count} rows.")
print("First cleaned row:", first_cleaned_row)

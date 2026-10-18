import csv
import os
from pathlib import Path
from typing import TypedDict

import psycopg
from dotenv import load_dotenv


class PatientEncounter(TypedDict):
    encounter_id: int
    patient_nbr: int
    age: str
    time_in_hospital: int
    number_inpatient: int
    number_emergency: int
    number_outpatient: int
    num_medications: int
    readmitted: str


EncounterInsert = tuple[int, int, str, int, int, int, int, int, str, int, str]


load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")

CSV_PATH = Path(__file__).resolve().parents[1] / "data" / "diabetic_data.csv"
BATCH_SIZE = 1_000

INSERT_SQL = """
    INSERT INTO patient_encounters (
        encounter_id,
        patient_nbr,
        age,
        time_in_hospital,
        number_inpatient,
        number_emergency,
        number_outpatient,
        num_medications,
        readmitted,
        risk_score,
        risk_level
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (encounter_id) DO UPDATE SET
        patient_nbr = EXCLUDED.patient_nbr,
        age = EXCLUDED.age,
        time_in_hospital = EXCLUDED.time_in_hospital,
        number_inpatient = EXCLUDED.number_inpatient,
        number_emergency = EXCLUDED.number_emergency,
        number_outpatient = EXCLUDED.number_outpatient,
        num_medications = EXCLUDED.num_medications,
        readmitted = EXCLUDED.readmitted,
        risk_score = EXCLUDED.risk_score,
        risk_level = EXCLUDED.risk_level
"""

INSERT_INTERVENTION_SQL = """
    INSERT INTO care_interventions (
        encounter_id,
        status,
        assigned_to,
        notes
    )
    SELECT %s, %s, %s, %s
    WHERE NOT EXISTS (
        SELECT 1
        FROM care_interventions
        WHERE encounter_id = %s
    )
"""


def required_value(row: dict[str, str | None], field: str) -> str:
    value = row.get(field)
    if value is None:
        raise ValueError(f"CSV row is missing the {field!r} value")
    return value


def clean_row(row: dict[str, str | None]) -> PatientEncounter:
    return {
        "encounter_id": int(required_value(row, "encounter_id")),
        "patient_nbr": int(required_value(row, "patient_nbr")),
        "age": required_value(row, "age"),
        "time_in_hospital": int(required_value(row, "time_in_hospital")),
        "number_inpatient": int(required_value(row, "number_inpatient")),
        "number_emergency": int(required_value(row, "number_emergency")),
        "number_outpatient": int(required_value(row, "number_outpatient")),
        "num_medications": int(required_value(row, "num_medications")),
        "readmitted": required_value(row, "readmitted"),
    }


def calculate_risk(patient: PatientEncounter) -> tuple[int, str]:
    risk_score = (
        (3 if patient["number_inpatient"] >= 3 else 0)
        + (2 if patient["number_emergency"] >= 2 else 0)
        + (1 if patient["number_outpatient"] >= 3 else 0)
        + (1 if patient["time_in_hospital"] >= 7 else 0)
        + (1 if patient["num_medications"] >= 20 else 0)
    )

    if risk_score <= 2:
        risk_level = "LOW"
    elif risk_score <= 4:
        risk_level = "MEDIUM"
    else:
        risk_level = "HIGH"
    return risk_score, risk_level


def flush_batch(cur, batch: list[EncounterInsert]) -> tuple[int, int]:
    cur.executemany(INSERT_SQL, batch)
    intervention_rows = [
        (record[0], "PENDING_REVIEW", None, None, record[0])
        for record in batch
        if record[10] in ("MEDIUM", "HIGH")
    ]
    if intervention_rows:
        cur.executemany(INSERT_INTERVENTION_SQL, intervention_rows)
    return len(batch), len(intervention_rows)


processed_count = 0
intervention_candidates = 0
with CSV_PATH.open(encoding="utf-8", newline="") as file:
    reader = csv.DictReader(file)
    batch: list[EncounterInsert] = []

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            for line_number, row in enumerate(reader, start=2):
                try:
                    patient = clean_row(row)
                except ValueError as exc:
                    raise ValueError(
                        f"Invalid patient data on CSV line {line_number}: {exc}"
                    ) from exc

                risk_score, risk_level = calculate_risk(patient)
                batch.append(
                    (
                        patient["encounter_id"],
                        patient["patient_nbr"],
                        patient["age"],
                        patient["time_in_hospital"],
                        patient["number_inpatient"],
                        patient["number_emergency"],
                        patient["number_outpatient"],
                        patient["num_medications"],
                        patient["readmitted"],
                        risk_score,
                        risk_level,
                    )
                )

                if len(batch) >= BATCH_SIZE:
                    processed, candidates = flush_batch(cur, batch)
                    processed_count += processed
                    intervention_candidates += candidates
                    batch.clear()

            if batch:
                processed, candidates = flush_batch(cur, batch)
                processed_count += processed
                intervention_candidates += candidates

if processed_count == 0:
    raise ValueError(f"No patient records found in {CSV_PATH}")

print(f"Inserted or updated {processed_count} patient encounter records.")
print(
    f"MEDIUM/HIGH encounters considered for care interventions: "
    f"{intervention_candidates}"
)
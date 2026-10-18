import csv
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv


load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")

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
RISK_INPUTS = {
    "encounter_id": 2278392,
    "number_inpatient": 3,
    "number_emergency": 2,
    "number_outpatient": 1,
    "time_in_hospital": 7,
    "num_medications": 20,
}
RISK_SCORE = 7
RISK_LEVEL = "HIGH"

with CSV_PATH.open(encoding="utf-8", newline="") as file:
    reader = csv.DictReader(file)
    source_row = next(
        (
            row
            for row in reader
            if int(row["encounter_id"]) == RISK_INPUTS["encounter_id"]
        ),
        None,
    )

if source_row is None:
    raise ValueError(
        f"Encounter {RISK_INPUTS['encounter_id']} was not found in {CSV_PATH}"
    )

patient: dict[str, int | str] = source_row.copy()
for field in INTEGER_FIELDS:
    patient[field] = int(source_row[field])
patient.update(RISK_INPUTS)

with psycopg.connect(DATABASE_URL) as conn:
    with conn.cursor() as cur:
        cur.execute(
            """
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
            """,
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
                RISK_SCORE,
                RISK_LEVEL,
            ),
        )
        cur.execute(
            """
            SELECT encounter_id, patient_nbr, risk_score, risk_level
            FROM patient_encounters
            WHERE encounter_id = %s
            """,
            (patient["encounter_id"],),
        )
        verified_record = cur.fetchone()

if verified_record is None:
    raise RuntimeError(
        f"Could not verify encounter {patient['encounter_id']} after insert"
    )

print(
    f"Verified encounter {verified_record[0]} for patient {verified_record[1]}; "
    f"risk score/level: {verified_record[2]} / {verified_record[3]}"
)

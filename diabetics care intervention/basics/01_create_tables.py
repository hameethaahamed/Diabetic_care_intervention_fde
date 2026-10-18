import psycopg
import os
from dotenv import load_dotenv
load_dotenv()


DATABASE_URL = os.getenv("DATABASE_URL")    
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")

with psycopg.connect(DATABASE_URL) as conn:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS patient_encounters (
                encounter_id BIGINT PRIMARY KEY,
                patient_nbr BIGINT,
                age VARCHAR(20),
                time_in_hospital INTEGER,
                number_inpatient INTEGER,
                number_emergency INTEGER,
                number_outpatient INTEGER,
                num_medications INTEGER,
                readmitted VARCHAR(10),
                risk_score NUMERIC(6, 2),
                risk_level VARCHAR(20)
            )
            """
        )

print("Table patient_encounters is ready.")

with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE care_interventions (
        intervention_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        encounter_id BIGINT NOT NULL,
        status VARCHAR(30) NOT NULL,
        assigned_to VARCHAR(100),
        notes TEXT,

        CONSTRAINT fk_encounter
        FOREIGN KEY (encounter_id)
        REFERENCES patient_encounters(encounter_id)
);
            """
        )

print("Table care_interventions is ready.")
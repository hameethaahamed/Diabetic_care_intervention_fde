# What the dataset tells us, what we do NOT know, and MVP hypothesis

| What the dataset tells us | What we do NOT know | MVP hypothesis |
|---|---|---|
| Historical encounters | Which readmissions were preventable? | Prior utilization may help prioritize follow-up |
| Historical <30-day readmissions | Cost of a readmission? | Care-management capacity is limited |
| Prior healthcare utilization | Current discharge workflow? | A risk queue may be better than reviewing everyone |
| Operational / treatment attributes | Cost of intervention? | Rules are acceptable for an explainable MVP |
| Historical outcome | Clinical validity of rules? | Historical outcomes can be used to evaluate the rule after scoring |

## Diabetes Care Intervention Queue

## Project purpose

This educational project imports historical diabetes encounters, scores them with
transparent utilization-based rules, and exposes a care-management review queue
and operational metrics through a FastAPI application.

> **Educational prototype only.** The risk rules are illustrative, are not
> clinically validated, and must not be used to make patient-care decisions.

## Risk scoring and outcome leakage

The score uses these rules:

| Condition | Points |
|---|---:|
| `number_inpatient >= 3` | +3 |
| `number_emergency >= 2` | +2 |
| `number_outpatient >= 3` | +1 |
| `time_in_hospital >= 7` | +1 |
| `num_medications >= 20` | +1 |

Scores map to risk levels as follows: **LOW** 0–2, **MEDIUM** 3–4, and
**HIGH** 5 or more. MEDIUM and HIGH encounters are added to
`care_interventions` with `PENDING_REVIEW` status.

The historical `readmitted` value is saved for retrospective analysis only. It
is not read by the risk-scoring function. The readmission-analysis endpoint
compares the already-assigned risk groups with historical `<30` outcomes; this
comparison does not establish clinical validity or causality.

## Architecture

```text
CSV -> import_data.py -> service.py (cleaning and scoring)
                       -> repository.py (PostgreSQL writes)

Care team -> main.py (FastAPI routes) -> service.py -> repository.py -> PostgreSQL
```

| File or directory | Responsibility |
|---|---|
| `refactor/main.py` | FastAPI request handling, validation, and response models |
| `refactor/service.py` | CSV cleaning, risk scoring, import orchestration, and metric calculations |
| `refactor/repository.py` | Parameterized SQL for encounter, intervention, queue, and metric operations |
| `refactor/database.py` | PostgreSQL connection setup from `DATABASE_URL` |
| `refactor/models.py` | Pydantic request and response models |
| `refactor/sql/` | Schema creation, intervention-status seed, and data reset |
| `refactor/import_data.py` | Command-line importer |
| `basics/` | Step-by-step learning scripts for CSV reading, cleaning, scoring, inserts, and an earlier API example |
| `data/diabetic_data.csv` | Input dataset |

## Setup and run

Run commands from PowerShell. Configure `DATABASE_URL` in the project `.env`
file with your PostgreSQL connection URL. For example:

```dotenv
DATABASE_URL=postgresql://<user>:<password>@localhost:5432/<database>
```

Install the project dependencies in your chosen Python environment if needed:
`psycopg`, `python-dotenv`, `fastapi`, and `uvicorn`.

Create the schema, then populate the valid intervention statuses:

```powershell
psql -U <user> -d <database> -f "refactor\sql\create_schema.sql"
psql -U <user> -d <database> -f "refactor\sql\seed_interventions_status.sql"
```

Import the default CSV:

```powershell
Set-Location "path\to\diabetics-care-intervention\refactor"
python import_data.py
```

To import a different CSV, pass its path:

```powershell
python import_data.py "path\to\your\diabetic_data.csv"
```

The importer requires `encounter_id`, `patient_nbr`, `age`,
`time_in_hospital`, `number_inpatient`, `number_emergency`,
`number_outpatient`, `num_medications`, and `readmitted`. It stores additional
schema-supported columns when present. Empty strings, `?`, and other recognized
null-like values are stored as `NULL`; missing risk inputs count as zero.
Malformed numeric values or missing required columns stop the import with an
error.

Encounter rows are upserted by `encounter_id`, so rerunning the import updates
existing encounter data. MEDIUM/HIGH encounters get a `PENDING_REVIEW`
intervention if one does not already exist; reruns do not duplicate or
overwrite an existing intervention.

Start the API from the `refactor` directory:

```powershell
python -m uvicorn main:app --reload
```

Open <http://127.0.0.1:8000/docs> for the interactive API documentation.

## API endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/encounters?page=1` | List encounters, 50 records per page |
| GET | `/encounters/{encounter_id}` | Fetch the care intervention for an encounter |
| GET | `/care-queue?page=1` | MEDIUM/HIGH encounters with `PENDING_REVIEW` interventions, 50 per page |
| GET | `/care-queue/high?page=1` | HIGH-risk care queue, 50 per page |
| PATCH | `/interventions/{encounter_id}` | Update intervention status, assignee, or notes |
| GET | `/operations/summary` | Encounter risk counts and pending/completed intervention counts |
| GET | `/operations/readmission-analysis` | HIGH-risk encounters compared with historical `<30` readmissions |
| GET | `/management/dashboard` | Executive summary metrics |

## Resetting imported data

The reset script clears encounter and intervention rows but retains the tables
and status lookup:

```powershell
psql -U <user> -d <database> -f "refactor\sql\reset.sql"
```

## Questions to validate before real-world use

- Are all risk inputs available at the time a care-management decision is made?
- Which readmissions were preventable?
- What is actual intervention capacity and the cost of an intervention?
- Does prioritization perform consistently across patient groups?
- Do the rules identify a meaningfully higher-risk population when validated on
  appropriate data?

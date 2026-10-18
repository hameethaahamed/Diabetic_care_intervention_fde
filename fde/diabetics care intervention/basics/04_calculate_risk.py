patient = {
    "encounter_id": 2278392,
    "number_inpatient": 3,
    "number_emergency": 2,
    "number_outpatient": 1,
    "time_in_hospital": 7,
    "num_medications": 20,
}

points_by_rule = {
    "inpatient admissions": 3 if patient["number_inpatient"] >= 3 else 0,
    "emergency visits": 2 if patient["number_emergency"] >= 2 else 0,
    "outpatient visits": 1 if patient["number_outpatient"] >= 3 else 0,
    "hospital stay": 1 if patient["time_in_hospital"] >= 7 else 0,
    "medications": 1 if patient["num_medications"] >= 20 else 0,
}

print(f"Risk calculation for encounter {patient['encounter_id']}:")
for rule, points in points_by_rule.items():
    print(f"{rule}: +{points}")

risk_score = sum(points_by_rule.values())
if risk_score <= 2:
    risk_level = "LOW"
elif risk_score <= 4:
    risk_level = "MEDIUM"
else:
    risk_level = "HIGH"

print(f"Total risk score: {risk_score}")
print(f"Risk level: {risk_level}")
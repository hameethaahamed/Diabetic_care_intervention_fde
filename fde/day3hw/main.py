from fastapi import FastAPI

try:
    from .services import (
        credit_notes,
        display_duplicate_invoices,
        get_invoices_with_no_amount,
        normalize_invoices,
        reconcile_payments,
        suspected_duplicate_invoices,
    )
except ImportError:
    from services import (
        credit_notes,
        display_duplicate_invoices,
        get_invoices_with_no_amount,
        normalize_invoices,
        reconcile_payments,
        suspected_duplicate_invoices,
    )

app = FastAPI()


@app.get("/invoices/no_amount")
@app.get("/invoices/NoAmount")
def get_no_amount_invoices():
    return get_invoices_with_no_amount()


@app.get("/invoices/display_duplicates")
def get_remove_duplicate_invoices():
    return display_duplicate_invoices()


@app.get("/invoices/suspected_duplicate_invoices")
def get_suspected_duplicate_invoices():
    return suspected_duplicate_invoices()


@app.get("/invoices/credit_notes")
def get_credit_notes():
    return credit_notes()


@app.get("/invoices/reconcile_payments")
def get_reconcile_payments():
    return reconcile_payments()


@app.get("/invoices/normalize_invoices")
def get_normalize_invoices():
    return normalize_invoices()

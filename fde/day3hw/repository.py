
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"


def load_invoices():
    with (DATA_DIR / "invoices.json").open("r", encoding="utf-8") as file:
        return json.load(file)


def load_payments():
    with (DATA_DIR / "payment.json").open("r", encoding="utf-8") as file:
        return json.load(file)


def get_invoices_with_no_amount():
    invoices = load_invoices()
    return [invoice for invoice in invoices if invoice.get("amount") in (None, 0)]


def display_duplicate_invoices():
    invoices = load_invoices()
    unique_invoices = []
    seen_invoices = set()

    for invoice in invoices:
        invoice_key = tuple(sorted(invoice.items()))
        if invoice_key not in seen_invoices:
            unique_invoices.append(invoice)
            seen_invoices.add(invoice_key)

    return unique_invoices


def suspected_duplicate_invoices():
    invoices = load_invoices()
    suspected_duplicates = []
    seen_invoices = {}

    for invoice in invoices:
        key = tuple((field_name, value) for field_name, value in invoice.items() if field_name != "invoice_id")
        if key in seen_invoices:
            suspected_duplicates.append(invoice)
        else:
            seen_invoices[key] = invoice

    return suspected_duplicates


def credit_notes():
    seen_invoices = {}
    matched_pairs = []
    matched_indexes = set()
    invoices = load_invoices()

    for index, invoice in enumerate(invoices):
        amount = invoice.get("amount")
        vendor = str(invoice.get("vendor", "")).strip().casefold()

        if amount is not None and amount > 0:
            key = (vendor, amount)
            seen_invoices.setdefault(key, []).append(index)

    for index, invoice in enumerate(invoices):
        amount = invoice.get("amount")
        vendor = str(invoice.get("vendor", "")).strip().casefold()

        if amount is not None and amount < 0:
            key = (vendor, abs(amount))
            partners = seen_invoices.get(key, [])
            positive_index = next((candidate for candidate in partners if candidate not in matched_indexes), None)

            if positive_index is not None:
                invoice["status"] = "CANCELLED"
                invoices[positive_index]["status"] = "CANCELLED"
                matched_indexes.add(index)
                matched_indexes.add(positive_index)
                matched_pairs.append((index, positive_index))

    return matched_pairs


def reconcile_payments():
    payment_totals = {}
    results = []

    invoices = load_invoices()
    payments = load_payments()

    for payment in payments:
        invoice_id = payment["invoice_id"]
        paid_amount = payment["paid"]
        payment_totals[invoice_id] = payment_totals.get(invoice_id, 0) + paid_amount

    matched_invoice_ids = set()
    for invoice in invoices:
        invoice_id = invoice["invoice_id"]
        invoice_amount = invoice["amount"]
        total_paid = payment_totals.get(invoice_id, 0)
        matched_invoice_ids.add(invoice_id)

        if invoice_amount is None:
            result = "INVOICE AMOUNT MISSING"
        elif invoice_amount < 0:
            result = "CREDIT NOTE"
        elif total_paid == 0:
            result = "UNPAID"
        elif total_paid < invoice_amount:
            result = "PARTIALLY PAID"
        elif total_paid == invoice_amount:
            result = "FULLY PAID"
        else:
            result = "OVERPAID"

        results.append({
            "invoice_id": invoice_id,
            "invoice_amount": invoice_amount,
            "total_paid": total_paid,
            "reconciliation_status": result,
        })

    for invoice_id, total_paid in payment_totals.items():
        if invoice_id not in matched_invoice_ids:
            results.append({
                "invoice_id": invoice_id,
                "invoice_amount": None,
                "total_paid": total_paid,
                "reconciliation_status": "NO MATCHING INVOICE",
            })

    return results


def normalize_invoices():
    invoices = load_invoices()
    valid_invoices = []

    for invoice in invoices:
        invoice["vendor"] = str(invoice.get("vendor", "")).strip().title()
        invoice["status"] = str(invoice.get("status", "")).upper()

        if invoice.get("amount") is None:
            continue

        valid_invoices.append(invoice)

    return valid_invoices

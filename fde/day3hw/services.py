try:
    from .repository import (
        credit_notes as _credit_notes,
        display_duplicate_invoices as _display_duplicate_invoices,
        get_invoices_with_no_amount as _get_invoices_with_no_amount,
        normalize_invoices as _normalize_invoices,
        reconcile_payments as _reconcile_payments,
        suspected_duplicate_invoices as _suspected_duplicate_invoices,
    )
except ImportError:
    from repository import (
        credit_notes as _credit_notes,
        display_duplicate_invoices as _display_duplicate_invoices,
        get_invoices_with_no_amount as _get_invoices_with_no_amount,
        normalize_invoices as _normalize_invoices,
        reconcile_payments as _reconcile_payments,
        suspected_duplicate_invoices as _suspected_duplicate_invoices,
    )


def get_invoices_with_no_amount():
    return _get_invoices_with_no_amount()


def display_duplicate_invoices():
    return _display_duplicate_invoices()


def suspected_duplicate_invoices():
    return _suspected_duplicate_invoices()


def credit_notes():
    return _credit_notes()


def reconcile_payments():
    return _reconcile_payments()


def normalize_invoices():
    return _normalize_invoices()
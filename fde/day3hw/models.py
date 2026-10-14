from pydantic import BaseModel


class Invoice(BaseModel):
    invoice_id: str
    amount: float
    status: str
    vendor: str
    date: str


class Payment(BaseModel):
    invoice_id: str
    paid: float
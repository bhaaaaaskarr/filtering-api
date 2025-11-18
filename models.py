from pydantic import BaseModel, Field
from typing import Optional, List

class InvoiceStatusRequest(BaseModel):
    account: int
    inv: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None

class InvoiceSchema(BaseModel):
    Supplier_Name: str = Field(..., alias="Supplier Name")
    Supplier_SECS: str = Field(..., alias="Supplier SECS")
    Vendor_Code: str = Field(..., alias="Vendor Code")
    Invoice_Number: str = Field(..., alias="Invoice Number")
    Invoice_Date: str = Field(..., alias="Invoice Date")
    Payment_Due_Date: str = Field(..., alias="Payment Due Date")
    Document_Type: str = Field(..., alias="Document Type")
    Amount: float
    Currency: str
    Remark: str
    Status: str

    class Config:
        populate_by_name = True

class ResponseSchema(BaseModel):
    invoices: List[dict]
    summary: Optional[dict] = None
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
import requests
from typing import Optional

from dependencies import get_api_key
from models import InvoiceStatusRequest, ResponseSchema, InvoiceSchema
from utils import normalize, parse_date, get_remark_and_status

router = APIRouter()

@router.get("/")
async def get_root():
    return {"message": "Welcome to the Invoice Status API!"}

@router.post("/invoice/status", response_model=ResponseSchema, response_class=JSONResponse)
async def invoice_status(
    request_data: InvoiceStatusRequest,
    api_key: str = Depends(get_api_key)
):
    def clean_param(param: Optional[str]) -> Optional[str]:
        if param is None or str(param).strip().lower() in ["none", "null", ""]:
            return None
        return str(param).strip()
    
    account = request_data.account
    inv = clean_param(request_data.inv)
    start_date = clean_param(request_data.start_date)
    end_date = clean_param(request_data.end_date)
    
    start_dt = parse_date(start_date) if start_date else None
    end_dt = parse_date(end_date) if end_date else None

    if start_dt and end_dt and start_dt > end_dt:
        raise HTTPException(
            status_code=400,
            detail="start_date cannot be after end_date."
        )

    data_api_url = "http://127.0.0.1:8001/data"
    try:
        response = requests.get(data_api_url)
        response.raise_for_status()
        financial_data = response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to connect to data API: {e}"
        )

    invoices_out = []

    # Case 1: Specific invoice
    if inv:
        invoice_rows = [
            row for row in financial_data
            if (row.get("Account")) == (account)
            and normalize(row.get("Reference key 3")) == inv
            and normalize(row.get("Document type")) in ["IL", "SP"]
        ]

        if not invoice_rows:
            return JSONResponse(content=f"Invoice {inv} is under process")
            
        for row in invoice_rows:
            remark, status = get_remark_and_status(row)
            invoices_out.append({
                "Supplier Name": str(row.get("Vendor name") or ""),
                "Supplier SECS": (row.get("Account") or ""),
                "Vendor Code": str(row.get("Vendor") or ""),
                "Invoice Number": inv,
                "Invoice Date": str(row.get("Entry Date") or ""),
                "Payment Due Date": str(row.get("Payment Date") or ""),
                "Document Type": normalize(row.get("Document type")),
                "Amount": abs(float(row.get("Amount in Doc. Curr.") or 0)),
                "Currency": str(row.get("Document Currency") or ""),
                "Remark": remark,
                "Status": status
            })

        il_amount = sum(abs(float(r.get("Amount in Doc. Curr.") or 0)) for r in invoice_rows if normalize(r.get("Document type")) == "IL")
        sp_amount = sum(abs(float(r.get("Amount in Doc. Curr.") or 0)) for r in invoice_rows if normalize(r.get("Document type")) == "SP")
        currency = invoice_rows[0].get("Document Currency") or ""
        _, status_first = get_remark_and_status(invoice_rows[0])
        amount_due_calc = il_amount - sp_amount
        if status_first == "Paid":
            # Only sum IL amounts for paid invoices
            paid_amount = sum(abs(float(r.get("Amount in Doc. Curr.") or 0)) 
                            for r in invoice_rows if normalize(r.get("Document type")) == "IL")
            due_amount = 0
        else:
            # Keep current logic for due invoices
            il_amount = sum(abs(float(r.get("Amount in Doc. Curr.") or 0)) 
                            for r in invoice_rows if normalize(r.get("Document type")) == "IL")
            sp_amount = sum(abs(float(r.get("Amount in Doc. Curr.") or 0)) 
                            for r in invoice_rows if normalize(r.get("Document type")) == "SP")
            amount_due_calc = il_amount - sp_amount
            paid_amount = 0
            due_amount = amount_due_calc

        summary = {
            "Amount Paid": paid_amount,
            "Amount Due": due_amount,
            "Currency": currency
        }

        return {"invoices": invoices_out, "summary": summary}

    # Case 2: All invoices
    else:
        account_invoices = {}
        for row in financial_data:
            if (row.get("Account")) != (account):
                continue
            if normalize(row.get("Document type")) not in ["IL", "SP"]:
                continue
            invoice_date_str = row.get("Entry Date")
            if not invoice_date_str:
                continue
            try:
                invoice_dt = parse_date(invoice_date_str)
            except HTTPException:
                continue
            if start_dt and invoice_dt < start_dt:
                continue
            if end_dt and invoice_dt > end_dt:
                continue
            inv_no = normalize(row.get("Reference key 3"))
            if not inv_no:
                continue
            account_invoices.setdefault(inv_no, []).append(row)
        for inv_no, rows in account_invoices.items():
            il_amount = sum(abs(float(r.get("Amount in Doc. Curr.") or 0)) for r in rows if normalize(r.get("Document type")) == "IL")
            sp_amount = sum(abs(float(r.get("Amount in Doc. Curr.") or 0)) for r in rows if normalize(r.get("Document type")) == "SP")
            base_row = rows[0] if rows else {}
            remark, status = get_remark_and_status(base_row)
            if status == "Paid":
            # For Paid invoices, ignore SP (same as summary logic)
                amount_due = il_amount
            else:
                # For Due invoices, keep IL - SP
                amount_due = il_amount - sp_amount

            invoices_out.append({
                "Supplier Name": str(base_row.get("Vendor name") or ""),
                "Supplier SECS": (base_row.get("Account") or ""),
                "Vendor Code": str(base_row.get("Vendor") or ""),
                "Invoice Number": inv_no,
                "Invoice Date": str(base_row.get("Entry Date") or ""),
                "Payment Due Date": str(base_row.get("Payment Date") or ""),
                "Document Type": "Aggregated",
                "Amount": amount_due,
                "Currency": str(base_row.get("Document Currency") or ""),
                "Remark": remark,
                "Status": status
            })
        summary = {
            "invoice_count": len(invoices_out),
            "due_count": sum(1 for i in invoices_out if i.get("Status") == "Due"),
            "paid_count": sum(1 for i in invoices_out if i.get("Status") == "Paid"),
            "total_due_amount": sum(
                (
                    sum(abs(float(r.get("Amount in Doc. Curr.") or 0)) 
                        for r in rows if normalize(r.get("Document type")) == "IL")
                    -
                    sum(abs(float(r.get("Amount in Doc. Curr.") or 0)) 
                        for r in rows if normalize(r.get("Document type")) == "SP")
                )
                for inv_no, rows in account_invoices.items()
                if get_remark_and_status(rows[0])[1] == "Due"
            ),

            
            "total_paid_amount": sum(
            sum(abs(float(r.get("Amount in Doc. Curr.") or 0)) for r in rows if normalize(r.get("Document type")) == "IL")
            for inv_no, rows in account_invoices.items()
            if get_remark_and_status(rows[0])[1] == "Paid"),

        }
        return {"invoices": invoices_out, "summary": summary}
from fastapi import HTTPException
from datetime import datetime, timedelta

def normalize(value):
    if value is None:
        return ""
    return str(value).strip()

def parse_date(date_str: str) -> datetime:
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid date format: {date_str}. Use YYYY-MM-DD."
        )

def get_remark_and_status(invoice: dict) -> tuple[str, str]:
    """
    Return (remark, status) based on business logic.
    Only case 4 is considered Paid, everything else is Due.
    """
    # ... Your original get_remark_and_status logic goes here ...
    ref_key = normalize(invoice.get("Reference key 3"))
    clearing_doc = normalize(invoice.get("Clearing Document"))
    vendor_clearing_doc_no = normalize(invoice.get("Vendor Clearing document no"))
    bp_clearing_date_str = normalize(invoice.get("BP clearing Date"))
    clearing_date = normalize(invoice.get("Clearing Date"))

    if not ref_key:
        return "Invoice under process", "Due"

    if ref_key and not clearing_doc and not vendor_clearing_doc_no and not bp_clearing_date_str and not clearing_date:
        return f"Invoice {ref_key} has been processed and booked for payment.", "Due"

    if ref_key and clearing_doc and clearing_date and not vendor_clearing_doc_no and not bp_clearing_date_str:
        return f"Invoice {ref_key} has been processed and sent to AP for payment.", "Due"

    if ref_key and clearing_doc and clearing_date and vendor_clearing_doc_no and bp_clearing_date_str:
        try:
            paid_date = parse_date(bp_clearing_date_str)
            today = datetime.today()
            if today - paid_date <= timedelta(days=4):
                return (
                    f"Payment for invoice {ref_key} has been processed on {bp_clearing_date_str}. "
                    f"It will be reflected in your bank account within 2 working days.",
                    "Paid"
                )
            else:
                return (
                    f"Payment for invoice {ref_key} has been processed on {bp_clearing_date_str}.",
                    "Paid"
                )
        except Exception:
            return f"Payment for invoice {ref_key} has been processed on {bp_clearing_date_str}.", "Paid"
            
    return f"Invoice {ref_key} found, but does not match defined status rules.", "Due"
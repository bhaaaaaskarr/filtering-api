
# helper.py
from typing import List, Dict, Optional, Iterable, Any
from collections import Counter
from datetime import datetime
import json

# Preferred columns (shown first when present)
PRIORITY_COLUMNS: List[str] = [
    "Supplier Name",
    "Supplier SECS",
    "Vendor Code",
    "Invoice Number",
    "Invoice Date",
    "Payment Due Date",
    # "Document Type",
    "Amount",
    "Currency",
    "Remark",
    "Status",
]

# Exclude noisy/internal keys if needed
EXCLUDE_KEYS: set[str] = set()

def _fmt_date(s: Optional[str]) -> str:
    """Format ISO-like date strings as DD-MMM-YYYY."""
    if not s:
        return ""
    fmts = ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%fZ")
    for f in fmts:
        try:
            dt = datetime.strptime(str(s)[:len(f)], f)
            return dt.strftime("%d-%b-%Y")
        except ValueError:
            continue
    return str(s)

def _fmt_amount(x: Optional[object]) -> str:
    """Format numeric amount with thousands separators and 2 decimals."""
    try:
        return f"{float(x):,.2f}"
    except (TypeError, ValueError):
        return "" if x is None else str(x)

# Column-specific formatters
COLUMN_FORMATTERS = {
    "Invoice Date": _fmt_date,
    "Payment Due Date": _fmt_date,
    "Amount": _fmt_amount,
}

def coerce_to_text(col: str, raw: Any) -> str:
    """
    Format value by column, then ensure it's a safe Markdown string.
    - Dict/List -> JSON string
    - Numbers/strings -> str
    - Applies COLUMN_FORMATTERS if present (CALLS the function)
    - Escapes pipes to avoid breaking Markdown tables
    """
    # Apply formatter if configured for this column (CALL the function)
    if col in COLUMN_FORMATTERS:
        try:
            formatted = COLUMN_FORMATTERS(col)
        except Exception:
            formatted = raw
    else:
        formatted = raw

    # Ensure final text
    if isinstance(formatted, (dict, list)):
        text = json.dumps(formatted, ensure_ascii=False)
    else:
        text = "" if formatted is None else str(formatted)

    # Markdown-safe: strip newlines, escape pipes
    return text.replace("\n", " ").strip().replace("|", "\\|")

def derive_columns(
    rows: Iterable[Dict],
    priority: Optional[List[str]] = None,
    exclude: Optional[Iterable[str]] = None,
    max_cols: Optional[int] = None,
) -> List[str]:
    """
    Derive dynamic headers from the union of keys across all rows.
    - Priority columns that exist appear first.
    - Remaining columns sorted by frequency (desc) then name (asc).
    - Excludes keys and caps number of columns if max_cols is set.
    """
    priority = priority or PRIORITY_COLUMNS
    exclude_set = set(exclude or EXCLUDE_KEYS)

    freq: Counter = Counter()
    for r in rows:
        freq.update(k for k in r.keys() if k not in exclude_set)

    if not freq:
        cols = [c for c in priority if c not in exclude_set]
        return cols[:max_cols] if max_cols else cols

    present_keys = set(freq.keys())

    # Priority columns that actually exist
    cols: List[str] = [c for c in priority if c in present_keys]

    # Remaining columns by frequency then alphabetical
    rest = [k for k in present_keys if k not in cols]
    rest.sort(key=lambda k: (-freq[k], k.lower()))
    cols.extend(rest)

    if max_cols and max_cols > 0:
        cols = cols[:max_cols]
    return cols

def to_markdown_dynamic(
    invoices: List[Dict],
    columns: List[str],
    page: int,
    page_size: int,
    pager_hint: bool = True,
) -> str:
    """
    Render a Markdown table with provided dynamic columns and paging.
    """
    lines: List[str] = []
    # Header
    lines.append("| " + " | ".join(columns) + " |")
    lines.append("|" + "|".join(["---"] * len(columns)) + "|")

    total = len(invoices)
    start = max((page - 1) * page_size, 0)
    end = min(start + page_size, total)
    subset = invoices[start:end]

    # Rows
    for r in subset:
        cells: List[str] = []
        for col in columns:
            raw = r.get(col, "")
            # ✅ Always coerce to text; prevents dict/list or function leaking into join()
            cells.append(coerce_to_text(col, raw))
        lines.append("| " + " | ".join(cells) + " |")

    # Pager hint
    if total == 0:
        lines.append("\n_No invoices found._")
    elif pager_hint:
        pages = (total + page_size - 1) // page_size
        lines.append(f"\n_Page **{page}** of **{pages}** · {total} rows_")

    return "\n".join(lines)

def summary_markdown_dynamic(summary: Dict) -> str:
    """Render a compact Markdown summary below the table."""
    if not summary:
        return ""
    items: List[str] = []
    for k, v in summary.items():
        items.append(f"- **{k}**: {coerce_to_text(k, v)}")
    return "\n\n**Summary**\n" + "\n".join(items)

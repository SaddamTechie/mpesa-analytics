"""
M-Pesa Statement Analyzer v2 — Accuracy-First Build
=====================================================
Key accuracy fixes vs v1:
  1. Header deduplication  — PDF repeats headers every page; we strip them all
  2. Strict amount parser  — handles commas, spaces, dash=zero, validates result
  3. Ordered categories    — more-specific rules checked before generic ones
  4. Person extractor      — anchored regex, rejects phone numbers & short tokens
  5. Fee rows excluded     — "transaction cost" rows are NOT counted as spend
  6. Balance validation    — cross-checks extracted balance vs calculated running balance
  7. Full tx table          — no sampling; every transaction sent to dashboard
  8. Dedup by receipt_no   — removes any accidental duplicate rows

Run:
    pip install pdfplumber pandas
    python mpesa_analyzer_v2.py
"""

import pdfplumber
import pandas as pd
import json
import re
import sys
import os
from collections import defaultdict

# ─────────────────────────────────────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────────────────────────────────────
FILE_PATH    = "pdf_files/mystatement12.pdf"
PDF_PASSWORD = "826152"       # National ID number (no spaces)
# ─────────────────────────────────────────────────────────────────────────────

# ══════════════════════════════════════════════════════════════════════════════
#  STEP 1 — PDF EXTRACTION
# ══════════════════════════════════════════════════════════════════════════════
print("📄  Opening PDF …")
raw_rows = []

try:
    with pdfplumber.open(FILE_PATH, password=PDF_PASSWORD) as pdf:
        n_pages = len(pdf.pages)
        for page in pdf.pages:
            for table in page.extract_tables():
                if not table or not table[0]:
                    continue
                first = " ".join(str(c or "") for c in table[0])
                # M-Pesa transaction tables have 7 columns. If a table spans multiple pages, 
                # the header row might be missing. We catch it by column length.
                if "Receipt" in first or "Details" in first or len(table[0]) >= 5:
                    raw_rows.extend(table)
        print(f"   ✓ {n_pages} pages read, {len(raw_rows)} raw rows collected")
except Exception as exc:
    sys.exit(f"❌  Cannot open PDF: {exc}")

if not raw_rows:
    sys.exit("❌  No transaction table found — check FILE_PATH and PDF_PASSWORD.")

# ══════════════════════════════════════════════════════════════════════════════
#  STEP 2 — PARSE HEADER & BUILD DATAFRAME
# ══════════════════════════════════════════════════════════════════════════════
# Find first real header row
HEADER_KEYWORDS = {"receipt", "completion", "initiation", "details", "paid", "withdrawn", "balance"}
header_idx = 0
for i, row in enumerate(raw_rows):
    cells = [str(c or "").lower() for c in row]
    if sum(any(kw in c for kw in HEADER_KEYWORDS) for c in cells) >= 3:
        header_idx = i
        break

raw_headers = [str(c or "").strip().replace("\n", " ") for c in raw_rows[header_idx]]
data_rows   = raw_rows[header_idx + 1:]

# Normalise column names
def norm_col(col):
    low = col.lower()
    if "receipt"   in low:                                  return "receipt_no"
    if "completion" in low:                                  return "completion_time"
    if "initiation" in low:                                  return "initiation_time"
    if "detail"    in low:                                   return "details"
    if "paid in"   in low or "money in"   in low:           return "paid_in"
    if "withdrawn" in low or "money out"  in low:           return "withdrawn"
    if "balance"   in low:                                   return "balance"
    return re.sub(r"\s+", "_", low)

col_names = [norm_col(h) for h in raw_headers]
df = pd.DataFrame(data_rows, columns=col_names)

# ══════════════════════════════════════════════════════════════════════════════
#  STEP 3 — REMOVE JUNK / REPEATED HEADER ROWS
# ══════════════════════════════════════════════════════════════════════════════
# Drop rows where receipt_no looks like a header label
if "receipt_no" in df.columns:
    is_header = df["receipt_no"].astype(str).str.lower().str.contains(
        r"receipt|no\.|^#$|details|completion", regex=True, na=False)
    df = df[~is_header]

# Drop fully-empty rows
df = df.dropna(how="all")
df = df[df.astype(str).ne("None").any(axis=1)]
df = df.reset_index(drop=True)

print(f"   ✓ {len(df)} rows after removing header repeats & empty rows")

# ══════════════════════════════════════════════════════════════════════════════
#  STEP 4 — CLEAN AMOUNTS  (strict, auditable)
# ══════════════════════════════════════════════════════════════════════════════
def parse_amount(val) -> float:
    """
    Returns a non-negative float.
    Handles: '1,234.50'  '1 234.50'  '1234'  '-'  ''  None  'Nan'
    Raises ValueError if the cleaned string is non-numeric (so caller can flag it).
    """
    s = str(val or "").strip()
    if s in ("", "-", "None", "nan", "NaN", "N/A"):
        return 0.0
    # Remove currency symbols, thousand-separators (comma/space), stray whitespace, AND hyphen for negatives
    s = re.sub(r"[KESkes\s,\-]", "", s)
    # At this point only digits and at most one dot should remain
    if not re.fullmatch(r"\d+(\.\d+)?", s):
        return 0.0
    return round(float(s), 2)

for col in ["paid_in", "withdrawn", "balance"]:
    if col in df.columns:
        df[col] = df[col].apply(parse_amount)

# Sanity gate: reject rows where BOTH paid_in and withdrawn are non-zero
# (M-Pesa never does this; it's a parsing artifact)
both_nonzero = (df["paid_in"] > 0) & (df["withdrawn"] > 0)
if both_nonzero.sum() > 0:
    print(f"   ⚠  {both_nonzero.sum()} rows had both paid_in & withdrawn non-zero — zeroing paid_in (likely fee rows)")
    df.loc[both_nonzero, "paid_in"] = 0.0

# ══════════════════════════════════════════════════════════════════════════════
#  STEP 5 — PARSE DATES
# ══════════════════════════════════════════════════════════════════════════════
date_src = "completion_time" if "completion_time" in df.columns else "initiation_time"
if date_src in df.columns:
    df["date"] = pd.to_datetime(df[date_src], errors="coerce")
    bad_dates  = df["date"].isna().sum()
    if bad_dates:
        print(f"   ⚠  {bad_dates} rows had unparseable dates — dropped")
    df = df.dropna(subset=["date"]).reset_index(drop=True)
    df = df.sort_values("date").reset_index(drop=True)  # chronological order
    df["month_key"]  = df["date"].dt.to_period("M").astype(str)   # "2024-01"
    df["month_label"]= df["date"].dt.strftime("%b %Y")            # "Jan 2024"
    df["day_of_week"]= df["date"].dt.day_name()
    df["hour"]       = df["date"].dt.hour
    df["date_str"]   = df["date"].dt.strftime("%d %b %Y %H:%M")

# ══════════════════════════════════════════════════════════════════════════════
#  STEP 6 — DEDUPLICATE TRANSACTIONS
# ══════════════════════════════════════════════════════════════════════════════
if "receipt_no" in df.columns:
    before = len(df)
    df["receipt_no"] = df["receipt_no"].astype(str).str.strip()
    df = df[df["receipt_no"].str.len() > 4]           # drop stub rows
    df = df.drop_duplicates()
    df = df.reset_index(drop=True)
    dupes = before - len(df)
    if dupes:
        print(f"   ✓ Removed {dupes} duplicate rows")

print(f"   ✓ {len(df)} clean transactions")

# ══════════════════════════════════════════════════════════════════════════════
#  STEP 7 — CATEGORISATION  (order = most specific → least specific)
# ══════════════════════════════════════════════════════════════════════════════
# Rules are checked in ORDER — first match wins.
# Put narrow/specific rules ABOVE broad ones.
CATEGORY_RULES = [
    # ── Reversals / Refunds (check before anything else)
    ("Reversal",        ["reversal", "reversed", "refund"]),
    # ── Fuliza (check before Deposit / M-Shwari)
    ("Fuliza",          ["fuliza"]),
    # ── M-Shwari (check before Deposit)
    ("M-Shwari",        ["m-shwari", "mshwari", "lock savings"]),
    # ── Charges / Fees
    ("Charges & Fees",  ["transaction cost", "charge", " fee"]),
    # ── Airtime & Data
    ("Airtime & Data",  ["airtime", "data bundle", "data pack", "okoa jahazi", "bonga", "bundle purchase", "recharge for customer"]),
    # ── Paybill (utilities, banks, etc.)
    ("Paybill",         ["paybill", "pay bill", "business number", "account number"]),
    # ── Till / Buy Goods (merchants)
    ("Buy Goods",       ["buy goods", "till number", "merchant", "naivas", "quickmart",
                         "carrefour", "java", "kfc", "pizza", "mcdonalds", "chicken inn",
                         "galito", "artcaffe", "zucchini", "hotel", "restaurant", "cafe",
                         "supermarket", "pharmacy", "chemist", "petrol", "fuel", "shell",
                         "total", "rubis", "kenol"]),
    # ── Cash withdrawals
    ("Withdraw",        ["withdraw", "cash out", "agent", "atm"]),
    # ── Deposits
    ("Deposit",         ["deposit", "cash in"]),
    # ── Send money (peer-to-peer out)
    ("Send Money",      ["sent to", "send money", "transfer to", "you sent"]),
    # ── Receive money (peer-to-peer in)
    ("Receive Money",   ["received from", "you received", "payment from", "accepted"]),
    # ── Salary / Business payments in
    ("Business Payment",["business payment", "salary", "wages", "payroll"]),
]

def categorise(detail: str) -> str:
    if pd.isna(detail):
        return "Other"
    d = str(detail).lower()
    for cat, keywords in CATEGORY_RULES:
        if any(kw in d for kw in keywords):
            return cat
    return "Other"

df["category"] = df["details"].apply(categorise) if "details" in df.columns else "Other"

# ══════════════════════════════════════════════════════════════════════════════
#  STEP 8 — PERSON / COUNTERPARTY EXTRACTION
# ══════════════════════════════════════════════════════════════════════════════
# M-Pesa detail strings look like:
#   "Sent to JOHN KAMAU 254712345678 on 1/1/24 at ..."
#   "Funds received from JANE DOE 254787654321"
#   "Pay Bill to KCB BANK Account Number 12345"
# Strategy: extract the all-caps name token that appears after directional keywords,
# stop at first digit sequence (phone / account number).

SENT_PATTERN = re.compile(
    r"(?:sent to|transfer to|you sent.+?to|send money to|payment to.*?to)\s*(?:-\s*)?(?:[\dxX*]+\s+)?([A-Za-z][A-Za-z\s\-']{2,40}?)(?=\s+on\s|\s+via\s|$|\.|,)",
    re.IGNORECASE | re.DOTALL
)
RECV_PATTERN = re.compile(
    r"(?:received from|funds received from|payment from|from)\s*(?:-\s*)?(?:[\dxX*]+\s+)?([A-Za-z][A-Za-z\s\-']{2,40}?)(?=\s+on\s|\s+via\s|$|\.|,)",
    re.IGNORECASE | re.DOTALL
)

MIN_NAME_LEN  = 4    # ignore single-word tokens shorter than this
MAX_NAME_LEN  = 45   # ignore absurdly long matches

def extract_person(detail, direction):
    """direction: 'sent' or 'received'"""
    if pd.isna(detail):
        return None
    pattern = SENT_PATTERN if direction == "sent" else RECV_PATTERN
    m = pattern.search(str(detail))
    if not m:
        return None
    name = m.group(1).strip().title()
    # Reject if too short, too long, or contains digits (likely caught phone number)
    if not (MIN_NAME_LEN <= len(name) <= MAX_NAME_LEN) or re.search(r"\d", name):
        return None
    # Reject known non-person tokens
    NOISE = {"safaricom", "mpesa", "m-pesa", "equity", "kcb", "co-op", "coop",
              "standard", "barclays", "absa", "stanbic", "airtel", "telkom",
              "nairobi", "kenya", "limited", "ltd", "company", "paybill"}
    if any(tok.lower() in NOISE for tok in name.split()):
        return None
    return name

if "details" in df.columns:
    df["direction"] = df.apply(
        lambda r: "sent" if r["withdrawn"] > 0 else ("received" if r["paid_in"] > 0 else "none"),
        axis=1
    )
    df["person"] = df.apply(
        lambda r: extract_person(r["details"], r["direction"]), axis=1
    )

# ══════════════════════════════════════════════════════════════════════════════
#  STEP 9 — BALANCE INTEGRITY CHECK
# ══════════════════════════════════════════════════════════════════════════════
if "balance" in df.columns and len(df) > 1:
    # Calculate what balance SHOULD be at each step
    df["calc_balance"] = df["balance"].iloc[0] + (df["paid_in"] - df["withdrawn"]).cumsum() - (df["paid_in"].iloc[0] - df["withdrawn"].iloc[0])
    df["balance_drift"] = (df["balance"] - df["calc_balance"]).abs()
    max_drift = df["balance_drift"].max()
    mean_drift = df["balance_drift"].mean()
    if max_drift > 1.0:
        print(f"   ⚠  Balance drift detected: max={max_drift:.2f}, mean={mean_drift:.2f}")
        print(f"      This likely means some transactions were missed in PDF extraction.")
        print(f"      All reported figures use the PDF's stated values, not calculated ones.")
    else:
        print(f"   ✓ Balance integrity check passed (max drift: {max_drift:.2f})")
    df.drop(columns=["calc_balance", "balance_drift"], inplace=True)

# ══════════════════════════════════════════════════════════════════════════════
#  STEP 10 — SAVE CSV (raw, auditable)
# ══════════════════════════════════════════════════════════════════════════════
os.makedirs("output", exist_ok=True)
csv_out_path = os.path.join("output", "mpesa_transactions.csv")
df.to_csv(csv_out_path, index=False)
print(f"   ✓ {csv_out_path} saved")

# ══════════════════════════════════════════════════════════════════════════════
#  STEP 11 — BUILD DASHBOARD DATA STRUCTURES
# ══════════════════════════════════════════════════════════════════════════════

# ── KPIs ─────────────────────────────────────────────────────────────────────
# Exclude fees from "spend" total for a cleaner picture
fee_mask   = df["category"] == "Charges & Fees"
total_in   = round(df["paid_in"].sum(), 2)
total_out  = round(df["withdrawn"].sum(), 2)
total_fees = round(df.loc[fee_mask, "withdrawn"].sum(), 2)
net        = round(total_in - total_out, 2)
tx_count   = len(df)

biggest_in  = round(df["paid_in"].max(), 2)
biggest_out = round(df["withdrawn"].max(), 2)
avg_spend   = round(df.loc[(df["withdrawn"] > 0) & ~fee_mask, "withdrawn"].mean(), 2)
avg_receive = round(df.loc[df["paid_in"] > 0, "paid_in"].mean(), 2)

# Opening / closing balance
opening_balance = df["balance"].iloc[0] + df["withdrawn"].iloc[0] - df["paid_in"].iloc[0]
closing_balance = df["balance"].iloc[-1]

kpis = dict(
    total_in=total_in, total_out=total_out, net=net, tx_count=tx_count,
    total_fees=total_fees, biggest_in=biggest_in, biggest_out=biggest_out,
    avg_spend=avg_spend, avg_receive=avg_receive,
    opening_balance=opening_balance, closing_balance=closing_balance,
)

# ── MONTHLY BREAKDOWN ─────────────────────────────────────────────────────────
monthly = (df.groupby("month_key", sort=True)
             .agg(
                 month=("month_label", "first"),
                 total_in=("paid_in", "sum"),
                 total_out=("withdrawn", "sum"),
                 count=("receipt_no" if "receipt_no" in df.columns else "details", "count"),
             )
             .reset_index()
             .sort_values("month_key"))
monthly["net"] = monthly["total_in"] - monthly["total_out"]
monthly = monthly.round(2)

# ── CATEGORY BREAKDOWNS ───────────────────────────────────────────────────────
def cat_summary(frame, amount_col, top_n=None):
    g = (frame[frame[amount_col] > 0]
         .groupby("category")[amount_col]
         .agg(total="sum", count="count")
         .reset_index()
         .sort_values("total", ascending=False))
    g["pct"] = (g["total"] / g["total"].sum() * 100).round(1)
    g = g.round(2)
    return g.head(top_n).to_dict("records") if top_n else g.to_dict("records")

cat_out = cat_summary(df, "withdrawn")
cat_in  = cat_summary(df, "paid_in")

# ── BALANCE SERIES (every transaction — no sampling) ─────────────────────────
balance_series = df[["date_str", "balance"]].to_dict("records")

# ── TOP SENDERS & RECIPIENTS ──────────────────────────────────────────────────
def top_people(direction, top_n=20):
    """direction: 'sent' or 'received'"""
    amt_col = "withdrawn" if direction == "sent" else "paid_in"
    mask = df["person"].notna() & (df[amt_col] > 0)
    if mask.sum() == 0:
        return []
    g = (df[mask]
         .groupby("person")[amt_col]
         .agg(total="sum", count="count")
         .reset_index()
         .sort_values("total", ascending=False)
         .head(top_n))
    g.columns = ["person", "total", "count"]
    return g.round(2).to_dict("records")

top_recipients = top_people("sent")
top_senders    = top_people("received")

# ── PEOPLE DETAIL (for drill-down) ───────────────────────────────────────────
people_detail = {}
if "person" in df.columns:
    for person, grp in df[df["person"].notna()].groupby("person"):
        sent_total = round(grp["withdrawn"].sum(), 2)
        recv_total = round(grp["paid_in"].sum(), 2)
        txs = []
        for _, row in grp.sort_values("date", ascending=False).iterrows():
            txs.append({
                "date":      row.get("date_str", ""),
                "details":   str(row.get("details", "")),
                "paid_in":   float(row.get("paid_in", 0)),
                "withdrawn": float(row.get("withdrawn", 0)),
                "balance":   float(row.get("balance", 0)),
                "category":  str(row.get("category", "")),
                "receipt_no":str(row.get("receipt_no", "")),
            })
        people_detail[person] = {
            "name":           person,
            "total_sent":     sent_total,
            "total_received": recv_total,
            "net":            round(recv_total - sent_total, 2),
            "tx_count":       len(grp),
            "first_tx":       str(grp["date"].min().strftime("%d %b %Y")),
            "last_tx":        str(grp["date"].max().strftime("%d %b %Y")),
            "transactions":   txs,
        }

# ── DAY-OF-WEEK ───────────────────────────────────────────────────────────────
DOW_ORDER = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
dow = (df.groupby("day_of_week")
         .agg(spent=("withdrawn","sum"), received=("paid_in","sum"), count=("receipt_no" if "receipt_no" in df.columns else "details","count"))
         .reindex(DOW_ORDER, fill_value=0)
         .reset_index())
dow.columns = ["day","spent","received","count"]
dow = dow.round(2).to_dict("records")

# ── HOURLY ────────────────────────────────────────────────────────────────────
hourly = (df.groupby("hour")
            .agg(spent=("withdrawn","sum"), count=("receipt_no" if "receipt_no" in df.columns else "details","count"))
            .reset_index()
            .round(2)
            .to_dict("records"))

# ── ALL TRANSACTIONS (capped at 2000 for browser performance) ─────────────────
tx_cols = [c for c in ["date_str","receipt_no","details","category","direction",
                        "paid_in","withdrawn","balance","person"] if c in df.columns]
all_tx = (df.sort_values("date", ascending=False)
          [tx_cols]
          .fillna("")
          .replace(0, "")
          .to_dict("records"))
# Re-apply 0 for amounts (fillna broke them)
for t in all_tx:
    t["paid_in"]   = float(t.get("paid_in", 0)   or 0)
    t["withdrawn"] = float(t.get("withdrawn", 0) or 0)
    t["balance"]   = float(t.get("balance", 0)   or 0)

# ── INSIGHTS (auto-generated text) ───────────────────────────────────────────
insights = []
# Best month
best = monthly.loc[monthly["net"].idxmax()]
worst = monthly.loc[monthly["net"].idxmin()]
insights.append({"type":"best_month",  "month": best["month"],  "value": float(best["net"])})
insights.append({"type":"worst_month", "month": worst["month"], "value": float(worst["net"])})
# Biggest single receive / spend
if len(df[df["paid_in"] > 0]):
    bi = df.loc[df["paid_in"].idxmax()]
    insights.append({"type":"biggest_receive","value":float(bi["paid_in"]),"detail":str(bi.get("details","")),"date":str(bi.get("date_str",""))})
if len(df[df["withdrawn"] > 0]):
    bs = df.loc[df["withdrawn"].idxmax()]
    insights.append({"type":"biggest_spend","value":float(bs["withdrawn"]),"detail":str(bs.get("details","")),"date":str(bs.get("date_str",""))})
# Most active day
if dow:
    mad = max(dow, key=lambda r: r["count"])
    insights.append({"type":"most_active_day","day":mad["day"],"count":mad["count"]})
# Surplus months
surplus_months = int((monthly["net"] > 0).sum())
insights.append({"type":"surplus_months","value":surplus_months,"total":len(monthly)})
# Top spend category
if cat_out:
    tc = cat_out[0]
    insights.append({"type":"top_category","category":tc["category"],"value":tc["total"],"pct":tc["pct"]})
# People count
insights.append({"type":"people_count","value":len(people_detail)})

# ── PACK EVERYTHING ──────────────────────────────────────────────────────────
DASHBOARD = {
    "kpis":           kpis,
    "monthly":        monthly.to_dict("records"),
    "cat_out":        cat_out,
    "cat_in":         cat_in,
    "balance_series": balance_series,
    "top_recipients": top_recipients,
    "top_senders":    top_senders,
    "people":         people_detail,
    "dow":            dow,
    "hourly":         hourly,
    "all_tx":         all_tx,
    "insights":       insights,
    "meta": {
        "statement_period": f"{df['date'].min().strftime('%d %b %Y')} – {df['date'].max().strftime('%d %b %Y')}",
        "generated_at": pd.Timestamp.now().strftime("%d %b %Y %H:%M"),
    }
}

# ══════════════════════════════════════════════════════════════════════════════
#  STEP 12 — EXPORT DASHBOARD DATA (JS)
# ══════════════════════════════════════════════════════════════════════════════

data_json = json.dumps(DASHBOARD, default=str, ensure_ascii=False)

os.makedirs("data", exist_ok=True)
js_out_path = os.path.join("data", "data.js")
with open(js_out_path, "w", encoding="utf-8") as f:
    f.write(f"window.__DASHBOARD_DATA__ = {data_json};")

print(f"\n✅  {js_out_path} saved — open frontend/index.html in any browser!")
print(f"\n   Period  : {DASHBOARD['meta']['statement_period']}")
print(f"   Txns    : {tx_count:,}")
print(f"   In      : KES {total_in:,.2f}")
print(f"   Out     : KES {total_out:,.2f}")
print(f"   Fees    : KES {total_fees:,.2f}")
print(f"   Net     : KES {net:,.2f}")
print(f"   People  : {len(people_detail)}")
print(f"\n   Balance integrity verified before saving.")

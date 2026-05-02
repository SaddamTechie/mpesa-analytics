import pdfplumber
import json
import re
from collections import defaultdict
from datetime import datetime
import io

def norm_col(col):
    low = col.lower()
    if "receipt"   in low: return "receipt_no"
    if "completion" in low: return "completion_time"
    if "initiation" in low: return "initiation_time"
    if "detail"    in low: return "details"
    if "paid in"   in low or "money in" in low: return "paid_in"
    if "withdrawn" in low or "money out" in low: return "withdrawn"
    if "balance"   in low: return "balance"
    return re.sub(r"\s+", "_", low)

def parse_amount(val) -> float:
    s = str(val or "").strip()
    if s in ("", "-", "None", "nan", "NaN", "N/A"):
        return 0.0
    s = re.sub(r"[KESkes\s,\-]", "", s)
    if not re.fullmatch(r"\d+(\.\d+)?", s):
        return 0.0
    return round(float(s), 2)

CATEGORY_RULES = [
    ("Reversal",        ["reversal", "reversed", "refund"]),
    ("Fuliza",          ["fuliza"]),
    ("M-Shwari",        ["m-shwari", "mshwari", "lock savings"]),
    ("Charges & Fees",  ["transaction cost", "charge", " fee"]),
    ("Airtime & Data",  ["airtime", "data bundle", "data pack", "okoa jahazi", "bonga", "bundle purchase", "recharge for customer"]),
    ("Paybill",         ["paybill", "pay bill", "business number", "account number"]),
    ("Buy Goods",       ["buy goods", "till number", "merchant", "naivas", "quickmart",
                         "carrefour", "java", "kfc", "pizza", "mcdonalds", "chicken inn",
                         "galito", "artcaffe", "zucchini", "hotel", "restaurant", "cafe",
                         "supermarket", "pharmacy", "chemist", "petrol", "fuel", "shell",
                         "total", "rubis", "kenol"]),
    ("Withdraw",        ["withdraw", "cash out", "agent", "atm"]),
    ("Deposit",         ["deposit", "cash in"]),
    ("Send Money",      ["sent to", "send money", "transfer to", "you sent"]),
    ("Receive Money",   ["received from", "you received", "payment from", "accepted"]),
    ("Business Payment",["business payment", "salary", "wages", "payroll"]),
]

def categorise(detail: str) -> str:
    if not detail:
        return "Other"
    d = str(detail).lower()
    for cat, keywords in CATEGORY_RULES:
        if any(kw in d for kw in keywords):
            return cat
    return "Other"

SENT_PATTERN = re.compile(
    r"(?:sent to|transfer to|you sent.+?to|send money to|payment to.*?to)\s*(?:-\s*)?(?:[\dxX*]+\s+)?([A-Za-z][A-Za-z\s\-']{2,40}?)(?=\s+on\s|\s+via\s|$|\.|,)",
    re.IGNORECASE | re.DOTALL
)
RECV_PATTERN = re.compile(
    r"(?:received from|funds received from|payment from|from)\s*(?:-\s*)?(?:[\dxX*]+\s+)?([A-Za-z][A-Za-z\s\-']{2,40}?)(?=\s+on\s|\s+via\s|$|\.|,)",
    re.IGNORECASE | re.DOTALL
)

def extract_person(detail, direction):
    if not detail:
        return None
    pattern = SENT_PATTERN if direction == "sent" else RECV_PATTERN
    m = pattern.search(str(detail))
    if not m:
        return None
    name = m.group(1).strip().title()
    if not (4 <= len(name) <= 45) or re.search(r"\d", name):
        return None
    NOISE = {"safaricom", "mpesa", "m-pesa", "equity", "kcb", "co-op", "coop",
              "standard", "barclays", "absa", "stanbic", "airtel", "telkom",
              "nairobi", "kenya", "limited", "ltd", "company", "paybill"}
    if any(tok.lower() in NOISE for tok in name.split()):
        return None
    return name

def parse_mpesa_statement(file_obj, password):
    raw_rows = []
    with pdfplumber.open(file_obj, password=password) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                if not table or not table[0]:
                    continue
                first = " ".join(str(c or "") for c in table[0])
                if "Receipt" in first or "Details" in first or len(table[0]) >= 5:
                    raw_rows.extend(table)
                    
    if not raw_rows:
        raise ValueError("No transaction table found in the PDF.")

    HEADER_KEYWORDS = {"receipt", "completion", "initiation", "details", "paid", "withdrawn", "balance"}
    header_idx = 0
    for i, row in enumerate(raw_rows):
        cells = [str(c or "").lower() for c in row]
        if sum(any(kw in c for kw in HEADER_KEYWORDS) for c in cells) >= 3:
            header_idx = i
            break

    raw_headers = [str(c or "").strip().replace("\n", " ") for c in raw_rows[header_idx]]
    col_names = [norm_col(h) for h in raw_headers]
    
    # Process into dicts
    transactions = []
    seen = set()
    
    for row in raw_rows[header_idx + 1:]:
        if not row or all(not c for c in row):
            continue
            
        row_dict = dict(zip(col_names, row))
        
        # Skip header repeats
        rno = str(row_dict.get("receipt_no", "")).lower()
        if not rno or len(rno) < 5 or re.search(r"receipt|no\.|^#$|details|completion", rno):
            continue
            
        # Parse amounts
        paid_in = parse_amount(row_dict.get("paid_in", ""))
        withdrawn = parse_amount(row_dict.get("withdrawn", ""))
        balance = parse_amount(row_dict.get("balance", ""))
        
        # Fix parsing artifact (both > 0)
        if paid_in > 0 and withdrawn > 0:
            paid_in = 0.0
            
        # Parse date
        date_src = row_dict.get("completion_time") or row_dict.get("initiation_time") or ""
        if not date_src:
            continue
            
        try:
            # Assuming YYYY-MM-DD HH:MM:SS format based on previous fixes
            dt = datetime.strptime(date_src.strip(), "%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
            
        # Deduplication using a stable tuple representation of the row
        row_tuple = (
            str(row_dict.get("receipt_no", "")).strip(),
            date_src.strip(),
            str(row_dict.get("details", "")).strip(),
            paid_in,
            withdrawn,
            balance
        )
        if row_tuple in seen:
            continue
        seen.add(row_tuple)
        
        details = str(row_dict.get("details", "")).strip()
        category = categorise(details)
        
        direction = "none"
        if withdrawn > 0: direction = "sent"
        elif paid_in > 0: direction = "received"
        
        person = extract_person(details, direction)
        
        transactions.append({
            "receipt_no": str(row_dict.get("receipt_no", "")).strip(),
            "date_obj": dt,
            "date_str": dt.strftime("%d %b %Y %H:%M"),
            "month_key": dt.strftime("%Y-%m"),
            "month_label": dt.strftime("%b %Y"),
            "day_of_week": dt.strftime("%A"),
            "hour": dt.hour,
            "details": details,
            "category": category,
            "direction": direction,
            "paid_in": paid_in,
            "withdrawn": withdrawn,
            "balance": balance,
            "person": person
        })
        
    if not transactions:
        raise ValueError("No valid transactions could be parsed.")

    # Sort chronologically
    transactions.sort(key=lambda x: x["date_obj"])
    
    # KPIs
    fee_mask_fn = lambda t: t["category"] == "Charges & Fees"
    total_in = sum(t["paid_in"] for t in transactions)
    total_out = sum(t["withdrawn"] for t in transactions)
    total_fees = sum(t["withdrawn"] for t in transactions if fee_mask_fn(t))
    net = total_in - total_out
    
    biggest_in = max((t["paid_in"] for t in transactions), default=0)
    biggest_out = max((t["withdrawn"] for t in transactions), default=0)
    
    spend_txs = [t["withdrawn"] for t in transactions if t["withdrawn"] > 0 and not fee_mask_fn(t)]
    recv_txs = [t["paid_in"] for t in transactions if t["paid_in"] > 0]
    
    avg_spend = sum(spend_txs) / len(spend_txs) if spend_txs else 0
    avg_receive = sum(recv_txs) / len(recv_txs) if recv_txs else 0
    
    opening_balance = transactions[0]["balance"] + transactions[0]["withdrawn"] - transactions[0]["paid_in"]
    closing_balance = transactions[-1]["balance"]
    
    kpis = dict(
        total_in=round(total_in, 2), total_out=round(total_out, 2), net=round(net, 2), tx_count=len(transactions),
        total_fees=round(total_fees, 2), biggest_in=round(biggest_in, 2), biggest_out=round(biggest_out, 2),
        avg_spend=round(avg_spend, 2), avg_receive=round(avg_receive, 2),
        opening_balance=round(opening_balance, 2), closing_balance=round(closing_balance, 2)
    )
    
    # Monthly Breakdown
    monthly_dict = defaultdict(lambda: {"total_in": 0.0, "total_out": 0.0, "count": 0, "month": ""})
    for t in transactions:
        mk = t["month_key"]
        monthly_dict[mk]["month"] = t["month_label"]
        monthly_dict[mk]["total_in"] += t["paid_in"]
        monthly_dict[mk]["total_out"] += t["withdrawn"]
        monthly_dict[mk]["count"] += 1
        
    monthly = []
    for mk in sorted(monthly_dict.keys()):
        m = monthly_dict[mk]
        monthly.append({
            "month_key": mk,
            "month": m["month"],
            "total_in": round(m["total_in"], 2),
            "total_out": round(m["total_out"], 2),
            "net": round(m["total_in"] - m["total_out"], 2),
            "count": m["count"]
        })
        
    # Categories
    def cat_summary(amt_col, top_n=None):
        cat_dict = defaultdict(lambda: {"total": 0.0, "count": 0})
        total_all = 0.0
        for t in transactions:
            amt = t[amt_col]
            if amt > 0:
                cat_dict[t["category"]]["total"] += amt
                cat_dict[t["category"]]["count"] += 1
                total_all += amt
                
        res = []
        for cat, data in sorted(cat_dict.items(), key=lambda x: x[1]["total"], reverse=True):
            res.append({
                "category": cat,
                "total": round(data["total"], 2),
                "count": data["count"],
                "pct": round(data["total"] / total_all * 100, 1) if total_all else 0.0
            })
        return res[:top_n] if top_n else res

    cat_out = cat_summary("withdrawn")
    cat_in = cat_summary("paid_in")
    
    balance_series = [{"date_str": t["date_str"], "balance": t["balance"]} for t in transactions]
    
    # Top People
    def top_people(amt_col, top_n=20):
        people_dict = defaultdict(lambda: {"total": 0.0, "count": 0})
        for t in transactions:
            if t["person"] and t[amt_col] > 0:
                people_dict[t["person"]]["total"] += t[amt_col]
                people_dict[t["person"]]["count"] += 1
                
        res = []
        for person, data in sorted(people_dict.items(), key=lambda x: x[1]["total"], reverse=True):
            res.append({
                "person": person,
                "total": round(data["total"], 2),
                "count": data["count"]
            })
        return res[:top_n]

    top_recipients = top_people("withdrawn")
    top_senders = top_people("paid_in")
    
    # People details
    people_detail = {}
    for t in transactions:
        p = t["person"]
        if p:
            if p not in people_detail:
                people_detail[p] = {
                    "name": p,
                    "total_sent": 0.0,
                    "total_received": 0.0,
                    "tx_count": 0,
                    "transactions": [],
                    "first_dt": t["date_obj"],
                    "last_dt": t["date_obj"]
                }
            pd = people_detail[p]
            pd["total_sent"] += t["withdrawn"]
            pd["total_received"] += t["paid_in"]
            pd["tx_count"] += 1
            pd["first_dt"] = min(pd["first_dt"], t["date_obj"])
            pd["last_dt"] = max(pd["last_dt"], t["date_obj"])
            pd["transactions"].append({
                "date": t["date_str"],
                "details": t["details"],
                "paid_in": t["paid_in"],
                "withdrawn": t["withdrawn"],
                "balance": t["balance"],
                "category": t["category"],
                "receipt_no": t["receipt_no"],
                "date_obj": t["date_obj"]
            })
            
    for pd in people_detail.values():
        pd["total_sent"] = round(pd["total_sent"], 2)
        pd["total_received"] = round(pd["total_received"], 2)
        pd["net"] = round(pd["total_received"] - pd["total_sent"], 2)
        pd["first_tx"] = pd["first_dt"].strftime("%d %b %Y")
        pd["last_tx"] = pd["last_dt"].strftime("%d %b %Y")
        pd["transactions"].sort(key=lambda x: x["date_obj"], reverse=True)
        # Remove datetime objects from JSON
        for tx in pd["transactions"]:
            del tx["date_obj"]
        del pd["first_dt"]
        del pd["last_dt"]
        
    # DOW
    DOW_ORDER = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    dow_dict = {d: {"spent": 0.0, "received": 0.0, "count": 0} for d in DOW_ORDER}
    for t in transactions:
        d = t["day_of_week"]
        dow_dict[d]["spent"] += t["withdrawn"]
        dow_dict[d]["received"] += t["paid_in"]
        dow_dict[d]["count"] += 1
        
    dow = []
    for d in DOW_ORDER:
        v = dow_dict[d]
        dow.append({
            "day": d,
            "spent": round(v["spent"], 2),
            "received": round(v["received"], 2),
            "count": v["count"]
        })
        
    # Hourly
    hourly_dict = {h: {"spent": 0.0, "count": 0} for h in range(24)}
    for t in transactions:
        h = t["hour"]
        hourly_dict[h]["spent"] += t["withdrawn"]
        hourly_dict[h]["count"] += 1
        
    hourly = []
    for h in range(24):
        hourly.append({
            "hour": h,
            "spent": round(hourly_dict[h]["spent"], 2),
            "count": hourly_dict[h]["count"]
        })
        
    # All tx (reversed)
    all_tx = []
    for t in reversed(transactions):
        tx_copy = t.copy()
        del tx_copy["date_obj"]
        all_tx.append(tx_copy)
        
    # Insights
    insights = []
    if monthly:
        best = max(monthly, key=lambda x: x["net"])
        worst = min(monthly, key=lambda x: x["net"])
        insights.append({"type":"best_month", "month": best["month"], "value": best["net"]})
        insights.append({"type":"worst_month", "month": worst["month"], "value": worst["net"]})
        
    if biggest_in > 0:
        bi = max(transactions, key=lambda x: x["paid_in"])
        insights.append({"type":"biggest_receive","value":bi["paid_in"],"detail":bi["details"],"date":bi["date_str"]})
    if biggest_out > 0:
        bo = max(transactions, key=lambda x: x["withdrawn"])
        insights.append({"type":"biggest_spend","value":bo["withdrawn"],"detail":bo["details"],"date":bo["date_str"]})
        
    if dow:
        mad = max(dow, key=lambda x: x["count"])
        insights.append({"type":"most_active_day","day":mad["day"],"count":mad["count"]})
        
    surplus_months = sum(1 for m in monthly if m["net"] > 0)
    insights.append({"type":"surplus_months","value":surplus_months,"total":len(monthly)})
    
    if cat_out:
        tc = cat_out[0]
        insights.append({"type":"top_category","category":tc["category"],"value":tc["total"],"pct":tc["pct"]})
        
    insights.append({"type":"people_count","value":len(people_detail)})
    
    min_date = transactions[0]["date_obj"].strftime('%d %b %Y')
    max_date = transactions[-1]["date_obj"].strftime('%d %b %Y')
    
    return {
        "kpis": kpis,
        "monthly": monthly,
        "cat_out": cat_out,
        "cat_in": cat_in,
        "balance_series": balance_series,
        "top_recipients": top_recipients,
        "top_senders": top_senders,
        "people": people_detail,
        "dow": dow,
        "hourly": hourly,
        "all_tx": all_tx,
        "insights": insights,
        "meta": {
            "statement_period": f"{min_date} – {max_date}",
            "generated_at": datetime.now().strftime("%d %b %Y %H:%M"),
        }
    }

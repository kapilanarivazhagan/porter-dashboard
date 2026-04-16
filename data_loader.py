import gspread
import pandas as pd
import re
from google.oauth2.service_account import Credentials


# ===============================
# SETUP
# ===============================

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

CREDS = Credentials.from_service_account_file(
    r"C:\Users\SPURGE\Desktop\Projects\Insights Report\porter_report\credentials.json",
    scopes=SCOPES
)

client = gspread.authorize(CREDS)

SHEET_URL = "https://docs.google.com/spreadsheets/d/1qvadntz8DAWWmtEZ23L-cQE8hOyqRrR5eZuVK7yZp74"


# ===============================
# SHEET FILTER (STRICT)
# ===============================

def is_valid_month_sheet(name: str) -> bool:
    pattern = r"^[A-Za-z]{3}\s\d{2}$"
    return bool(re.match(pattern, name.strip()))


# ===============================
# LOAD ALL MONTHS (FULL LOAD - RARE USE)
# ===============================

def load_sheet():

    sheet = client.open_by_url(SHEET_URL)
    worksheets = sheet.worksheets()

    all_data = []
    loaded_sheets = []

    for ws in worksheets:
        name = ws.title.strip()

        if not is_valid_month_sheet(name):
            continue

        try:
            data = ws.get_all_records()
            if not data:
                continue

            df = pd.DataFrame(data)
            df["source_sheet"] = name

            all_data.append(df)
            loaded_sheets.append(name)

        except Exception as e:
            print(f"⚠️ Failed loading {name}: {e}")

    if not all_data:
        raise ValueError("❌ No valid data loaded")

    final_df = pd.concat(all_data, ignore_index=True)

    if "Order Date" in final_df.columns:
        final_df["Order Date"] = pd.to_datetime(
            final_df["Order Date"], errors="coerce"
        )

    final_df = final_df.dropna(subset=["Order Date"])

    print("✅ Full load complete")
    print("📊 Total rows:", len(final_df))

    return final_df


# ===============================
# LOAD SINGLE DATE (FAST - MAIN USE)
# ===============================

def load_by_date(target_date):

    target_date = pd.to_datetime(target_date)
    sheet_name = target_date.strftime("%b %y")  # Example: Apr 26

    sheet = client.open_by_url(SHEET_URL)

    try:
        ws = sheet.worksheet(sheet_name)
    except:
        raise ValueError(f"❌ Sheet not found: {sheet_name}")

    data = ws.get_all_records()

    if not data:
        raise ValueError(f"❌ No data in sheet: {sheet_name}")

    df = pd.DataFrame(data)

    if "Order Date" not in df.columns:
        raise ValueError("❌ 'Order Date' column missing")

    df["Order Date"] = pd.to_datetime(df["Order Date"], errors="coerce")

    df = df[df["Order Date"] == target_date]

    print(f"✅ Loaded {len(df)} rows for {target_date.date()} from {sheet_name}")

    return df


# ===============================
# LOAD MULTIPLE DATES (MANUAL MODE)
# ===============================

def load_multiple_dates(date_list):

    all_data = []

    for d in date_list:
        try:
            df = load_by_date(d)
            all_data.append(df)
        except Exception as e:
            print(f"⚠️ Failed for {d}: {e}")

    if not all_data:
        raise ValueError("❌ No data loaded for given dates")

    final_df = pd.concat(all_data, ignore_index=True)

    print(f"✅ Loaded multiple dates → {len(final_df)} rows")

    return final_df
import pandas as pd


# ===============================
# HELPER FUNCTIONS
# ===============================

def safe_numeric(series):
    return pd.to_numeric(series, errors="coerce")


def clean_percentage(series):
    return (
        series.astype(str)
        .str.replace("%", "", regex=False)
        .str.strip()
        .replace("", None)
        .pipe(pd.to_numeric, errors="coerce")
    )


# ===============================
# MAIN CLEAN FUNCTION
# ===============================

def clean_data(df: pd.DataFrame, remove_compact=True) -> pd.DataFrame:

    df = df.copy()

    # ===============================
    # COLUMN STANDARDIZATION
    # ===============================

    df.columns = df.columns.str.strip()

    # ===============================
    # DATE CLEANING
    # ===============================

    df["Order Date"] = pd.to_datetime(df["Order Date"], errors="coerce")
    df = df.dropna(subset=["Order Date"])

    # ===============================
    # STRING CLEANING
    # ===============================

    df["City"] = df["City"].astype(str).str.strip().str.lower()
    df["Vehicle Number"] = df["Vehicle Number"].astype(str).str.strip()
    df["Driver Name"] = df["Driver Name"].astype(str).str.strip()
    df["Veh Type"] = df["Veh Type"].astype(str).str.strip()

    # ===============================
    # REMOVE COMPACT 3W (CONTROLLED)
    # ===============================

    if remove_compact:
        df = df[~df["Veh Type"].str.lower().str.strip().eq("compact 3w")]

    # ===============================
    # NUMERIC CLEANING
    # ===============================

    numeric_cols = [
        "Earnings",
        "Login Hours",
        "Distance Travelled",
        "Completed Orders",
        "missed_notifs_overall",
        "partner_cancellation"
    ]

    for col in numeric_cols:
        if col in df.columns:
            df[col] = safe_numeric(df[col])

    # ===============================
    # PERCENT CLEANING
    # ===============================

    if "Completion %" in df.columns:
        df["Completion %"] = clean_percentage(df["Completion %"])

    # ===============================
    # MISSING VALUE HANDLING
    # ===============================

    df["Completed Orders"] = df["Completed Orders"].fillna(0)
    df["missed_notifs_overall"] = df["missed_notifs_overall"].fillna(0)
    df["partner_cancellation"] = df["partner_cancellation"].fillna(0)

    # ===============================
    # DERIVED METRICS (OPTIONAL)
    # ===============================

    df["orders_per_hour"] = df["Completed Orders"] / df["Login Hours"]
    df["earnings_per_order"] = df["Earnings"] / df["Completed Orders"]

    df["orders_per_hour"] = df["orders_per_hour"].replace([float("inf"), -float("inf")], pd.NA)
    df["earnings_per_order"] = df["earnings_per_order"].replace([float("inf"), -float("inf")], pd.NA)

    df["orders_per_hour"] = pd.to_numeric(df["orders_per_hour"], errors="coerce")
    df["earnings_per_order"] = pd.to_numeric(df["earnings_per_order"], errors="coerce")

    # ===============================
    # LOGIN TIME CLEANING
    # ===============================

    if "Login Time" in df.columns:
        df["Login Time"] = pd.to_datetime(
            df["Login Time"],
            format="%H:%M:%S",
            errors="coerce"
        ).dt.time

    # ===============================
    # FINAL FILTER
    # ===============================

    df = df[df["Login Hours"] >= 0]

    return df
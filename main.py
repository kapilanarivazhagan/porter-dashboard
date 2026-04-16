from datetime import datetime, timedelta

from data_loader import load_multiple_dates
from cleaner import clean_data
from metrics import build_metrics
from ai_insights import generate_city_insights, format_insights
from html_template import generate_html


# ===============================
# CONFIG
# ===============================

MODE = "auto"  

MANUAL_DATES = [
    "2026-04-10"
]


# ===============================
# DATE LOGIC
# ===============================

def get_auto_date():
    today = datetime.today()

    d_minus_1 = today - timedelta(days=1)

    # Skip Sunday
    if d_minus_1.weekday() == 6:
        d_minus_1 = today - timedelta(days=2)

    return d_minus_1.strftime("%Y-%m-%d")


# ===============================
# RUN FOR ONE DATE
# ===============================

def run_for_date(date):

    print(f"\n📅 Processing: {date}")

    try:
        target_date = datetime.strptime(date, "%Y-%m-%d")
        yday = (target_date - timedelta(days=1)).strftime("%Y-%m-%d")

        dates = [
            (target_date - timedelta(days=i)).strftime("%Y-%m-%d")
            for i in range(7)
        ]

        df = load_multiple_dates(dates)
        print(f"Rows loaded: {len(df)}")

        # ===============================
        # CLEAN DATA
        # ===============================
        clean_df = clean_data(df.copy(), remove_compact=True)

        # ===============================
        # BUILD METRICS
        # ===============================
        result = build_metrics(clean_df, date, city="all")

        # ===============================
        # KPI OUTPUT
        # ===============================
        print("\n🔝 KPI")
        for k, v in result["kpis"].items():
            print(f"{k}: {v}")

        # ===============================
        # CHART DATA
        # ===============================
        print("\n📊 City Earnings")
        print(result["charts"]["city_earnings"])

        # ===============================
        # COMPLETION CHECK
        # ===============================
        print("\n📊 CITY-WISE COMPLETION")

        city_completion = clean_df.groupby("City")["Completion %"].mean().reset_index()
        city_completion["Completion %"] = city_completion["Completion %"].round(0)

        print(city_completion)

        # ===============================
        # 🧠 INSIGHTS
        # ===============================
        print("\n🧠 INSIGHTS")

        city_data = result["city_data"]

        insights = generate_city_insights(city_data)
        formatted = format_insights(insights)

        for line in formatted:
            print(line)

        # ===============================
        # 🌐 GENERATE HTML (FIXED)
        # ===============================
        html_content = generate_html(
            {
                "kpis": result["kpis"],
                "charts": result["charts"],
                "city_data": result["city_data"], 
                "insights": insights
            },
            date
        )

        # ===============================
        # SAVE HTML
        # ===============================
        filename = "porter_report.html"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"\n✅ HTML saved: {filename}")

    except Exception as e:
        print(f"❌ Failed for {date}: {e}")


# ===============================
# MAIN FLOW
# ===============================

if __name__ == "__main__":

    if MODE == "manual":

        for date in MANUAL_DATES:
            run_for_date(date)

    else:

        target_date = get_auto_date()
        print(f"\n📅 Auto mode date: {target_date}")

        run_for_date(target_date)

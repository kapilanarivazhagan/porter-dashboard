from datetime import datetime
from html import escape
import json


def format_date(date_str):
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return dt.strftime("&#128202; Porter Report - %d %B")


def format_inr(val):
    return f"{chr(8377)}{int(val):,}"


def _json_records(data):
    if data is None:
        return []

    if isinstance(data, list):
        records = data
    else:
        records = data.to_dict(orient="records")

    clean_records = []

    for record in records:
        clean = {}

        for key, value in record.items():
            if value != value:
                clean[key] = None
            else:
                clean[key] = value

        clean_records.append(clean)

    return clean_records


def _chart_payload(trend):
    records = _json_records(trend)
    date_keys = sorted({record["Order Date"].strftime("%Y-%m-%d") if hasattr(record["Order Date"], "strftime") else str(record["Order Date"])[:10] for record in records})
    labels = []

    for date_key in date_keys:
        dt = datetime.strptime(date_key, "%Y-%m-%d")
        labels.append(dt.strftime("%b %d (%a)"))

    cities = sorted({str(record["City"]) for record in records})
    datasets = []

    for city in cities:
        city_records = {}

        for record in records:
            record_city = str(record["City"])
            raw_date = record["Order Date"]
            date_key = raw_date.strftime("%Y-%m-%d") if hasattr(raw_date, "strftime") else str(raw_date)[:10]

            if record_city == city:
                city_records[date_key] = int(round(record["Earnings"], 0))

        datasets.append({
            "label": city,
            "data": [city_records.get(date_key, None) for date_key in date_keys],
        })

    return {
        "labels": labels,
        "datasets": datasets,
    }


def _allow_strong(text):
    safe = escape(str(text))
    return (
        safe
        .replace("&lt;strong&gt;", "<strong>")
        .replace("&lt;/strong&gt;", "</strong>")
    )


def _insight_text(text):
    return _allow_strong(text)


# ===============================
# CHANGE FORMAT
# ===============================
def fmt_change(change, metric):

    change = float(change or 0)

    if change == 0:
        return "0.0%"

    arrow = "&#8593;" if change > 0 else "&#8595;"

    return f"{arrow} {abs(change):.1f}%"


def change_class(change, metric):

    change = float(change or 0)

    if change == 0:
        return "change neutral"

    if metric == "missed":
        good = change < 0
    else:
        good = change > 0

    tone = "positive" if good else "negative"

    return f"change {tone}"


def generate_html(report_data, date):

    kpis = report_data["kpis"]
    city_data = report_data["city_data"]
    charts = report_data.get("charts", {})
    insights = report_data["insights"]

    # ===============================
    # CITY DATA
    # ===============================
    city_kpi = {}
    for _, row in city_data.iterrows():
        drivers = int(row.get("Drivers Reported", 0) or 0)
        driver_count = max(drivers, 1)

        city_kpi[row["City"]] = {
            "earnings": format_inr(row["Earnings"]),
            "orders": int(row["Completed Orders"]),
            "completion": int(round(row["Completion %"])),
            "drivers": drivers,
            "missed": int(row["missed_notifs_overall"]),
            "avg_earnings": format_inr(row["Earnings"] / driver_count),
            "avg_orders": int(row["Completed Orders"] / driver_count),
            "earnings_change": float(row.get("earnings_change", 0) or 0),
            "avg_earnings_change": float(row.get("avg_earnings_change", 0) or 0),
            "completion_change": float(row.get("completion_change", 0) or 0),
            "orders_change": float(row.get("orders_change", 0) or 0),
            "orders_change_abs": int(row.get("orders_change_abs", 0) or 0),
            "avg_orders_change": float(row.get("avg_orders_change", 0) or 0),
            "drivers_change": float(row.get("drivers_change", 0) or 0),
            "missed_change": float(row.get("missed_change", 0) or 0)
        }

    city_kpi_json = json.dumps(city_kpi, ensure_ascii=False)
    chart_json = json.dumps(
        {
            "cityEarningsTrend": _chart_payload(charts.get("city_earnings_trend")),
        },
        ensure_ascii=False,
    )

    # ===============================
    # INSIGHTS
    # ===============================
    insights_html = ""
    for ins in insights:
        city_key = escape(str(ins["city"]).lower())
        city_label = escape(str(ins.get("city_label", "All Cities" if city_key == "all" else str(ins["city"]).title())))
        what_changed = ins.get("what_changed", {})
        key_issue = _insight_text(ins.get("key_issue", ins.get("what", "")))
        action_plan = _insight_text(ins.get("action_plan", ins.get("action", "")))
        trend_line = _insight_text(ins.get("trend_line", ins.get("why", "")))
        earnings_change = _insight_text(what_changed.get("earnings", "Earnings 0.0%"))
        completion_change = _insight_text(what_changed.get("completion", "Completion 0.0%"))
        orders_change = _insight_text(what_changed.get("orders", "Orders 0.0%"))

        insights_html += f"""
        <article class="insight-card" data-city="{city_key}">
            <div class="insight-city">&#128205; {city_label}</div>

            <div class="insight-block">
                <div class="insight-label">&#9888; Key Issue:</div>
                <p>{key_issue}</p>
            </div>

            <div class="insight-block">
                <div class="insight-label">&#128202; What Changed:</div>
                <div class="change-story">
                    <p>{earnings_change}</p>
                    <p>{completion_change}</p>
                    <p>{orders_change}</p>
                </div>
                <p class="trend-line">{trend_line}</p>
            </div>

            <div class="insight-block">
                <div class="insight-label">&#128640; Action Plan:</div>
                <p>{action_plan}</p>
            </div>
        </article>
        """

    options = "".join([
        f'<option value="{escape(str(c))}">{escape(str(c).title())}</option>'
        for c in city_data["City"]
    ])

    # ===============================
    # HTML
    # ===============================
    html = f"""
    <html>
    <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <style>

    * {{
        box-sizing: border-box;
    }}

    html,
    body {{
        height: 100%;
        margin: 0;
        overflow-x: hidden;
        overflow-y: auto;        
    }}

    body {{
        font-family: Arial, sans-serif;
        background:
        linear-gradient(rgba(10,10,20,0.45), rgba(10,10,20,0.7)),
        url("Ready-for-migrating-to-an-electric-vehicle-fleet.jpg");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;  
    }}

    .app-shell {{
        display: flex;
        flex-direction: column;
        height: 100vh;
        min-height: 100vh;
    }}

    .header {{
        flex: 0 0 auto;
        text-align: center;
        padding: 14px 16px 8px;
        font-size: 30px;
        font-weight: 900;
        color: #ffffff;   /* 🔥 pure white */
        letter-spacing: 0.06em;
        text-shadow: 0 2px 10px rgba(0,0,0,0.6);
    }}

    .filter {{
        flex: 0 0 auto;
        text-align: center;
        padding-bottom: 8px;
    }}

    select {{
        min-width: 170px;
        padding: 7px 11px;
        border-radius: 6px;
        background: rgba(15,23,42,0.84);
        color: white;
        border: 1px solid rgba(148,163,184,0.28);
        outline: none;
    }}

    .dashboard-viewport {{
        flex: 1 1 auto;
        min-height: 0;
        padding: 0 14px 10px;
        overflow: hidden;
    }}

    .dashboard-track {{
        display: grid;
        grid-template-columns: 25% 75%;
        grid-template-rows: 1fr 1fr;
        gap: 12px;
        height: 100%;
        min-height: 0;
    }}

    .page {{
        min-width: 0;
        min-height: 0;
    }}

    .kpi-page {{
        grid-column: 1;
        grid-row: 1 / span 2;
    }}

    .insights-page {{
        grid-column: 2;
        grid-row: 1;
    }}

    .chart-page {{
        grid-column: 2;
        grid-row: 2;
    }}

    .section-panel {{
        display: flex;
        flex-direction: column;
        height: 100%;
        min-height: 0;
        background: rgba(15,23,42,0.18);
        border: 1px solid rgba(148,163,184,0.12);
        border-radius: 8px;
        backdrop-filter: blur(14px);
        padding: 10px;
    }}

    .section-title {{
        color: #ffffff;
        font-weight: 900;
        letter-spacing: 0.08em; 
        flex: 0 0 auto;
        margin: 0 0 8px;
        padding-bottom: 7px;
        border-bottom: 1px solid rgba(148,163,184,0.2);
        font-size: 13px;
        font-weight: 800;
        letter-spacing: 0.08em;
        text-transform: uppercase;
    }}

    /* KPI PANEL */
    .kpi-stack {{
        flex: 1 1 auto;
        min-height: 0;
        display: grid;
        grid-template-rows: repeat(7, 1fr);
        gap: 7px;
    }}

    .kpi-card {{
        display: grid;
        grid-template-columns: minmax(86px, 1fr) minmax(72px, auto) minmax(66px, auto);
        align-items: center;
        gap: 8px;
        min-height: 0;
        background: rgba(30,41,59,0.35);
        border: 1px solid rgba(148,163,184,0.18);
        border-radius: 8px;
        padding: 8px 10px;
        backdrop-filter: blur(12px);
        box-shadow: 0 10px 24px rgba(2,6,23,0.16);
    }}

    .kpi-card .label {{
        min-width: 0;
        color: #e2e8f0;
        font-size: 10px;
        font-weight: 800;
        letter-spacing: 0.04em;
        text-align: left;
        text-transform: uppercase;
        white-space: normal;
    }}

    .kpi-card .value {{
        color: #f8fafc;
        font-size: 18px;
        font-weight: 800;
        line-height: 1;
        text-align: center;
        white-space: nowrap;
    }}


    /* KPI VALUE COLORS */
    .kpi-card.earnings .value {{
        color: #4ade80;   /* green */
    }}

    .kpi-card.avg .value {{
        color: #38bdf8;   /* cyan */
    }}

    .kpi-card.completion .value {{
        color: #60a5fa;   /* blue */
    }}

    .kpi-card.orders .value {{
        color: #fbbf24;   /* yellow */
    }}

    .kpi-card.drivers .value {{
        color: #a78bfa;   /* purple */
    }}

    .kpi-card.missed .value {{
        color: #f87171;   /* red */
    }}

    .change {{
        color: #94a3b8;
        font-size: 14px;
        font-weight: 700;
        text-align: right;
        text-shadow: 0 0 10px currentColor;
        white-space: nowrap;
    }}

    .change.positive {{
        color: #4ade80;
        text-shadow: 0 0 8px rgba(74,222,128,0.6);
    }}

    .change.negative {{
        color: #f87171;
        text-shadow: 0 0 8px rgba(248,113,113,0.6);
    }}

    .change.neutral {{
        color: #94a3b8;
        text-shadow: none;
    }}

    .earnings {{ border-left: 4px solid #4ade80; }}
    .completion {{ border-left: 4px solid #60a5fa; }}
    .orders {{ border-left: 4px solid #fbbf24; }}
    .drivers {{ border-left: 4px solid #a78bfa; }}
    .avg {{ border-left: 4px solid #38bdf8; }}
    .missed {{ border-left: 4px solid #f87171; }}

    /* INSIGHTS */
    .insights-list {{
        flex: 1 1 auto;
        min-height: 0;
    }}

    .insights {{
        height: 100%;
        overflow-y: auto;
        padding-right: 6px;
    }}

    .insight-card {{
        min-height: 100%;
        background: rgba(30,41,59,0.32);
        border: 1px solid rgba(148,163,184,0.16);
        border-radius: 8px;
        padding: 16px;
        line-height: 1.35;
        margin-bottom: 10px;
    }}

    .insight-card:last-child {{
        margin-bottom: 0;
    }}

    .insight-city {{
        margin-bottom: 12px;
        color: #bfdbfe;
        font-size: 15px;
        font-weight: 800;
        text-transform: uppercase;
    }}

    .insight-block {{
        margin-bottom: 13px;
    }}

    .insight-block:last-child {{
        margin-bottom: 0;
    }}

    .insight-label {{
        color: #ffffff;
        font-weight: 700;
        font-size: 12px;
        letter-spacing: 0.04em;
        margin-bottom: 5px;
    }}

    .insight-block p {{
        margin: 0;
        font-size: 14px;
        color: #e2e8f0; 
        font-weight: 400;   
    }}

    .change-story p {{
        margin: 0 0 6px;
        font-size: 14px;
        color: #f1f5f9;
    }}

    .change-story p:last-child {{
        margin-bottom: 0;
    }}

    .trend-line {{
        margin-top: 7px !important;
        color: #cbd5f5 !important;
        font-size: 13px !important;
    }}

    strong {{
        color: #f8fafc;
    }}

    /* CHART */
    .chart-card {{
        display: flex;
        flex-direction: column;
        flex: 1 1 auto;
        min-height: 0;
        height: 100%;
        background: rgba(30,41,59,0.28);
        border: 1px solid rgba(148,163,184,0.16);
        border-radius: 8px;
        padding: 10px;
    }}

    .chart-container {{
        flex: 1 1 auto;
        min-height: 0;
        width: 100%;
        height: 100%;
    }}

    .chart-title {{
        height: auto;
        margin-bottom: 6px;
        color: #cbd5e1;
        font-size: 12px;
        font-weight: 800;
        letter-spacing: 0.04em;
        text-transform: uppercase;
    }}

    .chart-subtitle {{
        margin-bottom: 6px;
        color: #94a3b8;
        font-size: 12px;
    }}

    canvas {{
        display: block;
        width: 100%;
        height: 100% !important;
        width: 100% !important;
    }}

    .empty-chart {{
        color: #94a3b8;
        font-size: 14px;
    }}

    .mobile-dots {{
        display: none;
        flex: 0 0 auto;
    }}

    .footer {{
        flex: 0 0 auto;
        text-align: center;
        padding: 7px;
        border-top: 1px solid rgba(148,163,184,0.18);
        color: #94a3b8;
        font-size: 11px;
    }}

    @media (max-width: 920px) {{
        .header {{
            padding-top: 10px;
            font-size: 21px;
        }}

        .filter {{
            padding-bottom: 6px;
        }}

        .dashboard-viewport {{
            padding: 0;
        }}

        .dashboard-track {{
            display: flex;
            width: 300%;
            gap: 0;
            transform: translateX(0);
            transition: transform 280ms ease;
        }}

        .dashboard-viewport {{
            overflow-y: auto; 
        }}

        .page,
        .kpi-page,
        .insights-page, 
        .chart-page {{
            grid-column: auto;
            grid-row: auto;
            flex: 0 0 100vw;
            width: 100vw;
            height: 100%;
            padding: 0 10px;
        }}

        .kpi-card {{
            grid-template-columns: minmax(92px, 1fr) minmax(72px, auto) minmax(68px, auto);
        }}

        .insight-block p,
        .change-story p {{
            font-size: 13px;
        }}

        canvas {{
            min-height: 0;
        }}

        .mobile-dots {{
            display: flex;
            justify-content: center;
            gap: 8px;
            padding: 6px 0;
        }}

        .dot-indicator {{
            width: 7px;
            height: 7px;
            border-radius: 999px;
            background: rgba(148,163,184,0.36);
            border: none;
            padding: 0;
        }}

        .dot-indicator.active {{
            width: 22px;
            background: #60a5fa;
        }}

        .footer {{
            position: sticky;
            bottom: 0;
            background: rgba(15,23,42,0.9);
        }}  

        .footer {{
            display: block;
            font-size: 10px;
            padding: 6px;
            text-align: center;
            color: #94a3b8;
            border-top: 1px solid rgba(148,163,184,0.18);
        }}
    }}

    </style>

    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2"></script>
    <script>

    const cityData = {city_kpi_json};
    const chartData = {chart_json};
    const chartColors = ["#4ade80", "#60a5fa", "#fbbf24", "#a78bfa", "#38bdf8", "#f87171", "#fb7185", "#34d399"];
    const chartConfig = {{
        type: "line",
        data: {{
            labels: chartData.cityEarningsTrend.labels,
            datasets: chartData.cityEarningsTrend.datasets.map((dataset, index) => {{
                const color = chartColors[index % chartColors.length];

                return {{
                    label: dataset.label,
                    data: dataset.data,
                    borderColor: color,
                    backgroundColor: color,
                    spanGaps: true,
                    pointRadius: function(ctx) {{
                        const value = ctx.raw;
                        const data = ctx.dataset.data.filter((item) => item !== null);
                        const max = Math.max(...data);
                        const min = Math.min(...data);

                        if (value === max || value === min) {{
                            return 6;
                        }}

                        return 3;
                    }},
                    pointBackgroundColor: function(ctx) {{
                        const value = ctx.raw;
                        const data = ctx.dataset.data.filter((item) => item !== null);
                        const max = Math.max(...data);
                        const min = Math.min(...data);

                        if (value === max) return "#4ade80";
                        if (value === min) return "#f87171";
                        return ctx.dataset.borderColor;
                    }}
                }};
            }})
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            interaction: {{
                intersect: false,
                mode: "nearest"
            }},
            elements: {{
                line: {{
                    tension: 0.4,
                    borderWidth: 3
                }},
                point: {{
                    radius: 4,
                    hoverRadius: 7
                }}
            }},
            plugins: {{
                legend: {{
                    labels: {{
                        color: "#e2e8f0",
                        boxWidth: 12,
                        font: {{
                            size: 11
                        }}
                    }}
                }},
                tooltip: {{
                    callbacks: {{
                        label: function(context) {{
                            return context.dataset.label + ": ₹" + context.raw.toLocaleString();
                        }}
                    }}
                }},
                datalabels: {{
                    display: false,
                    color: function(ctx) {{
                        const index = ctx.dataIndex;
                        const data = ctx.dataset.data;

                        if (index === 0) return "#e2e8f0";

                        const prev = data[index - 1];
                        const curr = data[index];

                        if (curr > prev) return "#4ade80";
                        if (curr < prev) return "#f87171";

                        return "#94a3b8";
                    }},
                    align: "top",
                    offset: 6,
                    clip: false,
                    font: {{
                        size: 10,
                        weight: "bold"
                    }},
                    formatter: function(value) {{
                        return String.fromCharCode(8377) + value.toLocaleString();
                        return "₹" + value.toLocaleString();
                        const data = ctx.dataset.data.filter((item) => item !== null);
                        const max = Math.max(...data);
                        const min = Math.min(...data);

                        if (value === max || value === min) {{
                            return "₹" + value.toLocaleString();
                        }}

                        return "";
                    }}
                }}
            }},
            scales: {{
                x: {{
                    ticks: {{
                        color: "#94a3b8",
                        maxRotation: 0,
                        autoSkip: true
                    }},
                    grid: {{
                        color: "rgba(148,163,184,0.1)"
                    }}
                }},
                y: {{
                    display: false,
                    beginAtZero: true,
                    ticks: {{
                        color: "#cbd5e1",
                        callback: function(value) {{
                            return "₹" + value.toLocaleString();
                        }}
                    }},
                    grid: {{
                        color: "rgba(148,163,184,0.12)"
                    }}
                }}
            }}
        }},
        plugins: [ChartDataLabels]
    }};
    const legacyChartConfig = {{
        elements: {{
            line: {{
                tension: 0.4,
                borderWidth: 3
            }},
            point: {{
                radius: 4,
                hoverRadius: 7
            }}
        }}
    }};
    let activePage = 0;
    let touchStartX = 0;

    function formatChange(change, metric) {{
        const numericChange = Number(change) || 0;

        if (numericChange === 0) {{
            return {{ text: "0.0%", tone: "neutral" }};
        }}

        const isGood = metric === "missed" ? numericChange < 0 : numericChange > 0;
        const tone = isGood ? "positive" : "negative";
        const arrow = numericChange > 0 ? "&#8593;" : "&#8595;";

        return {{ text: `${{arrow}} ${{Math.abs(numericChange).toFixed(1)}}%`, tone }};
    }}

    function setKpi(id, value, change, metric) {{
        document.getElementById(id).innerText = value;
        const changeElement = document.getElementById(`${{id}}_change`);
        const changeState = formatChange(change, metric);
        changeElement.className = `change ${{changeState.tone}}`;
        changeElement.innerHTML = changeState.text;
    }}

    function filterInsights(city) {{
        document.querySelectorAll(".insight-card").forEach((card) => {{
            const cardCity = card.getAttribute("data-city");
            card.style.display = cardCity === city ? "block" : "none";
        }});
    }}

    function filterCity() {{
        const city = document.getElementById("cityFilter").value;
        const d = city === "all" ? null : cityData[city];

        setKpi("earnings", city === "all" ? "{format_inr(kpis['earnings'])}" : d.earnings, city === "all" ? {kpis['earnings_change']} : d.earnings_change, "earnings");
        setKpi("avg_earnings", city === "all" ? "{format_inr(kpis['avg_earnings'])}" : d.avg_earnings, city === "all" ? {kpis['avg_earnings_change']} : d.avg_earnings_change, "avg_earnings");
        setKpi("completion", city === "all" ? "{int(kpis['completion'])}%" : d.completion + "%", city === "all" ? {kpis['completion_change']} : d.completion_change, "completion");
        setKpi("drivers", city === "all" ? "{int(kpis['drivers'])}" : d.drivers, city === "all" ? {kpis['drivers_change']} : d.drivers_change, "drivers");
        setKpi("orders", city === "all" ? "{int(kpis['orders'])}" : d.orders, city === "all" ? {kpis['orders_change']} : d.orders_change, "orders");
        setKpi("avg_orders", city === "all" ? "{int(kpis['avg_orders'])}" : d.avg_orders, city === "all" ? {kpis['avg_orders_change']} : d.avg_orders_change, "avg_orders");
        setKpi("missed", city === "all" ? "{int(kpis['missed'])}" : d.missed, city === "all" ? {kpis['missed_change']} : d.missed_change, "missed");
        filterInsights(city);
    }}

    function setPage(page) {{
        activePage = Math.max(0, Math.min(2, page));
        const track = document.getElementById("dashboardTrack");

        if (window.matchMedia("(max-width: 920px)").matches) {{
            track.style.transform = `translateX(-${{activePage * 100}}vw)`;
        }} else {{
            track.style.transform = "";
        }}

        document.querySelectorAll(".dot-indicator").forEach((dot, index) => {{
            dot.classList.toggle("active", index === activePage);
        }});
    }}

    function initSwipe() {{
        const viewport = document.getElementById("dashboardViewport");

        viewport.addEventListener("touchstart", (event) => {{
            touchStartX = event.touches[0].clientX;
        }}, {{ passive: true }});

        viewport.addEventListener("touchend", (event) => {{
            const deltaX = event.changedTouches[0].clientX - touchStartX;

            if (Math.abs(deltaX) < 45) {{
                return;
            }}

            setPage(activePage + (deltaX < 0 ? 1 : -1));
        }}, {{ passive: true }});

        window.addEventListener("resize", () => setPage(activePage));
    }}

    function getNumber(value) {{
        return Number(value) || 0;
    }}

    function setEmpty(svg, message) {{
        svg.innerHTML = `<text x="50%" y="52%" text-anchor="middle" class="empty-chart">${{message}}</text>`;
    }}

    function scale(value, min, max, start, end) {{
        if (max === min) {{
            return (start + end) / 2;
        }}

        return start + ((value - min) / (max - min)) * (end - start);
    }}

    function smoothPath(points) {{
        if (points.length < 2) {{
            return "";
        }}

        let path = `M ${{points[0].x}} ${{points[0].y}}`;
        const tension = chartConfig.elements.line.tension;

        for (let index = 0; index < points.length - 1; index++) {{
            const current = points[index];
            const next = points[index + 1];
            const previous = points[index - 1] || current;
            const following = points[index + 2] || next;
            const cp1x = current.x + (next.x - previous.x) * tension / 6;
            const cp1y = current.y + (next.y - previous.y) * tension / 6;
            const cp2x = next.x - (following.x - current.x) * tension / 6;
            const cp2y = next.y - (following.y - current.y) * tension / 6;

            path += ` C ${{cp1x}} ${{cp1y}}, ${{cp2x}} ${{cp2y}}, ${{next.x}} ${{next.y}}`;
        }}

        return path;
    }}

    function drawFrame(svg) {{
        svg.innerHTML = `
            <line class="grid-line" x1="56" y1="26" x2="56" y2="188"></line>
            <line class="grid-line" x1="56" y1="188" x2="642" y2="188"></line>
            <line class="grid-line" x1="56" y1="134" x2="642" y2="134"></line>
            <line class="grid-line" x1="56" y1="80" x2="642" y2="80"></line>
            <text class="axis-label" x="14" y="24">Earnings</text>
            <text class="axis-label" x="606" y="222">Date</text>
        `;
    }}

    function drawCityEarningsChart() {{
        const canvas = document.getElementById("cityEarningsChart");
        const labels = chartData.cityEarningsTrend.labels || [];
        const datasets = chartData.cityEarningsTrend.datasets || [];

        if (!labels.length || !datasets.length) {{
            const empty = document.createElement("div");
            empty.className = "empty-chart";
            empty.textContent = "7-day earnings trend unavailable";
            canvas.replaceWith(empty);
            return;
        }}

        new Chart(canvas, chartConfig);
    }}

    document.addEventListener("DOMContentLoaded", () => {{
        filterCity();
        initSwipe();
        setPage(0);
        drawCityEarningsChart();
    }});

    </script>

    </head>

    <body>
    <div class="app-shell">

        <div class="header">
            {format_date(date)}
        </div>

        <div class="filter">
            <select id="cityFilter" onchange="filterCity()">
                <option value="all">All Cities</option>
                {options}
            </select>
        </div>

        <main class="dashboard-viewport" id="dashboardViewport">
            <div class="dashboard-track" id="dashboardTrack">

                <section class="page kpi-page">
                    <div class="section-panel">
                        <h3 class="section-title">KPI</h3>

                        <div class="kpi-stack">
                            <div class="kpi-card earnings">
                                <span class="label">Earnings</span>
                                <span class="value" id="earnings">{format_inr(kpis['earnings'])}</span>
                                <span class="{change_class(kpis['earnings_change'], 'earnings')}" id="earnings_change">{fmt_change(kpis['earnings_change'], 'earnings')}</span>
                            </div>

                            <div class="kpi-card avg">
                                <span class="label">Avg Earnings</span>
                                <span class="value" id="avg_earnings">{format_inr(kpis['avg_earnings'])}</span>
                                <span class="{change_class(kpis['avg_earnings_change'], 'avg_earnings')}" id="avg_earnings_change">{fmt_change(kpis['avg_earnings_change'], 'avg_earnings')}</span>
                            </div>

                            <div class="kpi-card completion">
                                <span class="label">Completion %</span>
                                <span class="value" id="completion">{int(kpis['completion'])}%</span>
                                <span class="{change_class(kpis['completion_change'], 'completion')}" id="completion_change">{fmt_change(kpis['completion_change'], 'completion')}</span>
                            </div>

                            <div class="kpi-card drivers">
                                <span class="label">Drivers Reported</span>
                                <span class="value" id="drivers">{int(kpis['drivers'])}</span>
                                <span class="{change_class(kpis['drivers_change'], 'drivers')}" id="drivers_change">{fmt_change(kpis['drivers_change'], 'drivers')}</span>
                            </div>

                            <div class="kpi-card orders">
                                <span class="label">Orders</span>
                                <span class="value" id="orders">{int(kpis['orders'])}</span>
                                <span class="{change_class(kpis['orders_change'], 'orders')}" id="orders_change">{fmt_change(kpis['orders_change'], 'orders')}</span>
                            </div>

                            <div class="kpi-card avg">
                                <span class="label">Avg Orders</span>
                                <span class="value" id="avg_orders">{int(kpis['avg_orders'])}</span>
                                <span class="{change_class(kpis['avg_orders_change'], 'avg_orders')}" id="avg_orders_change">{fmt_change(kpis['avg_orders_change'], 'avg_orders')}</span>
                            </div>

                            <div class="kpi-card missed">
                                <span class="label">Missed Orders</span>
                                <span class="value" id="missed">{int(kpis['missed'])}</span>
                                <span class="{change_class(kpis['missed_change'], 'missed')}" id="missed_change">{fmt_change(kpis['missed_change'], 'missed')}</span>
                            </div>
                        </div>
                    </div>
                </section>

                <section class="page insights-page">
                    <div class="section-panel">
                        <h3 class="section-title">Insights</h3>
                    <div class="insights insights-list">
                        {insights_html}
                    </div>
                    </div>
                </section>

                <section class="page chart-page">
                    <div class="section-panel">
                        <h3 class="section-title">Chart</h3>
                        <div class="chart-card">
                            <div class="chart-title">City vs Earnings (Last 7 Days)</div>
                            <div class="chart-subtitle">Last 7 days earnings trend across cities</div>
                            <div class="chart-container">
                                <canvas id="cityEarningsChart" aria-label="City vs Earnings last 7 days line chart"></canvas>
                            </div>
                        </div>
                    </div>
                </section>

            </div>
        </main>

        <div class="mobile-dots">
            <button class="dot-indicator active" onclick="setPage(0)" aria-label="Show KPI"></button>
            <button class="dot-indicator" onclick="setPage(1)" aria-label="Show insights"></button>
            <button class="dot-indicator" onclick="setPage(2)" aria-label="Show chart"></button>
        </div>

        <div class="footer">
            Kapilan A &bull; Data Scientist &bull; Fyn Mobility
        </div>

    </div>
    </body>
    </html>
    """

    return html

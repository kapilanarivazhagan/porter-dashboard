import streamlit as st
import subprocess
import os
from datetime import datetime
import streamlit.components.v1 as components

# -----------------------------
# CONFIG
# -----------------------------
S3_BUCKET = "porter-dashboard-kavi"
BASE_S3_URL = f"https://{S3_BUCKET}.s3.amazonaws.com"

REPORT_FILE = "porter_report.html"
LOCAL_PATH = REPORT_FILE

# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(page_title="Porter Insight Reports", layout="wide")

# -----------------------------
# HEADER
# -----------------------------
st.markdown(
    "<h1 style='text-align: center;'>Porter Insight Reports</h1>",
    unsafe_allow_html=True
)
st.markdown("---")

# -----------------------------
# BUTTON
# -----------------------------
generate = st.button("Generate Report")

# -----------------------------
# MAIN FLOW
# -----------------------------
if generate:

    # -----------------------------
    # RUN SCRIPT
    # -----------------------------
    with st.spinner("Generating report..."):
        result = subprocess.run("python main.py", shell=True)

        if result.returncode != 0:
            st.error("Error running main.py")
            st.stop()

    st.success("Report generated")

    # -----------------------------
    # CHECK FILE
    # -----------------------------
    if not os.path.exists(LOCAL_PATH):
        st.error("HTML report not found")
        st.stop()

    # -----------------------------
    # UPLOAD TO S3
    # -----------------------------
    with st.spinner("Uploading to S3..."):

        subprocess.run(
            f'aws s3 cp "{LOCAL_PATH}" s3://{S3_BUCKET}/{REPORT_FILE}',
            shell=True
        )

        subprocess.run(
            f'aws s3 cp "Ready-for-migrating-to-an-electric-vehicle-fleet.jpg" '
            f's3://{S3_BUCKET}/Ready-for-migrating-to-an-electric-vehicle-fleet.jpg',
            shell=True
        )

    # -----------------------------
    # S3 LINK
    # -----------------------------
    html_url = f"{BASE_S3_URL}/{REPORT_FILE}"

    st.success("Uploaded successfully")

    # -----------------------------
    # PREVIEW
    # -----------------------------
    st.markdown("## Report Preview")

    components.iframe(html_url, height=600, scrolling=True)

    # -----------------------------
    # CAPTION BLOCK
    # -----------------------------
    today_str = datetime.now().strftime("%d %B")

    caption = f"""
Fleet Status - Porter - {today_str}

Primary: Completion at 65-70% range
Impact: Missed notifications impacting conversions

Full Report:
{html_url}
"""

    safe_caption = caption.replace("`", "\\`")

    st.markdown("## Caption")

    components.html(f"""
        <div style="
            position: relative;
            border: 1px solid #ddd;
            border-radius: 10px;
            padding: 15px;
            background: #fafafa;
        ">

            <button onclick="copyText()"
            style="
                position: absolute;
                top: 10px;
                right: 10px;
                background: black;
                color: white;
                border: none;
                padding: 5px 10px;
                border-radius: 6px;
                cursor: pointer;">
                Copy
            </button>

            <div id="toast" style="
                position: absolute;
                top: 10px;
                right: 80px;
                background: green;
                color: white;
                padding: 4px 8px;
                border-radius: 5px;
                display: none;">
                Copied
            </div>

            <pre id="text" style="
                margin-top: 25px;
                white-space: pre-wrap;
                font-size: 14px;
            ">{safe_caption}</pre>
        </div>

        <script>
        function copyText() {{
            let text = document.getElementById("text").innerText;
            navigator.clipboard.writeText(text);

            let toast = document.getElementById("toast");
            toast.style.display = "block";

            setTimeout(() => {{
                toast.style.display = "none";
            }}, 1500);
        }}
        </script>
    """, height=250)

    st.success("All done 🚀")
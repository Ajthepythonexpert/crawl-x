import streamlit as st
import time
import json
import pandas as pd
import io
import os
import re
from urllib.parse import urlparse

from jobs.job_manager import start_job, get_job
from core.scraper import build_keyword_script


# 🔧 Prevent Excel crash on empty sheets
def df_to_excel_bytes(sheets: dict) -> bytes:
    def safe_df(df):
        if isinstance(df, pd.DataFrame) and not df.empty:
            return df
        return pd.DataFrame({"Info": ["No data found for this section."]})

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        for name, df in sheets.items():
            safe_df(df).to_excel(writer, sheet_name=name[:31], index=False)
    return buf.getvalue()


def render():
    if "jobs" not in st.session_state:
        st.session_state["jobs"] = {}

    st.markdown("""
    <div class="tool-header">
        <div class="tool-icon">🔍</div>
        <div>
            <div class="tool-title">Keyword Finder</div>
            <div class="tool-sub">Scan every page for a text match · Background Execution</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # INPUT FORM
    with st.form("kw_form"):
        sitemap_url = st.text_input("Sitemap XML URL")
        keyword = st.text_input("Keyword to search for")
        path_filter = st.text_input("Sub-folder filter (optional)")
        submitted = st.form_submit_button("🚀 Start Crawl")

    # START JOB
    if submitted and "keyword" not in st.session_state["jobs"]:
        if not sitemap_url or not keyword:
            st.error("Please fill in both the Sitemap URL and Keyword.")
            return

        user_id = st.session_state.get("user_id", "admin")

        def builder(output_path):
            return build_keyword_script(sitemap_url, keyword, path_filter, output_path)

        job_id = start_job(user_id, "keyword", {}, builder)
        st.session_state["jobs"]["keyword"] = job_id
        st.rerun()

    # POLLING
    if "keyword" in st.session_state["jobs"]:
        job_id = st.session_state["jobs"]["keyword"]
        job = get_job(job_id)

        if not job:
            st.error("Job not found.")
            return

        status = job[3]
        st.caption(f"Job ID: {job_id}")

        if status in ["queued", "running"]:
            with st.spinner(f"⏳ {status.upper()}..."):
                time.sleep(2)
                st.rerun()

        elif status == "failed":
            st.error(f"❌ Job failed: {job[7]}")
            if st.button("Start New Crawl"):
                st.session_state["jobs"].pop("keyword", None)
                st.rerun()

        elif status == "completed":
            result_path = job[5]

            if not result_path or not os.path.exists(result_path):
                st.error("Result file missing.")
                return

            with open(result_path) as f:
                data = json.load(f)

            # ✅ SAFE DATA EXTRACTION
            results_data = data.get("results", [])
            sitemap_data = data.get("sitemap", [])

            # ✅ ALWAYS CREATE VALID DATAFRAMES
            df_all = pd.DataFrame(results_data) if results_data else pd.DataFrame(columns=["URL", "Status", "Keyword_Found"])
            df_official = pd.DataFrame(sitemap_data, columns=["URL"]) if sitemap_data else pd.DataFrame(columns=["URL"])

            # 🔥 FIXED KEYWORD LOGIC (extra safe)
            if not df_all.empty and "Keyword_Found" in df_all.columns:
                keyword_hits = df_all[df_all["Keyword_Found"] == True]
            else:
                keyword_hits = pd.DataFrame(columns=df_all.columns)

            # Missing in sitemap
            if not df_all.empty and not df_official.empty:
                missing_in_xml = df_all[
                    (df_all["Status"] == 200) &
                    (~df_all["URL"].isin(df_official["URL"]))
                ]
            else:
                missing_in_xml = pd.DataFrame(columns=df_all.columns)

            # Orphans
            if not df_official.empty and not df_all.empty:
                orphans = df_official[~df_official["URL"].isin(df_all["URL"])]
            else:
                orphans = pd.DataFrame(columns=df_official.columns)

            st.success("✅ Crawl complete!")

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Pages Scanned", len(df_all))
            c2.metric("🚩 Keyword Hits", len(keyword_hits))
            c3.metric("Missing from XML", len(missing_in_xml))
            c4.metric("Orphan Pages", len(orphans))

            # ✅ SAFE DISPLAY (NO CRASH)
            st.markdown("### 🚩 Keyword Hits")
            if not keyword_hits.empty:
                st.dataframe(keyword_hits, use_container_width=True)
            else:
                st.info("No keyword matches found.")

            # EXPORT
            sheets = {
                "Keyword Hits": keyword_hits,
                "Missing from Sitemap": missing_in_xml,
                "Orphans": orphans,
                "All Pages": df_all,
                "Sitemap": df_official,
            }

            excel_bytes = df_to_excel_bytes(sheets)

            col1, col2 = st.columns([1, 4])
            with col1:
                st.download_button(
                    "⬇️ Download Report",
                    data=excel_bytes,
                    file_name=f"Keyword_Audit_{urlparse(sitemap_url).netloc}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )

            with col2:
                if st.button("Start New Crawl"):
                    st.session_state["jobs"].pop("keyword", None)
                    st.rerun()


if __name__ == "__main__":
    render()

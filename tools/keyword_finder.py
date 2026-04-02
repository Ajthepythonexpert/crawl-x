import streamlit as st
import time
import json
import pandas as pd
import io
import os
from urllib.parse import urlparse

from jobs.job_manager import start_job, get_job
from core.scraper import build_keyword_script

# 🔧 Prevent Excel crash on empty sheets
def df_to_excel_bytes(sheets: dict) -> bytes:
    def safe_df(df):
        return df if not df.empty else pd.DataFrame({"Info": ["No data found for this section."]})
        
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        for name, df in sheets.items():
            safe_df(df).to_excel(writer, sheet_name=name[:31], index=False)
    return buf.getvalue()

def render():
    # 1. Initialize safe session state for tracking jobs
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

    # 2. USER INPUT FORM
    with st.form("kw_form"):
        sitemap_url = st.text_input("Sitemap XML URL", placeholder="https://example.com/sitemap.xml")
        keyword = st.text_input("Keyword to search for", placeholder="e.g. no product results")
        path_filter = st.text_input("Sub-folder filter (optional)", placeholder="e.g. /mkt-category/")
        submitted = st.form_submit_button("🚀 Start Crawl")

    # 3. START JOB LOGIC 
    # 🔧 IMPROVEMENT 1: Prevent duplicate button clicks from spamming the DB
    if submitted and "keyword" not in st.session_state["jobs"]:
        if not sitemap_url or not keyword:
            st.error("Please fill in both the Sitemap URL and Keyword.")
            return

        user_id = st.session_state.get("user_id", "admin")
        params = {"sitemap_url": sitemap_url, "keyword": keyword, "path_filter": path_filter}

        def builder(output_path):
            return build_keyword_script(sitemap_url, keyword, path_filter, output_path)

        # Submit to the SQLite Job Manager
        job_id = start_job(user_id, "keyword", params, builder)
        st.session_state["jobs"]["keyword"] = job_id
        
        st.rerun()

    # 4. POLLING & RESULTS LOGIC
    if "keyword" in st.session_state["jobs"]:
        job_id = st.session_state["jobs"]["keyword"]
        job = get_job(job_id)

        if not job:
            st.error("Job not found in database.")
            return

        status = job[3]  # DB Column index for 'status'

        # 🔧 IMPROVEMENT 2: Persistent Job ID UI for easy debugging
        st.caption(f"**Job ID:** `{job_id}`")

        # Active Polling
        if status in ["queued", "running"]:
            with st.spinner(f"⏳ Status: {status.upper()}... Please do not close this tab."):
                time.sleep(2)
                st.rerun() 

        # Failure State
        elif status == "failed":
            st.error(f"❌ Job failed: {job[7]}")
            if st.button("Start New Crawl"):
                st.session_state["jobs"].pop("keyword", None)
                st.rerun()

        # Success State
        elif status == "completed":
            result_path = job[5]  

            if not result_path:
                st.error("No result file found in database.")
                return

            # Safe File Check
            if not os.path.exists(result_path):
                st.error("Result file is missing from the disk. It may have been deleted.")
                if st.button("Start New Crawl"):
                    st.session_state["jobs"].pop("keyword", None)
                    st.rerun()
                return

            with open(result_path) as f:
                data = json.load(f)

            # Safe Dictionary Parsing
            results_data = data.get("results", [])
            sitemap_data = data.get("sitemap", [])

            df_all = pd.DataFrame(results_data).drop_duplicates(subset=["URL"]) if results_data else pd.DataFrame(columns=["URL"])
            df_official = pd.DataFrame(sitemap_data, columns=["URL"]) if sitemap_data else pd.DataFrame(columns=["URL"])
            
            # Safe filtering
            if not df_all.empty and "Keyword_Found" in df_all.columns:
                keyword_hits = df_all[df_all["Keyword_Found"] == True]
            else:
                keyword_hits = pd.DataFrame()

            if not df_all.empty and "Status" in df_all.columns:
                missing_in_xml = df_all[(df_all["Status"] == 200) & (~df_all["URL"].isin(df_official["URL"]))]
            else:
                missing_in_xml = pd.DataFrame()

            if not df_official.empty and not df_all.empty:
                orphans = df_official[~df_official["URL"].isin(df_all["URL"])]
            else:
                orphans = pd.DataFrame()

            st.success("✅ Crawl complete!")

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Pages Scanned", len(df_all))
            c2.metric("🚩 Keyword Hits", len(keyword_hits))
            c3.metric("Missing from XML", len(missing_in_xml))
            c4.metric("Orphan Pages", len(orphans))

            if not keyword_hits.empty:
                st.markdown("### 🚩 Keyword Hits")
                st.dataframe(keyword_hits, use_container_width=True)

            sheets = {
                "1. KEYWORD HITS": keyword_hits,
                "2. Missing from Sitemap": missing_in_xml,
                "3. Orphans (XML Only)": orphans,
                "4. All Live Audit": df_all,
                "5. Official Sitemap List": df_official,
            }
            
            excel_bytes = df_to_excel_bytes(sheets)
            
            col1, col2 = st.columns([1, 4])
            with col1:
                st.download_button(
                    "⬇️ Download Full Excel Report",
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
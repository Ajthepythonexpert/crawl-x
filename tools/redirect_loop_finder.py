import streamlit as st
import time
import json
import os
import pandas as pd
from urllib.parse import urlparse

from jobs.job_manager import start_job, get_job
from core.scraper import build_redirect_script

def render():
    if "jobs" not in st.session_state:
        st.session_state["jobs"] = {}

    st.markdown("""
    <div class="tool-header">
        <div class="tool-icon">🔄</div>
        <div>
            <div class="tool-title">Redirect Loop Finder</div>
            <div class="tool-sub">Trace chains · Detect infinite loops · Find 404s</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 1. USER INPUT FORM
    with st.form("rd_form"):
        sitemap_url = st.text_input("Sitemap XML URL", placeholder="https://example.com/sitemap.xml")
        path_filter = st.text_input("Sub-folder filter (optional)", placeholder="e.g. /products/")
        submitted = st.form_submit_button("🚀 Start Redirect Audit")

    # 2. START JOB LOGIC 
    if submitted and "redirect" not in st.session_state["jobs"]:
        if not sitemap_url:
            st.error("Please provide a Sitemap URL.")
            return

        user_id = st.session_state.get("user_id", "admin")
        params = {"sitemap_url": sitemap_url, "path_filter": path_filter}
        
        def builder(output_path):
            return build_redirect_script(sitemap_url, path_filter, output_path)

        job_id = start_job(user_id, "redirect", params, builder)
        st.session_state["jobs"]["redirect"] = job_id
        st.rerun()

    # 3. POLLING & RESULTS LOGIC
    if "redirect" in st.session_state["jobs"]:
        job_id = st.session_state["jobs"]["redirect"]
        job = get_job(job_id)
        
        if job:
            status = job[3]
            result_path = job[5]
            st.caption(f"**Job ID:** `{job_id}`")

            if status in ["queued", "running"]:
                with st.spinner(f"⏳ Tracing Redirects ({status.upper()})..."):
                    time.sleep(2)
                    st.rerun()
            
            elif status == "failed":
                st.error(f"❌ Job failed: {job[7]}")
                if st.button("Start New Audit"):
                    st.session_state["jobs"].pop("redirect", None)
                    st.rerun()

            elif status == "completed":
                if not result_path or not os.path.exists(result_path):
                    st.error("Result file missing from server.")
                    return

                try:
                    with open(result_path, "r") as f:
                        data = json.load(f)
                except:
                    st.error("Invalid or corrupted result file.")
                    return
                
                # 🔧 IMPROVEMENT 1 & 2: Safe Data Processing
                df = pd.DataFrame(data.get("results", []))
                
                if df.empty:
                    st.warning("Crawl finished, but no data was returned.")
                elif "Status" not in df.columns:
                    st.error("Invalid result format: Missing 'Status' column.")
                else:
                    # Safe Metrics Filtering
                    status_col = df["Status"]
                    redirects = df[status_col.isin([301, 302, 307, 308, "LOOP"])]
                    loops = df[status_col == "LOOP"]
                    dead = df[status_col == 404]

                    st.success("✅ Trace Complete!")
                    
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Total URLs", len(df))
                    m2.metric("Redirects", len(redirects))
                    m3.metric("Loops", len(loops))
                    m4.metric("Dead (404)", len(dead))

                    st.markdown("### 📋 Audit Results")
                    st.dataframe(df, use_container_width=True)

                    # 🔧 IMPROVEMENT 3: Add Download Button
                    st.divider()
                    col_dl, col_new = st.columns([1, 4])
                    with col_dl:
                        st.download_button(
                            "⬇️ Download JSON",
                            data=json.dumps(data, indent=2),
                            file_name=f"redirect_audit_{job_id}.json",
                            mime="application/json"
                        )
                    with col_new:
                        if st.button("Start New Audit"):
                            st.session_state["jobs"].pop("redirect", None)
                            st.rerun()

if __name__ == "__main__":
    render()
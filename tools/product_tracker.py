# -------------------------------------------------------------------------
# START OF CLOUD PATH ENVIRONMENT FIX
# -------------------------------------------------------------------------
import sys
import os

# Append the parent directory to sys.path so Streamlit Cloud can resolve 'core' and 'analytics'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# -------------------------------------------------------------------------

import streamlit as st
import pandas as pd
from analytics.db import get_conn
from core.job_manager import start_job

# 📦 METADATA DECLARATION FOR THE DASHBOARD REGISTRY LOOP
INFO = {
    "title": "Product Delta Tracker",
    "icon": "📦",
    "description": "Monitor vanished or newly introduced product variants week-over-week across markets."
}

def get_tracked_dates(country):
    """Fetches all unique historical snapshot dates available for a specific market."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT DISTINCT snapshot_date FROM product_snapshots WHERE country=? ORDER BY snapshot_date DESC", (country,))
        dates = [row[0] for row in cur.fetchall()]
    except Exception:
        dates = []
    finally:
        conn.close()
    return dates

def render():
    st.title("📦 Product Delta Tracker")
    st.caption("Weekly defensive visibility system to detect unintended drop-offs from your regional storefront inventory.")

    # --- CONFIGURATION BOX ---
    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col1:
            sitemap_url = st.text_input("Sitemap URL Seed", value="https://www.bosch-home.com/za/sitemap.xml")
            # Using session state key tracking to handle dynamic lookups gracefully
            country = st.text_input("Country Identifier (e.g., ZA, SG, UA)", value="ZA", key="prod_country_input").upper().strip()
        with col2:
            brand = st.selectbox("Target Brand", ["BOSCH", "SIEMENS", "NEFF"])

    # --- TRIGGER NEW CRAWL JOB ---
    if st.button("🚀 INITIATE CURRENT WEEKLY INVENTORY SNAPSHOT", use_container_width=True):
        if not sitemap_url or not country:
            st.error("Please provide both a valid Sitemap URL and Country Identifier.")
        else:
            params = {
                "sitemap_url": sitemap_url, 
                "country": country, 
                "brand": brand
            }
            job_id = start_job(st.session_state.get("user_id", "Admin"), "product_tracker", params)
            st.success(f"Snapshot tracking run assigned to execution thread! Task ID: {job_id}")

    st.divider()
    
    # --- COMPARATIVE INVENTORY VARIANCE ENGINE ---
    st.subheader("📊 Comparative Inventory Variance Engine")
    st.markdown("Select two distinct snapshot dates to inspect items that have been dropped or newly introduced.")
    
    dates = get_tracked_dates(country)

    if len(dates) >= 2:
        c1, c2 = st.columns(2)
        with c1:
            curr_week = st.selectbox("Baseline Run Date (Newer)", dates, index=0)
        with c2:
            prev_week = st.selectbox("Comparison Target Run Date (Older)", dates, index=1)

        if st.button("⚖️ CALCULATE DELTA HISTORICAL VARIANCE", use_container_width=True):
            conn = get_conn()
            df_new = pd.read_sql(f"SELECT url, model_number FROM product_snapshots WHERE snapshot_date='{curr_week}' AND country='{country}'", conn)
            df_old = pd.read_sql(f"SELECT url, model_number FROM product_snapshots WHERE snapshot_date='{prev_week}' AND country='{country}'", conn)
            conn.close()

            set_new = set(df_new['url'].tolist())
            set_old = set(df_old['url'].tolist())

            # Math sets difference rules for finding deltas
            dropped_urls = set_old - set_new
            added_urls = set_new - set_old

            df_dropped = df_old[df_old['url'].isin(dropped_urls)].drop_duplicates()
            df_added = df_new[df_new['url'].isin(added_urls)].drop_duplicates()

            t1, t2 = st.tabs([f"🚨 Vanished Models ({len(df_dropped)})", f"🟢 New Arrivals ({len(df_added)})"])
            
            with t1:
                if not df_dropped.empty:
                    st.warning(f"Alert! {len(df_dropped)} products disappeared from the sitemap this week.")
                    st.dataframe(df_dropped, use_container_width=True)
                    
                    # Generation of instant excel file trace sheet download
                    report_title = f"VANISHED_PRODUCTS_{country}_{curr_week}.xlsx"
                    df_dropped.to_excel(report_title, index=False)
                    with open(report_title, "rb") as file_bytes:
                        st.download_button("📥 Download Missing Models Audit Sheet (Excel)", file_bytes, file_name=report_title, mime="application/vnd.ms-excel")
                else:
                    st.success("Clean check! Zero discrepancies or inventory drops identified compared to the selection target week.")

            with t2:
                if not df_added.empty:
                    st.info(f"Detected {len(df_added)} newly registered product configurations.")
                    st.dataframe(df_added, use_container_width=True)
                else:
                    st.write("No newly registered listings located in this temporal range match.")
    else:
        st.info(f"Awaiting historical data for country code '{country}'. Run at least two snapshot tasks across different dates for this country to begin historical analysis comparisons.")

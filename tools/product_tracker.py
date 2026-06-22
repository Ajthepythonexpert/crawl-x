import streamlit as st
import pandas as pd
import json
import time
from datetime import datetime
import advertools as adv
import sqlite3

# 📦 METADATA DECLARATION FOR THE DASHBOARD REGISTRY LOOP
INFO = {
    "title": "Product Delta Tracker",
    "icon": "📦",
    "description": "Monitor vanished or newly introduced product variants week-over-week across markets."
}

def run_snapshot_crawler(sitemap_url, country, brand):
    """Executes the tracking scan directly inline matching your core platform style."""
    today = datetime.now().strftime("%Y-%m-%d")
    results = []
    
    try:
        df = adv.sitemap_to_df(sitemap_url)
        if 'loc' in df.columns:
            all_urls = df['loc'].dropna().unique().tolist()
            
            # Isolate targeted structural product storefront paths
            product_urls = [u for u in all_urls if "/product/" in u.lower() or "/mkt-product/" in u.lower()]
            
            # Direct database fallback link bypassing global file dependencies
            conn = sqlite3.connect("database.db")
            conn.execute("PRAGMA journal_mode=WAL;")
            cur = conn.cursor()
            
            for url in product_urls:
                model_num = url.rstrip('/').split('/')[-1]
                
                cur.execute("""
                    INSERT INTO product_snapshots (url, model_number, brand, country, status_code, snapshot_date, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (url, model_num, brand, country, 200, today, time.time()))
                
                results.append({"url": url, "model": model_num})
                
            conn.commit()
            conn.close()
            return True, len(results)
    except Exception as e:
        return False, str(e)
    return True, 0

def render():
    st.title("📦 Product Delta Tracker")
    st.caption("Weekly defensive visibility system to detect unintended drop-offs from your regional storefront inventory.")

    # --- CONFIGURATION BOX ---
    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col1:
            sitemap_url = st.text_input("Sitemap URL Seed", value="https://www.bosch-home.com/za/sitemap.xml")
            country = st.text_input("Country Identifier (e.g., ZA, SG, UA)", value="ZA").upper().strip()
        with col2:
            brand = st.selectbox("Target Brand", ["BOSCH", "SIEMENS", "NEFF"])

    # --- TRIGGER CRAWL ---
    if st.button("🚀 INITIATE CURRENT WEEKLY INVENTORY SNAPSHOT", use_container_width=True):
        if not sitemap_url or not country:
            st.error("Please provide both a valid Sitemap URL and Country Identifier.")
        else:
            progress_bar = st.progress(0, text="Initializing inventory crawler...")
            
            progress_bar.progress(30, text="Fetching and parsing sitemap dataframe...")
            success, count_or_error = run_snapshot_crawler(sitemap_url, country, brand)
            
            if success:
                progress_bar.progress(100, text="Done!")
                st.success(f"✅ Snapshot complete! Successfully logged {count_or_error} products for {brand} ({country}).")
                time.sleep(1)
                st.rerun()
            else:
                st.error(f"Snapshot run failed: {count_or_error}")

    st.divider()
    
    # --- COMPARATIVE INVENTORY VARIANCE ENGINE ---
    st.subheader("📊 Comparative Inventory Variance Engine")
    st.markdown("Select two distinct snapshot dates to inspect items that have been dropped or newly introduced.")
    
    # Inline localized database fetch loop
    try:
        conn = sqlite3.connect("database.db")
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT snapshot_date FROM product_snapshots WHERE country=? ORDER BY snapshot_date DESC", (country,))
        dates = [row[0] for row in cur.fetchall()]
        conn.close()
    except Exception:
        dates = []

    if len(dates) >= 2:
        c1, c2 = st.columns(2)
        with c1:
            curr_week = st.selectbox("Baseline Run Date (Newer)", dates, index=0)
        with c2:
            prev_week = st.selectbox("Comparison Target Run Date (Older)", dates, index=1)

        if st.button("⚖️ CALCULATE DELTA HISTORICAL VARIANCE", use_container_width=True):
            conn = sqlite3.connect("database.db")
            df_new = pd.read_sql(f"SELECT url, model_number FROM product_snapshots WHERE snapshot_date='{curr_week}' AND country='{country}'", conn)
            df_old = pd.read_sql(f"SELECT url, model_number FROM product_snapshots WHERE snapshot_date='{prev_week}' AND country='{country}'", conn)
            conn.close()

            set_new = set(df_new['url'].tolist())
            set_old = set(df_old['url'].tolist())

            dropped_urls = set_old - set_new
            added_urls = set_new - set_old

            df_dropped = df_old[df_old['url'].isin(dropped_urls)].drop_duplicates()
            df_added = df_new[df_new['url'].isin(added_urls)].drop_duplicates()

            t1, t2 = st.tabs([f"🚨 Vanished Models ({len(df_dropped)})", f"🟢 New Arrivals ({len(df_added)})"])
            
            with t1:
                if not df_dropped.empty:
                    st.warning(f"Alert! {len(df_dropped)} products disappeared from the sitemap this week.")
                    st.dataframe(df_dropped, use_container_width=True)
                    
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

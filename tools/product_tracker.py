import streamlit as st
import pandas as pd
import sqlite3
import time
import re
from datetime import datetime
from urllib.parse import urlparse
import requests

# 📦 METADATA DECLARATION FOR THE DASHBOARD REGISTRY LOOP
INFO = {
    "title": "Product Delta Tracker",
    "icon": "📦",
    "description": "Monitor vanished or newly introduced product variants week-over-week by executing a live full-site link crawl."
}

def deep_crawl_site(start_url, country, brand, progress_bar, status_text):
    """
    Executes an inline full-site discovery crawl. 
    Traverses internal anchor links to mimic your stockfinderv2.py spider logic.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    parsed_start = urlparse(start_url)
    allowed_domain = parsed_start.netloc
    
    # Initialize crawl balance maps
    urls_to_crawl = [start_url]
    visited_urls = set()
    product_urls = set()
    
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    })
    
    # Cap limit to keep the browser execution thread safe on Streamlit Cloud (Adjustable)
    MAX_PAGES_TO_SCAN = 1200 
    
    while urls_to_crawl and len(visited_urls) < MAX_PAGES_TO_SCAN:
        current_url = urls_to_crawl.pop(0)
        
        if current_url in visited_urls:
            continue
            
        visited_urls.add(current_url)
        status_text.text(f"🔍 Visited: {len(visited_urls)} pages | Discovered Storefront Products: {len(product_urls)}")
        
        # Update progress bar occasionally based on scanned segments
        progress_val = min(int((len(visited_urls) / 200) * 100), 95)
        progress_bar.progress(progress_val)
        
        try:
            r = session.get(current_url, timeout=15, allow_redirects=True)
            if r.status_code != 200:
                continue
                
            # 1. Inspect URL for structural product identifier variants
            if "/product/" in current_url.lower() or "/mkt-product/" in current_url.lower():
                product_urls.add(current_url)
                
            # 2. Extract every internal anchor href attribute from the live html markup
            all_links = re.findall(r'href=["\'](https?://[^"\']+|/[^"\']*)["\']', r.text)
            
            for link in all_links:
                # Resolve relative pathways cleanly
                if link.startswith("/"):
                    link = f"{parsed_start.scheme}://{allowed_domain}{link}"
                
                parsed_link = urlparse(link)
                # Keep crawler strictly isolated to your targeted regional brand workspace
                if parsed_link.netloc == allowed_domain and link not in visited_urls and link not in urls_to_crawl:
                    # Filter string pathways to prioritize clean catalog content indexing
                    if not any(ext in parsed_link.path.lower() for ext in ['.pdf', '.jpg', '.png', '.zip', '.css', '.js']):
                        urls_to_crawl.append(link)
                        
        except Exception:
            continue
            
    # --- SAVE DISCOVERED STOCK MATRIX ---
    results = []
    if product_urls:
        conn = sqlite3.connect("database.db")
        conn.execute("PRAGMA journal_mode=WAL;")
        cur = conn.cursor()
        
        for url in product_urls:
            # Clean split to pull model variants out of tail ends
            model_num = url.rstrip('/').split('/')[-1].split('?')[0]
            
            cur.execute("""
                INSERT INTO product_snapshots (url, model_number, brand, country, status_code, snapshot_date, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (url, model_num, brand, country, 200, today, time.time()))
            
            results.append({"URL": url, "Model Number": model_num})
            
        conn.commit()
        conn.close()
        
    return results

def render():
    st.title("📦 Product Live Crawl Tracker")
    st.caption("Deep crawler that navigates from the home entry point across all nested layers to discover newly published variants.")

    if "last_crawl_results" not in st.session_state:
        st.session_state.last_crawl_results = None

    # --- CONFIGURATION BOX ---
    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col1:
            start_url = st.text_input("Homepage Entry Point URL", value="https://www.bosch-home.com/za/")
            country = st.text_input("Country Identifier (e.g., ZA, SG, UA)", value="ZA").upper().strip()
        with col2:
            brand = st.selectbox("Target Brand", ["BOSCH", "SIEMENS", "NEFF"])

    # --- TRIGGER RUN ---
    if st.button("🚀 INITIATE DEEP FULL-SITE DISCOVERY CRAWL", use_container_width=True):
        if not start_url or not country:
            st.error("Please provide both a valid Home Start URL and Country Identifier.")
        else:
            progress_bar = st.progress(0, text="Deploying custom discovery bots...")
            status_text = st.empty()
            
            data_payload = deep_crawl_site(start_url, country, brand, progress_bar, status_text)
            
            progress_bar.progress(100)
            status_text.empty()
            
            st.session_state.last_crawl_results = data_payload
            st.success(f"✅ Deep discovery loop finalized! Successfully scraped and cataloged {len(data_payload)} live storefront items.")

    # --- IMMEDIATE EXCEL DOWNLOAD SHEET BAR ---
    if st.session_state.last_crawl_results:
        with st.container(border=True):
            st.markdown("### 📥 Discovered Active Inventory Results")
            df_current = pd.DataFrame(st.session_state.last_crawl_results)
            st.dataframe(df_current, use_container_width=True)
            
            file_name = f"DEEP_CRAWL_INVENTORY_{brand}_{country}_{datetime.now().strftime('%Y-%m-%d')}.xlsx"
            df_current.to_excel(file_name, index=False)
            with open(file_name, "rb") as f:
                st.download_button(
                    label="📥 Download Discovered Models List (Excel)",
                    data=f,
                    file_name=file_name,
                    mime="application/vnd.ms-excel",
                    use_container_width=True
                )

    st.divider()
    
    # --- COMPARATIVE INVENTORY VARIANCE ENGINE ---
    st.subheader("📊 Comparative Inventory Variance Engine")
    st.markdown("Select two distinct snapshot dates to inspect items that have been dropped or newly introduced.")
    
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
                    st.warning(f"Alert! {len(df_dropped)} products disappeared from the storefront map.")
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

if __name__ == "__main__":
    render()

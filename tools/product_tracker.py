import streamlit as st
import pandas as pd
import sqlite3
import time
import re
import asyncio
import aiohttp
from datetime import datetime
from urllib.parse import urlparse, urljoin
import advertools as adv

# 📦 METADATA DECLARATION FOR THE DASHBOARD REGISTRY LOOP
INFO = {
    "title": "Product Delta Tracker",
    "icon": "📦",
    "description": "High-performance asynchronous live catalog spider to track inventory deltas."
}

async def fetch_page(session, url):
    """Safely handles non-blocking async network resource grabs with cache-busting headers."""
    try:
        # Force the target server to return fresh content instead of cached edge data
        headers = {"Cache-Control": "no-cache", "Pragma": "no-cache"}
        async with session.get(url, timeout=12, allow_redirects=True, headers=headers) as response:
            if response.status == 200:
                text = await response.text()
                return url, text
    except Exception:
        pass
    return url, None

async def async_site_crawler(start_url, base_lang, product_urls, progress_container, status_text):
    """Executes a high-speed asynchronous link discovery crawl inside the primary thread loop."""
    parsed_start = urlparse(start_url)
    allowed_domain = parsed_start.netloc
    
    # Initialize lookup queues cleanly
    to_visit = set([f"{parsed_start.scheme}://{allowed_domain}/{base_lang}/"])
    to_visit.update(product_urls)
    
    visited = set()
    discovered_products = set()
    
    CONCURRENT_LIMIT = 16
    sem = asyncio.Semaphore(CONCURRENT_LIMIT)
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    }
    
    MAX_TOTAL_PAGES = 1500
    
    async with aiohttp.ClientSession(headers=headers) as session:
        while to_visit and len(visited) < MAX_TOTAL_PAGES:
            # Batch out tasks up to our concurrency limit
            current_batch = [to_visit.pop() for _ in range(min(len(to_visit), CONCURRENT_LIMIT))]
            
            async def worker(url):
                async with sem:
                    if url in visited:
                        return None
                    visited.add(url)
                    return await fetch_page(session, url)
            
            tasks = [worker(url) for url in current_batch]
            results = await asyncio.gather(*tasks)
            
            for res in results:
                if not res:
                    continue
                url, html_content = res
                if not html_content:
                    continue
                
                if "/product/" in url.lower() or "/mkt-product/" in url.lower():
                    discovered_products.add(url)
                
                # Dynamic page-from-page link extraction
                links = re.findall(r'href=["\'](https?://[^"\']+|/[^"\']*)["\']', html_content)
                for link in links:
                    if link.startswith("/"):
                        link = urljoin(url, link)
                    
                    p_link = urlparse(link)
                    if p_link.netloc == allowed_domain and link not in visited and link not in to_visit:
                        if f"/{base_lang}/" in link.lower() and not any(ext in p_link.path.lower() for ext in ['.pdf', '.jpg', '.png', '.css', '.js', '.zip']):
                            to_visit.add(link)
            
            # Real-time UI diagnostics reporting panel
            status_text.markdown(f"⏳ **Live Network Sync Running...** | Pages Scanned: `{len(visited)}` | Discovered Storefront Items: `{len(discovered_products)}`")
            progress_container.progress(min(int((len(visited) / 500) * 100), 100))
            
    return list(discovered_products)

def render():
    st.title("📦 Product Delta Tracker (Async Engine)")
    st.caption("High-performance real-time catalog link crawler to discover updated variants without outdated sitemaps.")

    # Persistent session state keys to store raw results data safely across reloads
    if "current_run_data" not in st.session_state:
        st.session_state.current_run_data = None
    if "run_summary_text" not in st.session_state:
        st.session_state.run_summary_text = ""

    # --- CONFIGURATION BOX ---
    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col1:
            sitemap_url = st.text_input("Sitemap XML URL Seed", value="https://www.bosch-home.com/za/sitemap.xml")
            country = st.text_input("Country Identifier (e.g., ZA, SG, UA)", value="ZA").upper().strip()
        with col2:
            brand = st.selectbox("Target Brand", ["BOSCH", "SIEMENS", "NEFF"])

    # --- TRIGGER CRAWL ---
    if st.button("🚀 INITIATE CURRENT WEEKLY INVENTORY SNAPSHOT", use_container_width=True):
        if not sitemap_url or not country:
            st.error("Please fill in both the Sitemap URL Seed and Country Identifier.")
        else:
            # Clear previous run views on new button trigger click
            st.session_state.current_run_data = None
            st.session_state.run_summary_text = ""
            
            progress_bar = st.progress(0, text="Initializing crawler context...")
            status_text = st.empty()
            
            status_text.info("Step 1: Reading configuration sitemap catalog arrays...")
            try:
                # Append a live timestamp string to bypass sitemap file CDN caches completely
                cache_buster_sitemap = f"{sitemap_url}?t={int(time.time())}"
                sm_df = adv.sitemap_to_df(cache_buster_sitemap)
                all_urls = sm_df['loc'].dropna().unique().tolist()
                product_urls = [u for u in all_urls if "/product/" in u or "/mkt-product/" in u]
            except Exception:
                product_urls = []
                
            base_lang = "vi" if "/vi/" in sitemap_url else "en"
            parsed_root = urlparse(sitemap_url)
            start_url = f"{parsed_root.scheme}://{parsed_root.netloc}/{base_lang}/"
            
            status_text.info("Step 2: Spawning deep recursive web link validation loop...")
            
            # Explicit cleanly isolated event loop instance initialization
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            product_links = loop.run_until_complete(
                async_site_crawler(start_url, base_lang, product_urls, progress_bar, status_text)
            )
            loop.close()
            
            # Step 3: Parse and save elements to SQLite layers
            today = datetime.now().strftime("%Y-%m-%d")
            compiled_payload = []
            
            if product_links:
                conn = sqlite3.connect("database.db")
                conn.execute("PRAGMA journal_mode=WAL;")
                cur = conn.cursor()
                for url in product_links:
                    model_num = url.rstrip('/').split('/')[-1].split('?')[0]
                    cur.execute("""
                        INSERT INTO product_snapshots (url, model_number, brand, country, status_code, snapshot_date, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (url, model_num, brand, country, 200, today, time.time()))
                    compiled_payload.append({"Verified URL": url, "Model ID": model_num, "Crawl Date": today})
                conn.commit()
                conn.close()
                
                # Save data objects to session states so they stay visible
                st.session_state.current_run_data = compiled_payload
                st.session_state.run_summary_text = f"✅ Success! Deep live-crawl discovered and logged {len(product_links)} products."
                progress_bar.progress(100)
                status_text.empty()
            else:
                st.warning("Scan completed but no active catalog pathways matched. Target server may have blocked the sync.")

    # --- RENDER IMMEDATE RUN RECOVERY FILE DOWNLOAD PANEL ---
    if st.session_state.current_run_data:
        st.success(st.session_state.run_summary_text)
        with st.container(border=True):
            st.markdown("### 📥 Active Extraction Output Sheets")
            df_active_run = pd.DataFrame(st.session_state.current_run_data)
            st.dataframe(df_active_run, use_container_width=True)
            
            xlsx_filename = f"LIVE_CRAWL_EXTRACTED_{brand}_{country}_{datetime.now().strftime('%Y-%m-%d')}.xlsx"
            df_active_run.to_excel(xlsx_filename, index=False)
            with open(xlsx_filename, "rb") as f:
                st.download_button(
                    label="⬇️ Download Verified Models Audit Spreadsheet (Excel)",
                    data=f,
                    file_name=xlsx_filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
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
                    st.warning(f"Alert! {len(df_dropped)} products disappeared from the storefront maps.")
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

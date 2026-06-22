import streamlit as st
import pandas as pd
import sqlite3
import time
import re
import io
import json
import html
import asyncio
import aiohttp
from datetime import datetime
from urllib.parse import urlparse, urljoin
import advertools as adv

# 📦 METADATA DECLARATION FOR THE DASHBOARD REGISTRY LOOP
INFO = {
    "title": "Product Delta Tracker",
    "icon": "📦",
    "description": "High-performance recursive live crawler parsing advanced product schemas and inventory data levels."
}

# -------------------------------------------------------------------------
# 🛠️ HELPER: EXCEL MULTI-SHEET GENERATOR (Matches your Scrapy file splits)
# -------------------------------------------------------------------------
def build_split_excel(master_list, domain, lang):
    if not master_list:
        return None
        
    df_master = pd.DataFrame(master_list).sort_values(by="Found In")

    # Table splits identical to your stockfinderv2.py closed() method
    df_shop_sheet = df_master[(df_master['URL'].str.contains('/product/')) | (df_master['Active Price'] != 'N/A')]
    df_shop_sheet = df_shop_sheet[['VIB', 'Site Language', 'Found In', 'URL', 'HTTP Status', 'Active Price', 'Promotional Price', 'Actual/Original Price', 'Tax Configuration', 'Stock Status', 'Availability Text Copy']]

    df_mkt_sheet = df_master[(df_master['URL'].str.contains('/mkt-product/')) | (df_master['Buy From Retailer'] == 'Yes')]
    df_mkt_sheet = df_mkt_sheet[['VIB', 'Site Language', 'Found In', 'URL', 'HTTP Status', 'Buy From Retailer', 'Retailer Names', 'Find Local Dealer']]

    df_orphans_errors = df_master[(df_master['Found In'] == 'Sitemap Only') | (~df_master['HTTP Status'].isin([200, 'N/A']))]

    glossary_data = [
        ["TERM / SHEET NAME", "OPERATIONAL BUSINESS DEFINITION & AUDIT RULE"],
        ["Glossary", "This initial tab outlining reporting metadata metrics and documentation definitions."],
        ["Master Status List", "Complete unique product inventory trace combining both the XML sitemap links and live crawl paths."],
        ["Shop Sheet Details", "Isolated transactional database tracker mapping pricing layers, promo items, and cart stock levels."],
        ["Marketing Sheet Details", "Isolated authorized distributor database mapping third-party e-commerce partners and dealer maps."],
        ["Orphans & Error Logs", "Discrepancy tracker: Houses sitemap links missing live on site, or URLs returning broken server errors."]
    ]
    df_glossary = pd.DataFrame(glossary_data[1:], columns=glossary_data[0])

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_glossary.to_excel(writer, sheet_name='Glossary', index=False)
        df_master.to_excel(writer, sheet_name='Master Status List', index=False)
        df_shop_sheet.to_excel(writer, sheet_name='Shop Sheet Details', index=False)
        df_mkt_sheet.to_excel(writer, sheet_name='Marketing Sheet Details', index=False)
        df_orphans_errors.to_excel(writer, sheet_name='Orphans & Error Logs', index=False)
    
    return output.getvalue()

# -------------------------------------------------------------------------
# 🕷️ PARSER ENGINE: NATIVE TRANSLATION OF YOUR PATHS A, B, AND C
# -------------------------------------------------------------------------
def parse_html_inventory(url, html_text, status_code, lang):
    vib = url.rstrip('/').split('/')[-1].split('?')[0]
    
    # Standard Baseline Balances
    active_price = "N/A"
    promo_price = ""
    actual_price = "N/A"
    stock_status = "N/A"
    avail_text_copy = "N/A"
    data_captured = False

    # Regex alternatives replacing Scrapy's scrapy.xpath selectors
    # --- LOGIC TRIGGER PATH A: SERVER DATA ENGINE (AU, NZ) ---
    body_match = re.search(r'data-page-dimensions=["\']([^"\']+)["\']', html_text)
    if body_match and not data_captured:
        try:
            clean_json = html.unescape(body_match.group(1))
            page_data = json.loads(clean_json)
            products_array = page_data.get('products', [])
            if products_array:
                product = products_array[0]
                p_price = product.get('product_price', '')
                p_avail = product.get('product_availability', '')
                if p_price:
                    active_price = f"${p_price}" if not str(p_price).startswith('$') else p_price
                    actual_price = active_price
                if p_avail:
                    avail_text_copy = p_avail
                    stock_status = "In Stock" if "In Stock" in p_avail or "Buyable" in p_avail else "Out of Stock"
                    data_captured = True
                p_promo = product.get('product_promotion_status', '')
                if p_promo and "Not on promotion" not in p_promo:
                    promo_price = active_price
        except Exception:
            pass

    # --- BRAND NEW LOGIC TRIGGER PATH B: SEO SCHEMA JSON-LD PARSER ---
    if not data_captured:
        schema_scripts = re.findall(r'<script\s+type=["\']application/ld\+json["\']>(.*?)</script>', html_text, re.DOTALL)
        for script_text in schema_scripts:
            try:
                schema_data = json.loads(script_text.strip())
                if isinstance(schema_data, list):
                    schema_data = schema_data[0] if schema_data else {}
                if schema_data.get('@type') == 'Product' or 'offers' in schema_data:
                    offers = schema_data.get('offers', {})
                    s_price = offers.get('price') if isinstance(offers, dict) else schema_data.get('price')
                    s_avail = offers.get('availability') if isinstance(offers, dict) else schema_data.get('availability')
                    if s_price:
                        active_price = f"${s_price}"
                        if actual_price == "N/A":
                            actual_price = active_price
                    if s_avail:
                        avail_text_copy = s_avail.split('/')[-1]
                        stock_status = "In Stock" if "InStock" in s_avail else "Out of Stock"
                        data_captured = True
                        break
            except Exception:
                pass

    # --- LOGIC TRIGGER PATH C: STANDARD STATIC SCRAPER FALLBACK (ZA, IN, DE) ---
    if not data_captured:
        # Regex mocks for standard data-testids
        main_price_m = re.search(r'data-testid=["\']price-main-price["\'][^>]*>(.*?)<', html_text)
        reduced_price_m = re.search(r'data-testid=["\']price-reduced-price["\'].*?width:\s*max-content[^>]*>(.*?)<', html_text, re.DOTALL)
        strikethrough_m = re.search(r'data-testid=["\']price-strikethrough-price["\'][^>]*>(.*?)<', html_text)
        rrp_mrp_m = re.search(r'data-testid=["\']rrp-price-component["\'].*?<span[^>]*>(.*?)<', html_text, re.DOTALL)
        
        if reduced_price_m:
            active_price = reduced_price_m.group(1).strip()
            promo_price = reduced_price_m.group(1).strip()
            actual_price = strikethrough_m.group(1).strip() if strikethrough_m else (main_price_m.group(1).strip() if main_price_m else "N/A")
        else:
            active_price = main_price_m.group(1).strip() if main_price_m else "N/A"
            promo_price = ""
            actual_price = rrp_mrp_m.group(1).strip() if rrp_mrp_m else (main_price_m.group(1).strip() if main_price_m else "N/A")

        add_to_cart_btn = 'data-testid="add-to-cart"' in html_text
        disabled_cart_btn = re.search(r'data-testid=["\']add-to-cart["\'][^>]*disabled', html_text) is not None
        avail_text_m = re.search(r'data-testid=["\']availability-text-with-link-text["\'][^>]*>(.*?)<', html_text)
        avail_text_copy = avail_text_m.group(1).strip() if avail_text_m else "N/A"
        
        if add_to_cart_btn:
            stock_status = "Out of Stock" if disabled_cart_btn else "In Stock"

    # Universal properties extraction (Retailer Grids & Dealer maps)
    tax_config_m = re.search(r'data-testid=["\']product-price-info["\'][^>]*>(.*?)<', html_text)
    tax_config = tax_config_m.group(1).strip() if tax_config_m else "N/A"
    buy_retail_flag = "Yes" if 'data-testid="buy-area-retailer-grid"' in html_text else "No"
    
    retailer_names_list = re.findall(r'data-testid=["\']retailer-product-availability["\'].*?<span[^>]*>(.*?)<', html_text, re.DOTALL)
    retailer_names = ", ".join([r.strip() for r in retailer_names_list if r.strip()]) if retailer_names_list else "N/A"

    has_dealer_list = 'data-testid="buy-area-dealer-locator-benefits-info-list"' in html_text
    has_buy_online = 'data-testid="buy-online-button"' in html_text
    local_dealer = "Available" if (has_dealer_list or has_buy_online) else "Not Available"

    return {
        'VIB': vib,
        'Site Language': lang,
        'URL': url,
        'Status': status_code,
        'Active Price': active_price,
        'Promotional Price': promo_price,
        'Actual/Original Price': actual_price,
        'Tax Configuration': tax_config,
        'Buy From Retailer': buy_retail_flag,
        'Stock Status': stock_status,
        'Availability Text Copy': avail_text_copy,
        'Retailer Names': retailer_names,
        'Find Local Dealer': local_dealer
    }

# -------------------------------------------------------------------------
# ⚙️ RECURSIVE DEEP LINK CRAWLER ENGINE
# -------------------------------------------------------------------------
async def fetch_page(session, url):
    try:
        # Cache-busting headers to bypass CDN layer proxies
        headers = {"Cache-Control": "no-cache", "Pragma": "no-cache"}
        async with session.get(url, timeout=12, allow_redirects=True, headers=headers) as response:
            if response.status == 200:
                text = await response.text()
                return url, text, response.status
            return url, None, response.status
    except Exception:
        pass
    return url, None, 0

async def recursive_site_crawler(start_url, base_lang, product_urls, sm_vibs, progress_container, status_text):
    parsed_start = urlparse(start_url)
    allowed_domain = parsed_start.netloc
    
    # Initialize the tracking queues matching CrawlSpider rules
    to_visit = set([f"{parsed_start.scheme}://{allowed_domain}/{base_lang}/"])
    to_visit.update(product_urls)  # Seeds from sitemap data
    
    visited = set()
    crawled_data_map = {}
    
    CONCURRENT_LIMIT = 16
    sem = asyncio.Semaphore(CONCURRENT_LIMIT)
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    # Hard safety boundary limits for server stability
    MAX_PAGES = 1800
    
    async with aiohttp.ClientSession(headers=headers) as session:
        while to_visit and len(visited) < MAX_PAGES:
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
                url, html_text, status_code = res
                if not html_text:
                    continue
                
                # If a product configuration link is spotted, process the advanced pricing matrix fields
                if "/product/" in url.lower() or "/mkt-product/" in url.lower():
                    parsed_metrics = parse_html_inventory(url, html_text, status_code, base_lang)
                    vib_key = parsed_metrics['VIB']
                    crawled_data_map[vib_key] = parsed_metrics
                
                # Recursive Link Extraction corresponding to your Rule(LinkExtractor(allow=f"/{self.lang}/"), follow=True)
                links = re.findall(r'href=["\'](https?://[^"\']+|/[^"\']*)["\']', html_text)
                for link in links:
                    if link.startswith("/"):
                        link = urljoin(url, link)
                    
                    p_link = urlparse(link)
                    if p_link.netloc == allowed_domain and link not in visited and link not in to_visit:
                        # Follow matching directories exclusively while discarding raw media files
                        if f"/{base_lang}/" in link.lower() and not any(ext in p_link.path.lower() for ext in ['.pdf', '.jpg', '.png', '.css', '.js', '.zip']):
                            to_visit.add(link)
            
            status_text.markdown(f"⏳ **Deep Recursive Link Crawl Active...** | Pages Scanned: `{len(visited)}` | Discovered Catalog Models: `{len(crawled_data_map)}`")
            progress_container.progress(min(int((len(visited) / 600) * 100), 100))
            
    # Process unified master balance trace dictionary blocks
    master_reporting_rows = []
    all_unique_vibs = set(crawled_data_map.keys()).union(sm_vibs)
    
    for vib in all_unique_vibs:
        in_crawl = vib in crawled_data_map
        in_xml = vib in sm_vibs
        discovery = "Both" if (in_crawl and in_xml) else ("Sitemap Only" if in_xml else "Live Only")
        data = crawled_data_map.get(vib, {})
        
        master_reporting_rows.append({
            'VIB': vib,
            'Site Language': data.get('Site Language', base_lang),
            'Found In': discovery,
            'URL': data.get('URL', 'N/A'),
            'HTTP Status': data.get('Status', 'Timeout/No Response'),
            'Active Price': data.get('Active Price', 'N/A'),
            'Promotional Price': data.get('Promotional Price', ''),
            'Actual/Original Price': data.get('Actual/Original Price', 'N/A'),
            'Tax Configuration': data.get('Tax Configuration', 'N/A'),
            'Buy From Retailer': data.get('Buy From Retailer', 'No'),
            'Stock Status': data.get('Stock Status', 'N/A'),
            'Availability Text Copy': data.get('Availability Text Copy', 'N/A'),
            'Retailer Names': data.get('Retailer Names', 'N/A'),
            'Find Local Dealer': data.get('Find Local Dealer', 'Not Available')
        })
        
    return master_reporting_rows

# -------------------------------------------------------------------------
# 🖥️ STREAMLIT APPLICATION INTERFACE
# -------------------------------------------------------------------------
def render():
    st.title("📦 Product Delta Tracker (Scrapy Translation)")
    st.caption("Deep recursive crawler processing advanced pricing structures and distributor maps across regional targets.")

    if "master_audit_payload" not in st.session_state:
        st.session_state.master_audit_payload = None
    if "audit_meta_string" not in st.session_state:
        st.session_state.audit_meta_string = ""

    # --- CONFIGURATION BOX ---
    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col1:
            sitemap_url = st.text_input("Sitemap XML URL Seed", value="https://www.bosch-home.com/za/sitemap.xml")
            country = st.text_input("Country Identifier (e.g., ZA, SG, UA)", value="ZA").upper().strip()
        with col2:
            brand = st.selectbox("Target Brand", ["BOSCH", "SIEMENS", "NEFF"])

    # --- TRIGGER RUN ---
    if st.button("🚀 INITIATE CURRENT WEEKLY INVENTORY SNAPSHOT", use_container_width=True):
        if not sitemap_url or not country:
            st.error("Please fill in both fields before executing.")
        else:
            st.session_state.master_audit_payload = None
            st.session_state.audit_meta_string = ""
            
            progress_bar = st.progress(0, text="Deploying structural bots...")
            status_text = st.empty()
            
            status_text.info("Step 1: Reading reference sitemap structures...")
            try:
                cache_buster = f"{sitemap_url}?t={int(time.time())}"
                sm_df = adv.sitemap_to_df(cache_buster)
                all_urls = sm_df['loc'].dropna().unique().tolist()
                product_urls = [u for u in all_urls if "/product/" in u or "/mkt-product/" in u]
                sm_vibs = {u.rstrip('/').split('/')[-1].split('?')[0] for u in product_urls}
            except Exception:
                product_urls = []
                sm_vibs = set()
                
            base_lang = "vi" if "/vi/" in sitemap_url else "en"
            parsed_root = urlparse(sitemap_url)
            start_url = f"{parsed_root.scheme}://{parsed_root.netloc}/{base_lang}/"
            
            status_text.info("Step 2: Spawning deep recursive web traversal loops...")
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            master_audit_data = loop.run_until_complete(
                recursive_site_crawler(start_url, base_lang, product_urls, sm_vibs, progress_bar, status_text)
            )
            loop.close()
            
            # Save snapshots down into central database frameworks
            today = datetime.now().strftime("%Y-%m-%d")
            if master_audit_data:
                conn = sqlite3.connect("database.db")
                conn.execute("PRAGMA journal_mode=WAL;")
                cur = conn.cursor()
                for item in master_audit_data:
                    if item['URL'] != 'N/A':
                        cur.execute("""
                            INSERT INTO product_snapshots (url, model_number, brand, country, status_code, snapshot_date, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (item['URL'], item['VIB'], brand, country, 200, today, time.time()))
                conn.commit()
                conn.close()
                
                st.session_state.master_audit_payload = master_audit_data
                st.session_state.audit_meta_string = f"✅ Crawl cycle complete! Saved {len(master_audit_data)} platform inventory records."
                progress_bar.progress(100)
                status_text.empty()
            else:
                st.error("No data collected during execution loop phase blocks.")

    # --- IMMEDIATE WORKSPACE BACKUP DOWNLOAD GENERATION ENGINE ---
    if st.session_state.master_audit_payload:
        st.success(st.session_state.audit_meta_string)
        with st.container(border=True):
            st.markdown("### 📥 Current Run Consolidated Audit Logs")
            df_display = pd.DataFrame(st.session_state.master_audit_payload)
            st.dataframe(df_display, use_container_width=True)
            
            parsed_domain = urlparse(sitemap_url).netloc.replace('.', '_')
            base_lang = "vi" if "/vi/" in sitemap_url else "en"
            excel_bytes = build_split_excel(st.session_state.master_audit_payload, parsed_domain, base_lang)
            
            if excel_bytes:
                st.download_button(
                    label="⬇️ Download Multi-Tab Split Audit Report (Excel)",
                    data=excel_bytes,
                    file_name=f"VIB_Master_Split_Audit_{parsed_domain}_{base_lang}.xlsx",
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

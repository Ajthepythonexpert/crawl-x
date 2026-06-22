import streamlit as st
import pandas as pd
import sqlite3
import time
from datetime import datetime
from urllib.parse import urlparse

# Scrapy High-Performance Core Imports
import scrapy
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from scrapy.crawler import Crawler
from scrapy.utils.project import get_project_settings
import advertools as adv

# 📦 METADATA DECLARATION FOR THE DASHBOARD REGISTRY LOOP
INFO = {
    "title": "Product Delta Tracker",
    "icon": "📦",
    "description": "High-performance asynchronous Scrapy spider to discover inventory discrepancies across markets."
}

# -------------------------------------------------------------------------
# 🕷️ YOUR WORKING SCRAPY SPIDER (Optimized for Streamlit Memory Structuring)
# -------------------------------------------------------------------------
class BoschGrandMasterSplitAuditor(CrawlSpider):
    name = 'bosch_split_auditor'

    def __init__(self, sitemap_url=None, sitemap_urls_list=None, sitemap_vibs=None, country="ZA", brand="BOSCH", results_accumulator=None, *args, **kwargs):
        super(BoschGrandMasterSplitAuditor, self).__init__(*args, **kwargs)
        self.sitemap_url = sitemap_url
        parsed = urlparse(sitemap_url)
        self.domain = parsed.netloc
        self.country = country
        self.brand = brand
        self.lang = "vi" if "/vi/" in sitemap_url else "en"
        self.allowed_domains = [self.domain]
        self.results_accumulator = results_accumulator if results_accumulator is not None else []
        
        self.start_urls = [f"{parsed.scheme}://{self.domain}/{self.lang}/"]
        if sitemap_urls_list:
            self.start_urls.extend(sitemap_urls_list)
        
        self.rules = (
            Rule(LinkExtractor(allow=f"/{self.lang}/"), callback='parse_item', follow=True),
        )
        self._compile_rules()
        self.sitemap_vibs = sitemap_vibs if sitemap_vibs else set()

    def parse_item(self, response):
        url = response.url
        if "/product/" in url or "/mkt-product/" in url:
            vib = url.rstrip('/').split('/')[-1].split('?')[0]
            
            avail_text = response.xpath('//*[@data-testid="availability-text-with-link-text"]/text()').get()
            avail_text_copy = avail_text.strip() if avail_text else "In Stock"
            
            # Record item instantly to reference arrays
            self.results_accumulator.append({
                "url": url,
                "model_number": vib,
                "availability": avail_text_copy
            })

# -------------------------------------------------------------------------
# ⚙️ INLINE CRAWL EXECUTION WRAPPER (Cloud Environment Compliant)
# -------------------------------------------------------------------------
def run_inline_crawler(sitemap_url, country, brand, product_urls, sm_vibs):
    """Executes the Scrapy spider asynchronously inside the primary engine thread context."""
    scraped_items = []
    
    settings = get_project_settings()
    settings.update({
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'LOG_LEVEL': 'INFO',
        'CONCURRENT_REQUESTS': 16,
        'DOWNLOAD_DELAY': 0.1,
        'COOKIES_ENABLED': False,
        'TELNETCONSOLE_ENABLED': False
    })
    
    # Initialize the Scrapy crawler engine instance directly
    crawler = Crawler(BoschGrandMasterSplitAuditor, settings)
    
    # Instantiate your custom parameters directly into the compilation engine
    spider = BoschGrandMasterSplitAuditor(
        sitemap_url=sitemap_url,
        sitemap_urls_list=product_urls,
        sitemap_vibs=sm_vibs,
        country=country,
        brand=brand,
        results_accumulator=scraped_items
    )
    
    # Run the internal crawling pipeline loop synchronously inside this scope block
    crawler.crawl(spider)
    
    # Write the results down into your central database framework directly
    today = datetime.now().strftime("%Y-%m-%d")
    if scraped_items:
        conn = sqlite3.connect("database.db")
        conn.execute("PRAGMA journal_mode=WAL;")
        cur = conn.cursor()
        for item in scraped_items:
            cur.execute("""
                INSERT INTO product_snapshots (url, model_number, brand, country, status_code, snapshot_date, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (item["url"], item["model_number"], brand, country, 200, today, time.time()))
        conn.commit()
        conn.close()
        
    return scraped_items

# -------------------------------------------------------------------------
# 🖥️ STREAMLIT FRONTEND USER INTERFACE LAYER
# -------------------------------------------------------------------------
def render():
    st.title("📦 Product Delta Tracker (Scrapy Async Engine)")
    st.caption("High-performance auditing interface powered by Scrapy multi-threaded link crawlers.")

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
            with st.status("🕷️ Scrapy Engine Deploying...", expanded=True) as status:
                st.write("Step 1: Reading base XML records to backfill reference catalog sets...")
                try:
                    sm_df = adv.sitemap_to_df(sitemap_url)
                    all_urls = sm_df['loc'].dropna().unique().tolist()
                    product_urls = [u for u in all_urls if "/product/" in u or "/mkt-product/" in u]
                    sm_vibs = {u.rstrip('/').split('/')[-1] for u in product_urls}
                except Exception:
                    product_urls = []
                    sm_vibs = set()
                
                st.write(f"Step 2: Commencing safe async link discovery crawler on core system domain...")
                payload = run_inline_crawler(sitemap_url, country, brand, product_urls, sm_vibs)
                
                status.update(label="✅ Inventory Run Finalized successfully!", state="complete")
                st.success(f"Successfully tracked and evaluated live pages! Refreshing data arrays...")
                time.sleep(1)
                st.rerun()

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

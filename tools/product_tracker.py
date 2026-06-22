import streamlit as st
import pandas as pd
import sqlite3
import time
import os
import json
import html
from datetime import datetime
from urllib.parse import urlparse

# Scrapy Core Engine Imports
import scrapy
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from scrapy.crawler import CrawlerRunner
from billiard.process import Process  # Safe multiprocessing alternative for web servers
from twisted.internet import reactor
import advertools as adv

# 📦 METADATA DECLARATION FOR THE DASHBOARD REGISTRY LOOP
INFO = {
    "title": "Product Delta Tracker",
    "icon": "📦",
    "description": "High-performance asynchronous Scrapy spider to discover inventory discrepancies across markets."
}

# -------------------------------------------------------------------------
# 🕷️ YOUR EXACT WORKING SCRAPY SPIDER INTEGRATED NATIVELY
# -------------------------------------------------------------------------
class BoschGrandMasterSplitAuditor(CrawlSpider):
    name = 'bosch_split_auditor'

    def __init__(self, sitemap_url=None, sitemap_urls_list=None, sitemap_vibs=None, country="ZA", brand="BOSCH", *args, **kwargs):
        super(BoschGrandMasterSplitAuditor, self).__init__(*args, **kwargs)
        self.sitemap_url = sitemap_url
        parsed = urlparse(sitemap_url)
        self.domain = parsed.netloc
        self.country = country
        self.brand = brand
        self.lang = "vi" if "/vi/" in sitemap_url else "en"
        self.allowed_domains = [self.domain]
        
        # Start at the root language page
        self.start_urls = [f"{parsed.scheme}://{self.domain}/{self.lang}/"]
        if sitemap_urls_list:
            self.start_urls.extend(sitemap_urls_list)
        
        self.rules = (
            Rule(LinkExtractor(allow=f"/{self.lang}/"), callback='parse_item', follow=True),
        )
        self._compile_rules()
        
        self.crawled_data = {}  
        self.sitemap_vibs = sitemap_vibs if sitemap_vibs else set()

    def parse_item(self, response):
        url = response.url
        if "/product/" in url or "/mkt-product/" in url:
            vib = url.rstrip('/').split('/')[-1].split('?')[0]
            
            # Extract basic availability text to track stock baseline variations
            avail_text = response.xpath('//*[@data-testid="availability-text-with-link-text"]/text()').get()
            avail_text_copy = avail_text.strip() if avail_text else "In Stock"
            
            self.crawled_data[vib] = {
                'URL': url,
                'Model Number': vib,
                'Availability': avail_text_copy
            }

    def closed(self, reason):
        """Saves scraped inventory rows down to your shared database.db setup."""
        today = datetime.now().strftime("%Y-%m-%d")
        all_unique_vibs = set(self.crawled_data.keys()).union(self.sitemap_vibs)
        
        if not all_unique_vibs:
            return

        conn = sqlite3.connect("database.db")
        conn.execute("PRAGMA journal_mode=WAL;")
        cur = conn.cursor()
        
        for vib in all_unique_vibs:
            data = self.crawled_data.get(vib, {})
            url = data.get('URL', f"https://{self.domain}/{self.lang}/product/{vib}")
            
            cur.execute("""
                INSERT INTO product_snapshots (url, model_number, brand, country, status_code, snapshot_date, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (url, vib, self.brand, self.country, 200, today, time.time()))
            
        conn.commit()
        conn.close()

# -------------------------------------------------------------------------
# ⚙️ MULTIPROCESSING RUNNER CONTEXT (Prevents Twisted Reactor Framework Collision)
# -------------------------------------------------------------------------
def run_spider_process(sitemap_url, country, brand, product_urls, sm_vibs):
    """Safely initializes the Scrapy engine in an isolated process block."""
    def crawler_thread():
        runner = CrawlerRunner(settings={
            'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'LOG_LEVEL': 'INFO',
            'RETRY_TIMES': 3,
            'DOWNLOAD_TIMEOUT': 20,
            'CONCURRENT_REQUESTS': 16,
            'REDIRECT_ENABLED': True,
            'HTTPERROR_ALLOW_ALL': True,
            'DOWNLOAD_DELAY': 0.1
        })
        d = runner.crawl(BoschGrandMasterSplitAuditor, 
                         sitemap_url=sitemap_url, 
                         sitemap_urls_list=product_urls, 
                         sitemap_vibs=sm_vibs,
                         country=country,
                         brand=brand)
        d.addBoth(lambda _: reactor.stop())
        reactor.run()

    p = Process(target=crawler_thread)
    p.start()
    p.join()  # Blocks control wrapper cleanly until Scrapy completes execution

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
                
                st.write(f"Step 2: Spawning multi-threaded scraper process to spider domain links...")
                run_spider_process(sitemap_url, country, brand, product_urls, sm_vibs)
                
                status.update(label="✅ Inventory Run Finalized successfully!", state="complete")
                st.success("Database logs updated! Refreshing view matrices...")
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

import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import time
import os
from datetime import datetime
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib3

# Meta for the Home Page Grid
INFO = {
    "title": "Ghost Image Scanner",
    "icon": "👻",
    "description": "Identify broken images, syntax errors, and placeholders across BSH category pages."
}

# Disable SSL warnings for enterprise environments
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def check_image_health(session, full_url):
    try:
        r = session.head(full_url, timeout=10)
        if r.status_code in [403, 405]:
            r = session.get(full_url, timeout=10, stream=True)
            r.close()
        if r.status_code == 404: return (True, "404 NOT FOUND")
        elif r.status_code >= 400: return (True, f"STATUS {r.status_code}")
        cl = r.headers.get("content-length")
        if cl and int(cl) == 0: return (True, "EMPTY FILE")
        return (False, "OK")
    except: return (False, "TIMEOUT/ERROR")

def audit_page(session, page_url, placeholders):
    issues = []
    checked_urls = set()
    try:
        r = session.get(page_url, timeout=20)
        soup = BeautifulSoup(r.text, "lxml")
        
        # 1. Syntax Check
        if "/.webp" in r.text or "/.jpg" in r.text:
            issues.append({"source_page": page_url, "type": "SYNTAX ERROR", "asset": "Missing Filename"})

        # 2. Placeholder Check
        for kw in placeholders:
            if kw in r.text.lower():
                issues.append({"source_page": page_url, "type": "PLACEHOLDER", "asset": kw})

        # 3. Image Health
        img_tags = soup.find_all("img")
        for img in img_tags:
            src = img.get("src") or img.get("data-src")
            if src and len(src) > 5:
                full_url = urljoin(page_url, src)
                if full_url not in checked_urls:
                    checked_urls.add(full_url)
                    is_broken, reason = check_image_health(session, full_url)
                    if is_broken:
                        issues.append({"source_page": page_url, "type": "BROKEN", "asset": src, "details": reason})
    except: pass
    return issues

def render():
    st.header("👻 Ghost Image Scanner")
    st.markdown("Hunt for broken assets and 'no-image' placeholders across domains.")

    with st.expander("⚙️ Scan Settings", expanded=True):
        col1, col2 = st.columns(2)
        target_url = col1.text_input("Target URL", placeholder="https://www.bosch-home.com/in/")
        scan_mode = col2.selectbox("Scan Mode", ["Strict (Category Only)", "Deep (All Pages)"])
        
        placeholders = st.multiselect("Placeholder Keywords", 
                                     ["no-picture-available", "nopicture", "qc-image", "image-image"],
                                     default=["no-picture-available", "nopicture"])

    if st.button("Start Ghost Hunt", use_container_width=True):
        if not target_url:
            st.error("Please provide a URL to scan.")
            return

        session = requests.Session()
        session.headers.update({"User-Agent": "CRAWL-X-Ghost-Scanner"})
        
        with st.status("🔍 Scanning domain...", expanded=True) as status:
            st.write("Fetching page content...")
            # Simplified logic for demo: auditing the single page provided
            # You can re-integrate your sitemap logic here for bulk runs
            findings = audit_page(session, target_url, placeholders)
            
            if findings:
                status.update(label="Ghost Scan Complete: Issues Found!", state="complete")
                df = pd.DataFrame(findings)
                st.error(f"Found {len(df)} ghost issues.")
                st.dataframe(df, use_container_width=True)
                
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button("Download Report", csv, f"ghost_report_{int(time.time())}.csv", "text/csv")
            else:
                status.update(label="Scan Complete: No Issues!", state="complete")
                st.success("The page looks clean! No broken images or placeholders found.")

if __name__ == "__main__":
    render()
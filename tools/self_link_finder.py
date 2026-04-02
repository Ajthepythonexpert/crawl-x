import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import re

# --- TOOL META ---
INFO = {
    "title": "Self-Link Finder",
    "icon": "🔄",
    "description": "Detect redundant internal links where a page points to its own URL, cluttering crawl depth."
}

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- SESSION MANAGER (BSH TUNED) ---
def create_session():
    s = requests.Session()
    # Retry logic handles flaky regional connections
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(pool_connections=15, pool_maxsize=15, max_retries=retries)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    s.headers.update({"User-Agent": "CRAWL-X-SelfLink-Auditor"})
    s.verify = False
    return s

SESSION = create_session()

# --- HELPERS ---
def classify_link(a):
    """Classifies where the link is located on the page"""
    if a.find_parent("nav"): return "Navigation"
    if a.find_parent("footer"): return "Footer"
    if "btn" in " ".join(a.get("class", [])).lower(): return "CTA Button"
    return "Body/Inline"

def is_self_link(source_url, target_url):
    """Strictly compares normalized URLs to identify self-references"""
    return source_url.rstrip("/") == target_url.rstrip("/")

# --- SCANNER CORE ---
def audit_self_links(url):
    results = []
    try:
        r = SESSION.get(url, timeout=20)
        if r.status_code != 200: return results
        soup = BeautifulSoup(r.text, "lxml")
        
        for a in soup.find_all("a", href=True):
            href = a["href"]
            # Ignore fragments and JS
            if href.startswith("#") or "javascript:" in href:
                continue
                
            full_link = urljoin(url, href)
            if is_self_link(url, full_link):
                results.append({
                    "Source Page": url,
                    "Self-Link URL": full_link,
                    "Element Type": classify_link(a),
                    "Anchor Text": a.get_text(strip=True)[:50] or "[Image/Icon]"
                })
    except: pass
    return results

def fetch_sitemap_urls(sm_url):
    """Extracts URLs from sitemap using regex for speed"""
    try:
        r = SESSION.get(sm_url, timeout=20)
        found = re.findall(r'<loc>(https?://[^<]+)</loc>', r.text)
        return list(set([u.strip() for u in found]))
    except: return []

# --- UI RENDER ---
def render():
    st.header("🔄 Self-Link Finder")
    st.markdown("Identify redundant links that point back to the current page.")

    sitemap_input = st.text_input("Sitemap URL", placeholder="https://www.bosch-home.com/sitemap.xml")
    limit = st.slider("Pages to Audit", 5, 200, 50)

    if st.button("Run Hygiene Audit", use_container_width=True):
        if not sitemap_input:
            st.error("Please provide a sitemap URL.")
            return

        with st.status("🔍 Scanning for redundancies...", expanded=True) as status:
            urls = fetch_sitemap_urls(sitemap_input)[:limit]
            if not urls:
                status.update(label="No URLs found in sitemap.", state="error")
                return

            st.write(f"Auditing {len(urls)} pages...")
            findings = []
            
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = {executor.submit(audit_self_links, u): u for u in urls}
                for f in as_completed(futures):
                    res = f.result()
                    if res: findings.extend(res)

            if findings:
                status.update(label=f"Scan Complete: {len(findings)} Self-Links Found", state="complete")
                df = pd.DataFrame(findings)
                st.warning("Redundant Self-Links Detected")
                st.dataframe(df, use_container_width=True)
                
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button("Download Self-Link Report", csv, "self_links.csv", "text/csv")
            else:
                status.update(label="Scan Complete: No Issues", state="complete")
                st.success("No redundant self-links found in the audited sample.")

if __name__ == "__main__":
    render()
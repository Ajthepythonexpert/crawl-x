import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import time
import pandas as pd
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# --- TOOL META ---
INFO = {
    "title": "ZX / WW Auditor",
    "icon": "🎯",
    "description": "Deep-scan sitemaps for legacy ZX/WW paths, self-links, and structural BSH link issues."
}

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIGURATION ---
SPECIAL_PATHS = ["zx", "ww"]
MAX_THREADS_SCAN = 15
TIMEOUT_SEC = 20

# --- SHARED SESSION MANAGER ---
def create_session():
    s = requests.Session()
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(pool_connections=MAX_THREADS_SCAN, pool_maxsize=MAX_THREADS_SCAN, max_retries=retries)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    s.headers.update({"User-Agent": "CRAWL-X-Enterprise-Scanner"})
    s.verify = False
    return s

SESSION = create_session()

# --- HELPERS ---
def classify_link(a):
    if a.find_parent("nav"): return "Navigation"
    if a.find_parent("footer"): return "Footer"
    if a.find("img"): return "Icon/Image"
    if "btn" in " ".join(a.get("class", [])).lower(): return "CTA Button"
    return "Inline Text"

def get_element_content(a_tag):
    text = a_tag.get_text(strip=True)
    if text: return text[:50]
    img = a_tag.find("img")
    if img:
        src = img.get("src", "")
        filename = src.split("/")[-1].split("?")[0] if src else "image"
        return f"[IMG: {filename}]"
    return "[EMPTY]"

def detect_special(url):
    try:
        parsed = urlparse(url)
        parts = parsed.path.strip("/").split("/")
        if parts and parts[0].lower() in SPECIAL_PATHS: 
            return parts[0].upper() 
    except: pass
    return None

def fetch_sitemap_urls(sm_url):
    try:
        r = SESSION.get(sm_url, timeout=TIMEOUT_SEC)
        if r.status_code != 200: return []
        found = re.findall(r'<loc>(https?://[^<]+)</loc>', r.text)
        return list(set([u.strip() for u in found]))
    except: return []

# --- CORE SCANNER ---
def scan_page(url, source_domain):
    results = []
    try:
        r = SESSION.get(url, timeout=TIMEOUT_SEC)
        if r.status_code != 200: return results
        soup = BeautifulSoup(r.text, "lxml")
        
        for a in soup.find_all("a", href=True):
            full_link = urljoin(url, a["href"])
            kind = detect_special(full_link)
            
            # Check for ZX/WW OR Self-Links (pointing to same page)
            if kind or full_link.rstrip("/") == url.rstrip("/"):
                results.append({
                    "Issue Type": kind if kind else "SELF-LINK",
                    "Page URL": url,
                    "Target Link": full_link,
                    "Location": classify_link(a),
                    "Content": get_element_content(a)
                })
    except: pass
    return results

# --- STREAMLIT UI ---
def render():
    st.header("🎯 ZX / WW & Self-Link Auditor")
    st.markdown("Directly scan a sitemap to identify legacy pathing issues and internal link hygiene.")

    # Input Section
    sitemap_url = st.text_input("Enter Sitemap URL", placeholder="https://www.bosch-home.com/sitemap.xml")
    
    col1, col2 = st.columns(2)
    scan_limit = col1.slider("Page Limit (Safety)", 10, 500, 100)
    include_self = col2.toggle("Flag Self-Links", value=True)

    if st.button("Launch Deep Audit", use_container_width=True):
        if not sitemap_url:
            st.warning("Please enter a valid sitemap URL.")
            return

        with st.status("🚀 Initializing Scan...", expanded=True) as status:
            st.write("Fetching URLs from sitemap...")
            all_urls = fetch_sitemap_urls(sitemap_url)
            target_urls = all_urls[:scan_limit]
            
            if not target_urls:
                status.update(label="Error: Sitemap Unreachable", state="error")
                return

            st.write(f"Auditing {len(target_urls)} pages...")
            all_findings = []
            
            progress_bar = st.progress(0)
            with ThreadPoolExecutor(max_workers=MAX_THREADS_SCAN) as executor:
                futures = {executor.submit(scan_page, u, sitemap_url): u for u in target_urls}
                for i, f in enumerate(as_completed(futures)):
                    res = f.result()
                    if res:
                        # Filter results if Self-Links are toggled off
                        if not include_self:
                            res = [r for r in res if r["Issue Type"] != "SELF-LINK"]
                        all_findings.extend(res)
                    progress_bar.progress((i + 1) / len(target_urls))

            if all_findings:
                status.update(label=f"Audit Complete: {len(all_findings)} Issues Found", state="complete")
                df = pd.DataFrame(all_findings)
                st.error(f"Detected {len(df)} Link Issues")
                st.dataframe(df, use_container_width=True)
                
                # Download
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button("📩 Download ZX/WW Report", csv, "zx_ww_report.csv", "text/csv")
            else:
                status.update(label="Audit Complete: Site is Clean!", state="complete")
                st.success("No ZX, WW, or Self-Link issues detected on the audited pages.")

if __name__ == "__main__":
    render()
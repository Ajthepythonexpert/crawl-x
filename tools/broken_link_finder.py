import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import re

# --- TOOL META ---
INFO = {
    "title": "404 Link Hunter",
    "icon": "🚫",
    "description": "Scan sitemaps to identify broken internal links (404s) that hurt user experience and SEO rankings."
}

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- SESSION MANAGER (BSH TUNED) ---
def create_session():
    s = requests.Session()
    # Retry logic handles flaky regional connections
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(pool_connections=20, pool_maxsize=20, max_retries=retries)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    s.headers.update({"User-Agent": "CRAWL-X-404-Hunter"})
    s.verify = False
    return s

SESSION = create_session()

# --- HELPERS ---
def check_url_status(url):
    """Verifies if a URL is alive or broken"""
    try:
        # Use HEAD first for speed, fallback to GET if server blocks HEAD
        r = SESSION.head(url, timeout=10, allow_redirects=True)
        if r.status_code in [403, 405]:
            r = SESSION.get(url, timeout=10, stream=True, allow_redirects=True)
            r.close()
        
        if r.status_code == 404:
            return True, "404 Not Found"
        if r.status_code >= 400:
            return True, f"Error {r.status_code}"
        return False, "OK"
    except:
        return True, "Timeout/Connection Error"

def get_broken_links_on_page(page_url):
    findings = []
    checked_links = set()
    try:
        r = SESSION.get(page_url, timeout=20)
        if r.status_code != 200: return []
        soup = BeautifulSoup(r.text, "lxml")
        
        # Extract all internal/external links
        links = [urljoin(page_url, a['href']) for a in soup.find_all("a", href=True) 
                 if not a['href'].startswith(("#", "javascript:", "mailto:", "tel:"))]
        
        for link in links:
            if link not in checked_links:
                checked_links.add(link)
                is_broken, reason = check_url_status(link)
                if is_broken:
                    findings.append({
                        "Source Page": page_url,
                        "Broken Link": link,
                        "Status": reason
                    })
    except: pass
    return findings

def fetch_sitemap_urls(sm_url):
    """Extracts URLs from sitemap"""
    try:
        r = SESSION.get(sm_url, timeout=20)
        found = re.findall(r'<loc>(https?://[^<]+)</loc>', r.text)
        return list(set([u.strip() for u in found]))
    except: return []

# --- UI RENDER ---
def render():
    st.header("🚫 404 Link Hunter")
    st.markdown("Identify dead links across your domain to improve crawl efficiency and UX.")

    sitemap_input = st.text_input("Sitemap URL", placeholder="https://www.bosch-home.com/sitemap.xml")
    limit = st.slider("Pages to Audit", 5, 100, 20)

    if st.button("Start 404 Search", use_container_width=True):
        if not sitemap_input:
            st.error("Please provide a sitemap URL.")
            return

        with st.status("📡 Probing for broken links...", expanded=True) as status:
            urls = fetch_sitemap_urls(sitemap_input)[:limit]
            if not urls:
                status.update(label="No URLs found in sitemap.", state="error")
                return

            st.write(f"Auditing links on {len(urls)} pages...")
            all_broken = []
            
            # Using ThreadPool for Phase 2 Auditing
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = {executor.submit(get_broken_links_on_page, u): u for u in urls}
                for f in as_completed(futures):
                    res = f.result()
                    if res: all_broken.extend(res)

            if all_broken:
                status.update(label=f"Audit Complete: {len(all_broken)} Broken Links Found", state="complete")
                df = pd.DataFrame(all_broken)
                st.error("Broken Links Detected")
                st.dataframe(df, use_container_width=True)
                
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button("📩 Download 404 Report", csv, "broken_links_report.csv", "text/csv")
            else:
                status.update(label="Audit Complete: All Links OK", state="complete")
                st.success("No broken links found in the audited sample. Excellent link health!")

if __name__ == "__main__":
    render()
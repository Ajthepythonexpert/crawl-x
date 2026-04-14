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
    "title": "Self-Link Finder",
    "icon": "🔄",
    "description": "Detect redundant internal links where a page points to its own URL."
}

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- SESSION ---
def create_session():
    s = requests.Session()
    retries = Retry(total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(pool_connections=30, pool_maxsize=30, max_retries=retries)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    s.headers.update({"User-Agent": "CRAWL-X-SelfLink-Auditor"})
    s.verify = False
    return s

SESSION = create_session()

# --- HELPERS ---
def classify_link(a):
    if a.find_parent("nav"):
        return "Navigation"
    if a.find_parent("footer"):
        return "Footer"
    if "btn" in " ".join(a.get("class", [])).lower():
        return "CTA Button"
    return "Body/Inline"

def is_self_link(source_url, target_url):
    return source_url.rstrip("/") == target_url.rstrip("/")

# --- CORE SCAN ---
def audit_self_links(url):
    results = []
    try:
        r = SESSION.get(url, timeout=10)
        if r.status_code != 200:
            return results

        soup = BeautifulSoup(r.text, "lxml")

        for a in soup.find_all("a", href=True):
            href = a["href"]

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
    except:
        pass

    return results

# --- SITEMAP FETCH ---
def fetch_sitemap_urls(sm_url):
    try:
        r = SESSION.get(sm_url, timeout=15)
        urls = re.findall(r'<loc>(https?://[^<]+)</loc>', r.text)
        return list(set([u.strip() for u in urls]))
    except:
        return []

# --- UI ---
def render():
    st.header("🔄 Self-Link Finder")
    st.markdown("Identify redundant links that point back to the same page.")

    sitemap_input = st.text_input(
        "Sitemap URL",
        placeholder="https://www.bosch-home.com/sitemap.xml"
    )

    limit = st.number_input(
        "Max Pages (0 = Full Sitemap)",
        min_value=0,
        value=0
    )

    if st.button("Run Hygiene Audit", use_container_width=True):

        if not sitemap_input:
            st.error("Please provide a sitemap URL.")
            return

        with st.status("🔍 Scanning pages...", expanded=True) as status:

            urls = fetch_sitemap_urls(sitemap_input)

            if not urls:
                status.update(label="No URLs found in sitemap.", state="error")
                return

            if limit > 0:
                urls = urls[:limit]

            total = len(urls)
            st.write(f"🚀 Auditing {total} pages...")

            MAX_WORKERS = 30
            BATCH_SIZE = 100

            progress = st.progress(0)
            findings = []

            for i in range(0, total, BATCH_SIZE):
                batch = urls[i:i + BATCH_SIZE]

                with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                    futures = {executor.submit(audit_self_links, u): u for u in batch}

                    for j, f in enumerate(as_completed(futures)):
                        try:
                            res = f.result()
                            if res:
                                findings.extend(res)
                        except:
                            pass

                        progress.progress(min((i + j + 1) / total, 1.0))

            if findings:
                status.update(
                    label=f"Scan Complete: {len(findings)} Self-Links Found",
                    state="complete"
                )

                df = pd.DataFrame(findings)
                st.warning("⚠️ Redundant Self-Links Detected")
                st.dataframe(df, use_container_width=True)

                csv = df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "Download Report",
                    csv,
                    "self_links.csv",
                    "text/csv"
                )

            else:
                status.update(label="Scan Complete: No Issues", state="complete")
                st.success("✅ No self-links found!")

if __name__ == "__main__":
    render()

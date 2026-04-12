import streamlit as st
import requests
import pandas as pd
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- SESSION SETUP ---
def create_session():
    s = requests.Session()
    retries = Retry(total=3, backoff_factor=0.5,
                    status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(pool_connections=50, pool_maxsize=50, max_retries=retries)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    s.headers.update({"User-Agent": "CRAWL-X-404-Hunter"})
    s.verify = False
    return s

SESSION = create_session()

# --- FETCH ALL URLS (Handles nested sitemaps) ---
def fetch_all_sitemap_urls(sitemap_url):
    urls = set()
    try:
        r = SESSION.get(sitemap_url, timeout=15)
        locs = re.findall(r'<loc>(.*?)</loc>', r.text)

        for loc in locs:
            loc = loc.strip()
            if loc.endswith(".xml"):
                urls.update(fetch_all_sitemap_urls(loc))  # recursive
            else:
                urls.add(loc)
    except:
        pass

    return urls

# --- FAST URL CHECK ---
def check_url_fast(url):
    try:
        r = SESSION.head(url, timeout=5, allow_redirects=True)

        if r.status_code in [403, 405]:
            r = SESSION.get(url, timeout=5, stream=True)
            r.close()

        if r.status_code == 404:
            return {"URL": url, "Status": "404 Not Found"}
        elif r.status_code >= 400:
            return {"URL": url, "Status": f"Error {r.status_code}"}

        return None

    except:
        return {"URL": url, "Status": "Timeout/Error"}

# --- STREAMLIT UI ---
def render():
    st.set_page_config(page_title="404 Link Hunter", layout="wide")

    st.title("🚫 404 Link Hunter (Full Website Scanner)")
    st.markdown("Scan your **entire sitemap** and detect all broken URLs (404s & errors).")

    sitemap_input = st.text_input(
        "Enter Sitemap URL",
        placeholder="https://www.example.com/sitemap.xml"
    )

    max_workers = st.slider("Speed (Threads)", 5, 50, 20)

    if st.button("🚀 Start Full Site Scan", use_container_width=True):

        if not sitemap_input:
            st.error("Please enter a sitemap URL")
            return

        with st.status("🌐 Fetching URLs from sitemap...", expanded=True):

            urls = fetch_all_sitemap_urls(sitemap_input)

            if not urls:
                st.error("No URLs found in sitemap")
                return

            urls = list(urls)
            st.write(f"✅ Total URLs found: {len(urls)}")

            broken_links = []

            st.write("⚡ Checking URL status (this may take time for large sites)...")

            progress = st.progress(0)

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(check_url_fast, url): url for url in urls}

                for i, f in enumerate(as_completed(futures)):
                    res = f.result()
                    if res:
                        broken_links.append(res)

                    progress.progress((i + 1) / len(urls))

        # --- RESULTS ---
        if broken_links:
            df = pd.DataFrame(broken_links)

            st.error(f"❌ {len(df)} Broken URLs Found")
            st.dataframe(df, use_container_width=True)

            st.download_button(
                "📩 Download Report",
                df.to_csv(index=False).encode("utf-8"),
                "broken_links_report.csv",
                "text/csv"
            )
        else:
            st.success("🎉 No broken URLs found. Site is healthy!")

# --- RUN ---
if __name__ == "__main__":
    render()

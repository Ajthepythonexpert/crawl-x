import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import time
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- SESSION ---
def create_session():
    s = requests.Session()
    s.headers.update({"User-Agent": "CRAWL-X-Ghost-Scanner"})
    s.verify = False
    return s

SESSION = create_session()

# --- FETCH ALL URLS FROM SITEMAP ---
def fetch_sitemap_urls(sitemap_url):
    urls = set()
    try:
        r = SESSION.get(sitemap_url, timeout=15)
        locs = re.findall(r'<loc>(.*?)</loc>', r.text)

        for loc in locs:
            loc = loc.strip()
            if loc.endswith(".xml"):
                urls.update(fetch_sitemap_urls(loc))  # recursive
            else:
                urls.add(loc)
    except:
        pass
    return list(urls)

# --- IMAGE HEALTH ---
def check_image_health(full_url):
    try:
        r = SESSION.head(full_url, timeout=5)

        if r.status_code in [403, 405]:
            r = SESSION.get(full_url, timeout=5, stream=True)
            r.close()

        if r.status_code == 404:
            return True, "404 NOT FOUND"
        elif r.status_code >= 400:
            return True, f"STATUS {r.status_code}"

        cl = r.headers.get("content-length")
        if cl and int(cl) == 0:
            return True, "EMPTY FILE"

        return False, "OK"

    except:
        return True, "TIMEOUT/ERROR"

# --- PAGE AUDIT ---
def audit_page(page_url, placeholders):
    issues = []
    checked_images = set()

    try:
        r = SESSION.get(page_url, timeout=10)
        soup = BeautifulSoup(r.text, "lxml")

        # Syntax check
        if "/.webp" in r.text or "/.jpg" in r.text:
            issues.append({
                "source_page": page_url,
                "type": "SYNTAX ERROR",
                "asset": "Missing Filename"
            })

        # Placeholder check
        for kw in placeholders:
            if kw in r.text.lower():
                issues.append({
                    "source_page": page_url,
                    "type": "PLACEHOLDER",
                    "asset": kw
                })

        # Image check
        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src")

            if src:
                full_url = urljoin(page_url, src)

                if full_url not in checked_images:
                    checked_images.add(full_url)

                    is_broken, reason = check_image_health(full_url)

                    if is_broken:
                        issues.append({
                            "source_page": page_url,
                            "type": "BROKEN IMAGE",
                            "asset": full_url,
                            "details": reason
                        })

    except:
        pass

    return issues

# --- UI ---
def render():
    st.set_page_config(page_title="Ghost Image Scanner", layout="wide")

    st.title("👻 Ghost Image Scanner (Full Website)")
    st.markdown("Scan all pages to detect broken images, placeholders, and syntax issues.")

    sitemap_url = st.text_input("Sitemap URL", placeholder="https://example.com/sitemap.xml")

    placeholders = st.multiselect(
        "Placeholder Keywords",
        ["no-picture-available", "nopicture", "qc-image", "image-image"],
        default=["no-picture-available", "nopicture"]
    )

    threads = st.slider("Speed (Threads)", 5, 30, 15)

    if st.button("🚀 Start Full Scan", use_container_width=True):

        if not sitemap_url:
            st.error("Please enter sitemap URL")
            return

        with st.status("🌐 Fetching all pages...", expanded=True):

            urls = fetch_sitemap_urls(sitemap_url)

            if not urls:
                st.error("No URLs found")
                return

            st.write(f"✅ Total pages: {len(urls)}")

            all_issues = []
            progress = st.progress(0)

            with ThreadPoolExecutor(max_workers=threads) as executor:
                futures = {executor.submit(audit_page, url, placeholders): url for url in urls}

                for i, f in enumerate(as_completed(futures)):
                    result = f.result()
                    if result:
                        all_issues.extend(result)

                    progress.progress((i + 1) / len(urls))

        # --- RESULTS ---
        if all_issues:
            df = pd.DataFrame(all_issues)

            st.error(f"❌ Found {len(df)} issues")
            st.dataframe(df, use_container_width=True)

            st.download_button(
                "📩 Download Report",
                df.to_csv(index=False).encode("utf-8"),
                f"ghost_report_{int(time.time())}.csv"
            )
        else:
            st.success("🎉 No ghost issues found!")

# --- RUN ---
if __name__ == "__main__":
    render()

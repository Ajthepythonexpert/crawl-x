import streamlit as st
import pandas as pd
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# ─── Use ONE consistent import path matching your project structure ───
# If your utils live at core/utils.py:
from core.utils import get_sitemap_urls, find_pdfs_on_page, search_keyword_in_pdf
# If your utils live at utils.py (root):
# from utils import get_sitemap_urls, find_pdfs_on_page, search_keyword_in_pdf

# ─── REQUIRED: Auto-discovery metadata for the Dashboard ─────────────
INFO = {
    "title": "PDF Keyword Scanner",
    "icon": "📄",
    "description": "Scan all PDFs across a sitemap for a specific keyword."
}

# ─── CORE LOGIC ──────────────────────────────────────────────────────
def run_pdf_scan(sitemap_url, keyword, max_workers=10):
    page_urls = get_sitemap_urls(sitemap_url)
    all_pdfs = {}
    lock = threading.Lock()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(find_pdfs_on_page, url): url for url in page_urls}
        for future in as_completed(futures):
            source_url = futures[future]
            try:
                pdfs = future.result()
            except Exception:
                continue
            if pdfs:
                with lock:
                    for pdf in pdfs:
                        all_pdfs[pdf] = source_url

    results = []
    flagged = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(search_keyword_in_pdf, pdf_url, keyword): (pdf_url, src)
            for pdf_url, src in all_pdfs.items()
        }
        for future in as_completed(futures):
            pdf_url, src = futures[future]
            try:
                res = future.result()
            except Exception:
                continue
            res["source_page"] = src
            results.append(res)
            if res.get("flagged"):
                flagged.append(res)

    return results, flagged


# ─── STREAMLIT UI ─────────────────────────────────────────────────────
# No wrapper function — just top-level Streamlit code.
# This is what app.py's st.Page() expects when it runs the file.

st.markdown("""
<div class='tool-header'>
    <div class='tool-title'>📄 PDF Keyword Scanner</div>
    <p style='color:#666; margin:0;'>Scan every PDF linked across your sitemap for a keyword.</p>
</div>
""", unsafe_allow_html=True)

sitemap_url = st.text_input("Enter Website or Sitemap URL", placeholder="https://example.com or https://example.com/sitemap.xml")
keyword = st.text_input("Keyword to Search", value="1993")

if st.button("🔍 Run PDF Scan"):
    if not sitemap_url:
        st.error("Please enter a website or sitemap URL.")
        st.stop()

    if not sitemap_url.endswith(".xml"):
        sitemap_url = sitemap_url.rstrip("/") + "/sitemap.xml"

    with st.spinner("Crawling sitemap and scanning PDFs..."):
        try:
            results, flagged = run_pdf_scan(sitemap_url, keyword)
        except Exception as e:
            st.error(f"Scan failed: {e}")
            st.stop()

    st.success(f"✅ {len(results)} PDFs scanned — {len(flagged)} flagged for keyword **'{keyword}'**")

    col1, col2, col3 = st.columns(3)
    col1.metric("Total PDFs Found", len(results))
    col2.metric("Flagged PDFs", len(flagged))
    col3.metric("Clean PDFs", len(results) - len(flagged))

    if flagged:
        st.subheader("🚨 Flagged PDFs")
        st.dataframe(pd.DataFrame(flagged), use_container_width=True)

    if results:
        st.subheader("📋 All Results")
        st.dataframe(pd.DataFrame(results), use_container_width=True)

        csv = pd.DataFrame(results).to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download Full Report (CSV)", csv, "pdf_scan_results.csv", "text/csv")
    else:
        st.warning("No PDFs were found across the sitemap.")

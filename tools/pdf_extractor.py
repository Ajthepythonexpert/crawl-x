import streamlit as st
import pandas as pd
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import core.utils

# ✅ FIXED IMPORT (based on your current setup)
from utils import *


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


def main():
    st.write("✅ PDF TOOL LOADED")

    st.markdown("""
    <div class='tool-header'>
        <div class='tool-title'>📄 PDF Keyword Scanner</div>
    </div>
    """, unsafe_allow_html=True)

    sitemap_url = st.text_input("Enter Website or Sitemap")
    keyword = st.text_input("Keyword", value="1993")

    if st.button("Run Scan"):

        if not sitemap_url:
            st.error("Please enter a website or sitemap")
            return

        if not sitemap_url.endswith(".xml"):
            sitemap_url = sitemap_url.rstrip("/") + "/sitemap.xml"

        with st.spinner("Scanning PDFs..."):
            try:
                results, flagged = run_pdf_scan(sitemap_url, keyword)
            except Exception as e:
                st.error(f"Error: {e}")
                return

        df_all = pd.DataFrame(results)
        df_flagged = pd.DataFrame(flagged)

        st.success(f"{len(results)} PDFs scanned | {len(flagged)} flagged")

        st.dataframe(df_flagged)


# 🔥 REQUIRED
main()

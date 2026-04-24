import streamlit as st
import pandas as pd
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# ✅ IMPORT YOUR FUNCTIONS HERE
# Example:
# from utils.pdf_utils import get_sitemap_urls, find_pdfs_on_page, search_keyword_in_pdf


def run_pdf_scan(sitemap_url, keyword, max_workers=10):
    page_urls = get_sitemap_urls(sitemap_url)

    all_pdfs = {}
    lock = threading.Lock()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(find_pdfs_on_page, url): url for url in page_urls}
        for future in as_completed(futures):
            source_url = futures[future]
            pdfs = future.result()
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
            res = future.result()
            res["source_page"] = src

            results.append(res)
            if res["flagged"]:
                flagged.append(res)

    return results, flagged


# ✅ MUST BE main()
def main():
    st.markdown("""
    <div class='tool-header'>
        <div class='tool-title'>📄 PDF Keyword Scanner</div>
    </div>
    """, unsafe_allow_html=True)

    sitemap_url = st.text_input(
        "Enter Website or Sitemap",
        placeholder="https://example.com OR https://example.com/sitemap.xml"
    )

    keyword = st.text_input("Keyword", value="1993")

    if st.button("Run Scan"):

        if not sitemap_url:
            st.error("Please enter a website or sitemap")
            return

        if not sitemap_url.endswith(".xml"):
            sitemap_url = sitemap_url.rstrip("/") + "/sitemap.xml"

        with st.spinner("Scanning PDFs across the website..."):
            results, flagged = run_pdf_scan(sitemap_url, keyword)

        df_all = pd.DataFrame(results)
        df_flagged = pd.DataFrame(flagged)

        st.success(f"✅ {len(results)} PDFs scanned | {len(flagged)} flagged")

        st.subheader("🚨 Flagged PDFs")
        st.dataframe(df_flagged, use_container_width=True)

        st.download_button(
            "⬇️ Download Flagged CSV",
            df_flagged.to_csv(index=False),
            "flagged_pdfs.csv"
        )

        with st.expander("📁 View All PDFs"):
            st.dataframe(df_all, use_container_width=True)

            st.download_button(
                "⬇️ Download All CSV",
                df_all.to_csv(index=False),
                "all_pdfs.csv"
            )

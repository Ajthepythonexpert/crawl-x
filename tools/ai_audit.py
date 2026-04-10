import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import google.generativeai as genai

# Import helpers
from core.utils import is_garbage_link, check_asset_health, get_image_details

INFO = {
    "title": "AI Audit",
    "icon": "🧠",
    "description": "Deep on-page analysis powered by Gemini Strategic Intelligence for BSH domains."
}

def render():
    st.markdown("""
    <div class="tool-header">
        <div class="tool-icon">🧠</div>
        <div>
            <div class="tool-title">CRAWL-X AI Audit</div>
            <div class="tool-sub">Deep Asset Inspection & Gemini Strategic Intelligence</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Sidebar
    with st.sidebar.expander("🔑 AI Authentication", expanded=True):
        user_api_key = st.text_input("Gemini API Key", type="password")
        if not user_api_key:
            st.warning("Enter API key to unlock AI Strategy.")

    # Inputs
    url_input = st.text_input("Target URL", value="https://www.bosch-home.com/za/en/services")
    target_kw = st.text_input("Target Keyword (Optional)")

    if st.button("🚀 START FULL AI AUDIT"):
        session = requests.Session()
        headers = {'User-Agent': 'CRAWL-X-Bot/1.0'}
        start_time = time.time()

        try:
            with st.spinner("CRAWL-X is performing a Deep Audit..."):
                response = session.get(url_input, timeout=15, headers=headers)
                latency = time.time() - start_time

                soup = BeautifulSoup(response.text, 'html.parser')
                html_content = response.text

                st.divider()

                tabs = st.tabs([
                    "📋 Diagnosis",
                    "🧠 AI Strategy",
                    "🔗 Links",
                    "📊 Density",
                    "🖼️ Image & Ghost Audit"
                ])

                # ---------------------------
                # 📋 Diagnosis
                # ---------------------------
                with tabs[0]:
                    title_str = soup.title.string.strip() if soup.title else "MISSING"
                    st.metric("Server Response", f"{latency:.2f}s")
                    st.markdown(f"**Title Tag:** `{title_str}`")

                    for h in ['h1', 'h2']:
                        for t in soup.find_all(h):
                            st.caption(f"**{h.upper()}**: {t.get_text().strip()}")

                # ---------------------------
                # 🧠 AI Strategy
                # ---------------------------
                with tabs[1]:
                    if not user_api_key:
                        st.info("AI Analysis Locked.")
                    else:
                        genai.configure(api_key=user_api_key)
                        model = genai.GenerativeModel("gemini-3-flash-preview")

                        prompt = f"""
                        URL: {url_input}
                        Target Keyword: {target_kw if target_kw else "Not provided"}

                        Perform an SEO audit and provide:
                        1. 3 critical issues
                        2. 3 quick wins
                        3. Content improvement suggestions
                        """

                        try:
                            response = model.generate_content(prompt)
                            st.info(response.text)
                        except Exception as ai_err:
                            st.error(f"AI Error: {ai_err}")

                # ---------------------------
                # 🔗 Links
                # ---------------------------
                with tabs[2]:
                    st.subheader("Broken Link Check")

                    links = [
                        urljoin(url_input, a.get('href', ''))
                        for a in soup.find_all('a')
                        if a.get('href') and not is_garbage_link(a.get('href'))
                    ]

                    # Remove duplicates but preserve order
                    unique_links = list(dict.fromkeys(links))[:20]

                    broken = []

                    with ThreadPoolExecutor(max_workers=5) as ex:
                        futures = {
                            ex.submit(check_asset_health, url, session): url
                            for url in unique_links
                        }

                        for f in as_completed(futures):
                            try:
                                is_err, res = f.result()
                                if is_err:
                                    broken.append({
                                        "URL": futures[f],
                                        "Error": res
                                    })
                            except Exception as e:
                                broken.append({
                                    "URL": futures[f],
                                    "Error": str(e)
                                })

                    df_broken = pd.DataFrame(broken)

                    if df_broken.empty:
                        st.success("No broken links in top 20.")
                    else:
                        st.dataframe(df_broken, use_container_width=True)

                # ---------------------------
                # 📊 Density (placeholder)
                # ---------------------------
                with tabs[3]:
                    st.info("Keyword Density module coming soon...")

                # ---------------------------
                # 🖼️ Image & Ghost Audit
                # ---------------------------
                with tabs[4]:

                    # IMAGE AUDIT
                    st.subheader("🖼️ Image Asset Audit")

                    img_list = []

                    for img in soup.find_all('img'):
                        try:
                            src = urljoin(url_input, img.get('src', ''))
                            size, res = get_image_details(src, session)

                            img_list.append({
                                "File": src.split('/')[-1],
                                "Size (KB)": round(size, 2),
                                "Status": "🚩 LARGE" if size > 1000 else "✅ OK"
                            })
                        except Exception:
                            continue

                    df_images = pd.DataFrame(img_list)

                    if df_images.empty:
                        st.info("No images found.")
                    else:
                        st.dataframe(df_images, use_container_width=True)

                    # GHOST AUDIT
                    st.subheader("👻 Ghost Image Audit")

                    ghosts = []

                    if "/.webp" in html_content or "/.jpg" in html_content:
                        ghosts.append({
                            "Type": "SYNTAX",
                            "Details": "Missing filename before extension"
                        })

                    df_ghosts = pd.DataFrame(ghosts)

                    if df_ghosts.empty:
                        st.success("No Ghost issues found.")
                    else:
                        st.dataframe(df_ghosts, use_container_width=True)

        except Exception as e:
            st.error(f"Audit failed: {e}")


if __name__ == "__main__":
    render()

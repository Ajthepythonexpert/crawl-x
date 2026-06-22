import streamlit as st
import sqlite3

# 📦 METADATA DECLARATION FOR THE DASHBOARD REGISTRY LOOP
INFO = {
    "title": "Product Delta Tracker",
    "icon": "📦",
    "description": "Monitor vanished or newly introduced product variants week-over-week across markets."
}

def render():
    st.title("📦 Product Delta Tracker")
    st.caption("Weekly defensive visibility system to detect unintended drop-offs from your regional storefront inventory.")

    # --- CONFIGURATION BOX ---
    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col1:
            sitemap_url = st.text_input("Sitemap URL Seed", value="https://www.bosch-home.com/za/sitemap.xml")
            country = st.text_input("Country Identifier (e.g., ZA, SG, UA)", value="ZA").upper().strip()
        with col2:
            brand = st.selectbox("Target Brand", ["BOSCH", "SIEMENS", "NEFF"])

    # --- TRIGGER RUN TRIGGER BUTTON PLACEHOLDER ---
    if st.button("🚀 INITIATE CURRENT WEEKLY INVENTORY SNAPSHOT", use_container_width=True):
        st.info(f"UI Layer verified! Ready to wire up the scraping engine for {brand} ({country}) in the final step.")

    st.divider()
    
    # --- COMPARATIVE INVENTORY VARIANCE ENGINE ---
    st.subheader("📊 Comparative Inventory Variance Engine")
    st.markdown("Select two distinct snapshot dates to inspect items that have been dropped or newly introduced.")
    
    # Inline localized database fetch loop to see historical dates safely
    dates = []
    try:
        conn = sqlite3.connect("database.db")
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT snapshot_date FROM product_snapshots WHERE country=? ORDER BY snapshot_date DESC", (country,))
        dates = [row[0] for row in cur.fetchall()]
        conn.close()
    except Exception as e:
        # If the table doesn't exist yet, we catch the exception so the page won't break
        pass

    # Render data controls based on how many dates are found
    if len(dates) >= 2:
        c1, c2 = st.columns(2)
        with c1:
            curr_week = st.selectbox("Baseline Run Date (Newer)", dates, index=0)
        with c2:
            prev_week = st.selectbox("Comparison Target Run Date (Older)", dates, index=1)
            
        st.success(f"📈 Database linked cleanly! Found {len(dates)} saved run snapshot records for country code '{country}'.")
    else:
        st.info(f"Awaiting historical data records for country code '{country}'. Once you run your first successful crawls across separate dates, this section will unlock to calculate product deltas.")

if __name__ == "__main__":
    render()

import streamlit as st
import os
import importlib.util
from auth.utils import create_user, verify_user
from analytics.db import init_db, get_conn

# ─── PAGE CONFIG ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CRAWL-X | BSH SEO Intelligence",
    page_icon="🕶️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── BSH CORPORATE GLOBAL CSS ─────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=Space+Mono&family=Syne:wght@700;800&display=swap');

:root {
    --bsh-orange: #E8491F;
    --bsh-orange-dim: #F26522;
    --bsh-bg: #F4F4F4;
    --bsh-text: #1A1A1A;
    --bsh-grey-border: #DDDDDD;
    --white: #FFFFFF;
}

/* Global App Container */
.stApp {
    background-color: var(--bsh-bg) !important;
    color: var(--bsh-text) !important;
    font-family: 'Inter', sans-serif;
}

[data-testid="stHeader"] { background: transparent !important; }

/* Sidebar Styling */
[data-testid="stSidebar"] { 
    background-color: var(--white) !important; 
    border-right: 1px solid var(--bsh-grey-border); 
}

.logo-text {
    font-family: 'Syne', sans-serif;
    font-weight: 800;
    font-size: 1.6rem;
    color: var(--bsh-orange);
    letter-spacing: -0.02em;
    margin-bottom: -5px;
}

/* Custom Tool Headers */
.tool-header {
    background: var(--white);
    border-left: 6px solid var(--bsh-orange);
    border-radius: 4px;
    padding: 1.5rem;
    margin-bottom: 2rem;
    box-shadow: 0 2px 10px rgba(0,0,0,0.05);
}

.tool-title {
    font-family: 'Syne', sans-serif;
    font-weight: 800;
    font-size: 1.8rem;
    color: var(--bsh-orange);
}

/* Standard BSH Buttons */
div.stButton > button {
    background-color: var(--bsh-orange) !important;
    color: var(--white) !important;
    border: none !important;
    border-radius: 4px !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 700 !important;
    width: 100%;
    transition: 0.3s all !important;
}

div.stButton > button:hover {
    background-color: var(--bsh-orange-dim) !important;
    box-shadow: 0 4px 15px rgba(232, 73, 31, 0.3) !important;
    transform: translateY(-1px);
}

/* Forms & Inputs */
.stTextInput input {
    border-radius: 4px !important;
}

/* Metrics */
[data-testid="stMetric"] {
    background: var(--white) !important;
    border: 1px solid var(--bsh-grey-border) !important;
    border-radius: 8px !important;
}

[data-testid="stMetricValue"] {
    color: var(--bsh-orange) !important;
    font-family: 'Space Mono', monospace !important;
}
</style>
""", unsafe_allow_html=True)

# ─── DATABASE & DIRECTORY INIT ────────────────────────────────────────────────
def ensure_dirs():
    for d in ["results", "temp"]:
        if not os.path.exists(d):
            os.makedirs(d)

def bootstrap_admin():
    """Ensures the BSH Master Admin exists for MA 2."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM users WHERE username=?", ("admin",))
    if not cur.fetchone():
        create_user("admin", "MA2AdminGBS")
    conn.close()

# Initialize core systems
init_db()
ensure_dirs()
bootstrap_admin()

# ─── AUTHENTICATION LOGIN PAGE ────────────────────────────────────────────────
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    _, col, _ = st.columns([1, 1.5, 1])
    with col:
        st.write("##")
        st.write("##")
        # Centered BSH Login Header
        st.markdown("<h1 style='text-align: center; color: #E8491F; font-family: Syne;'>CRAWL-X</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #666; margin-top: -15px;'>Enterprise SEO Intelligence Login</p>", unsafe_allow_html=True)
        
        with st.form("login_form"):
            user = st.text_input("Username")
            pw = st.text_input("Password", type="password")
            submit = st.form_submit_button("Access BSH Suite")
            
            if submit:
                if verify_user(user, pw):
                    st.session_state.authenticated = True
                    st.session_state.user_id = user
                    st.rerun()
                else:
                    st.error("Invalid Credentials. Access Denied.")
    st.stop()

# ─── SIDEBAR & NAVIGATION ─────────────────────────────────────────────────────
with st.sidebar:
    # Clean single-line logo
    st.markdown("<div class='logo-text'>CRAWL-X</div>", unsafe_allow_html=True)
    st.caption("BSH SEO Intelligence Suite")
    st.divider()

# Define Core Pages
home_page = st.Page("tools/home.py", title="Dashboard Home", icon="🏠", default=True)
history_page = st.Page("tools/job_history.py", title="Audit History", icon="📜")

# Auto-discovery for Tool Files in /tools/
seo_tools = []
tool_dir = "tools"
exclude_list = ["home.py", "job_history.py", "__init__.py"]

if os.path.exists(tool_dir):
    for file in sorted(os.listdir(tool_dir)):
        if file.endswith(".py") and file not in exclude_list:
            # Format filename 'bulk_url_opener.py' -> 'Bulk Url Opener'
            display_name = file.replace(".py", "").replace("_", " ").title()
            seo_tools.append(st.Page(os.path.join(tool_dir, file), title=display_name, icon="🛠️"))

# Create Navigation Structure
pg = st.navigation({
    "Main": [home_page, history_page],
    "CRAWL-X Tools": seo_tools
})

# Launch Application
pg.run()
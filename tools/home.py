import streamlit as st
import os
import importlib.util
from datetime import datetime

def get_all_tools():
    """Scans the tools folder and extracts INFO from each file."""
    tools_list = []
    tool_dir = "tools"
    exclude = ["home.py", "job_history.py", "__init__.py"]
    
    if os.path.exists(tool_dir):
        for file in sorted(os.listdir(tool_dir)):
            if file.endswith(".py") and file not in exclude:
                path = os.path.join(tool_dir, file)
                spec = importlib.util.spec_from_file_location(file[:-3], path)
                module = importlib.util.module_from_spec(spec)
                try:
                    spec.loader.exec_module(module)
                    info = getattr(module, "INFO", {
                        "title": file.replace(".py", "").replace("_", " ").title(),
                        "icon": "🛠️",
                        "description": "CRAWL-X Audit Tool."
                    })
                    info["filename"] = file
                    tools_list.append(info)
                except:
                    continue
    return tools_list

def render():
    # --- DATA PREP ---
    now = datetime.now().strftime("%d %b %Y")
    user_name = st.session_state.get("user_id", "Admin").upper()

    # ─── THE CSS: ZERO TOP MARGIN & SYMMETRICAL HERO ──────────────────────
    st.markdown(f"""
    <style>
    /* 1. CRITICAL: Kill Streamlit's default top padding for the whole app */
    .block-container {{
        padding-top: 0rem !important;
        padding-bottom: 0rem !important;
        margin-top: 0px !important;
    }}
    
    /* 2. Hide the header anchor to save more space */
    [data-testid="stHeader"] {{
        background: rgba(0,0,0,0);
        color: rgba(0,0,0,0);
    }}

    .top-header-bar {{
        display: flex;
        justify-content: flex-end;
        align-items: center;
        padding: 5px 0; /* Minimal padding for the Admin text */
        font-family: 'Inter', sans-serif;
        font-size: 0.65rem;
        color: #AAA;
        letter-spacing: 0.1em;
        margin-top: 0px;
    }}
    
    .status-pill {{
        background: rgba(40, 167, 69, 0.1);
        color: #28a745;
        padding: 2px 8px;
        border-radius: 12px;
        margin-left: 10px;
        font-weight: 700;
    }}

    /* 3. Balanced Hero Section */
    .hero-wrapper {{
        background: radial-gradient(circle at center, rgba(232, 73, 31, 0.04) 0%, transparent 70%);
        padding: 27px 0 27px; /* 55px total / 2 = 27.5px symmetry */
        text-align: center;
    }}
    
    .hero-title {{
        font-family: 'Syne', sans-serif;
        font-weight: 800;
        font-size: 2.8rem;
        color: #1A1A1A;
        letter-spacing: -0.04em;
        margin: 0;
        line-height: 1.1;
    }}
    .hero-title span {{ color: #E8491F; }}

    .tool-card {{
        background: #FFFFFF;
        padding: 20px 15px 15px;
        border-radius: 16px;
        border: 1px solid rgba(0,0,0,0.06);
        box-shadow: 0 4px 12px rgba(0,0,0,0.02);
        height: 180px;
        display: flex;
        flex-direction: column;
        align-items: center;
        text-align: center;
        transition: transform 0.3s ease;
    }}
    .tool-card:hover {{
        transform: translateY(-5px);
        border-color: #E8491F;
        box-shadow: 0 10px 20px rgba(232, 73, 31, 0.08);
    }}

    .card-icon {{ font-size: 2.2rem; margin-bottom: 8px; }}
    .card-title {{
        font-family: 'Syne', sans-serif;
        font-weight: 700;
        font-size: 0.85rem;
        text-transform: uppercase;
        color: #1A1A1A;
        line-height: 1.2;
        height: 2.4rem;
        display: flex;
        align-items: center;
        justify-content: center;
    }}
    .card-desc {{ 
        font-size: 0.72rem; 
        color: #888; 
        line-height: 1.3;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }}

    div.stButton > button {{
        background-color: transparent !important;
        color: #E8491F !important;
        border: 1.2px solid #E8491F !important;
        border-radius: 10px !important;
        font-size: 10px !important;
        font-weight: 800 !important;
        text-transform: uppercase !important;
        padding: 6px 12px !important;
        width: 100% !important;
        height: 34px !important;
        margin-top: 10px;
    }}
    div.stButton > button:hover {{
        background-color: #E8491F !important;
        color: white !important;
    }}
    </style>

    <div class="top-header-bar">
        {user_name} • {now} <span class="status-pill">LIVE</span>
    </div>

    <div class="hero-wrapper">
        <h1 class="hero-title">Crawl. Audit. <span>Dominate.</span></h1>
    </div>
    """, unsafe_allow_html=True)

    # ─── 4-COLUMN DENSE GRID ────────────────────────────────────────────────
    tools = get_all_tools()
    if tools:
        cols = st.columns(4)
        for idx, tool in enumerate(tools):
            col_idx = idx % 4
            with cols[col_idx]:
                st.markdown(f"""
                <div class="tool-card">
                    <div class="card-icon">{tool['icon']}</div>
                    <div class="card-title">{tool['title']}</div>
                    <div class="card-desc">{tool['description']}</div>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button(f" {tool['title']}", key=f"btn_{idx}", use_container_width=True):
                    st.switch_page(f"tools/{tool['filename']}")
    else:
        st.warning("No tool modules found.")

if __name__ == "__main__":
    render()

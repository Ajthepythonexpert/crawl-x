import streamlit as st
import os
import importlib.util
from datetime import datetime

def get_all_tools():
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
                except: continue
    return tools_list

def render():
    now = datetime.now().strftime("%d %b %Y")
    user_name = st.session_state.get("user_id", "Admin").upper()

    # ─── CLEAN SaaS CSS: NO BUTTONS, CLICKABLE CARDS ───────────────────────
    st.markdown(f"""
    <style>
    [data-testid="stVerticalBlock"] > div:first-child {{
        margin-top: -30px !important; 
    }}

    .top-header-bar {{
        display: flex;
        justify-content: flex-end;
        align-items: center;
        font-family: 'Inter', sans-serif;
        font-size: 0.65rem;
        color: #AAA;
        letter-spacing: 0.1em;
        margin-bottom: 10px;
    }}
    
    .status-pill {{
        background: rgba(40, 167, 69, 0.1);
        color: #28a745;
        padding: 2px 8px;
        border-radius: 12px;
        margin-left: 10px;
        font-weight: 700;
    }}

    .hero-wrapper {{
        background: radial-gradient(circle at center, rgba(232, 73, 31, 0.04) 0%, transparent 70%);
        padding: 5px 0 25px;
        text-align: center;
    }}
    
    .hero-title {{
        font-family: 'Syne', sans-serif;
        font-weight: 800;
        font-size: 2.8rem;
        color: #1A1A1A;
        letter-spacing: -0.04em;
        margin: 0;
    }}
    .hero-title span {{ color: #E8491F; }}

    /* The "Ghost Button" container that makes the card clickable */
    div.stButton {{
        position: relative;
        height: 200px; /* Matches card height */
        margin-top: -200px; /* Overlays the button on top of the card */
        opacity: 0; /* Makes the real button invisible */
        z-index: 10;
    }}
    
    div.stButton > button {{
        width: 100% !important;
        height: 200px !important;
        cursor: pointer !important;
    }}

    .tool-card {{
        background: #FFFFFF;
        padding: 25px 15px;
        border-radius: 20px;
        border: 1px solid rgba(0,0,0,0.06);
        box-shadow: 0 4px 12px rgba(0,0,0,0.02);
        height: 200px;
        display: flex;
        flex-direction: column;
        align-items: center;
        text-align: center;
        transition: all 0.3s ease;
        position: relative;
        z-index: 1;
    }}

    .tool-card:hover {{
        transform: translateY(-5px);
        border-color: #E8491F;
        box-shadow: 0 10px 30px rgba(232, 73, 31, 0.1);
    }}

    .card-icon {{ font-size: 2.5rem; margin-bottom: 10px; }}
    .card-title {{
        font-family: 'Syne', sans-serif;
        font-weight: 700;
        font-size: 0.9rem;
        text-transform: uppercase;
        color: #1A1A1A;
        margin-bottom: 8px;
    }}
    .card-desc {{ 
        font-size: 0.75rem; 
        color: #888; 
        line-height: 1.4;
    }}
    </style>

    <div class="top-header-bar">
        {user_name} • {now} <span class="status-pill">LIVE</span>
    </div>

    <div class="hero-wrapper">
        <h1 class="hero-title">Crawl. Audit. <span>Dominate.</span></h1>
    </div>
    """, unsafe_allow_html=True)

    # ─── 4-COLUMN INTERACTIVE GRID ──────────────────────────────────────────
    tools = get_all_tools()
    if tools:
        cols = st.columns(4)
        for idx, tool in enumerate(tools):
            col_idx = idx % 4
            with cols[col_idx]:
                # 1. The VISUAL CARD (Z-index 1)
                st.markdown(f"""
                <div class="tool-card">
                    <div class="card-icon">{tool['icon']}</div>
                    <div class="card-title">{tool['title']}</div>
                    <div class="card-desc">{tool['description']}</div>
                </div>
                """, unsafe_allow_html=True)
                
                # 2. The INVISIBLE OVERLAY BUTTON (Z-index 10)
                # This button covers the card area perfectly
                if st.button("", key=f"overlay_{idx}", help=f"Launch {tool['title']}"):
                    st.switch_page(f"tools/{tool['filename']}")
    else:
        st.warning("No tools detected.")

if __name__ == "__main__":
    render()

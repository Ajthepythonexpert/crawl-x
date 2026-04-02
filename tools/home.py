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

    # ─── HIGH-DENSITY SaaS CSS ──────────────────────────────────────────────
    st.markdown(f"""
    <style>
    /* 1. Header & Hero (Tighter Spacing) */
    .top-header-bar {{
        display: flex;
        justify-content: flex-end;
        align-items: center;
        padding: 0 0 10px 0;
        font-family: 'Inter', sans-serif;
        font-size: 0.65rem;
        color: #AAA;
        letter-spacing: 0.1em;
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
        padding: 10px 0 25px; /* Significantly reduced */
        text-align: center;
    }}
    .hero-title {{
        font-family: 'Syne', sans-serif;
        font-weight: 800;
        font-size: 2.8rem; /* Scaled down slightly */
        color: #1A1A1A;
        letter-spacing: -0.04em;
        margin: 0;
    }}
    .hero-title span {{ color: #E8491F; }}

    /* 2. Compact Grid Cards */
    .tool-card {{
        background: #FFFFFF;
        padding: 20px 15px 15px; /* Tighter padding */
        border-radius: 16px;
        border: 1px solid rgba(0,0,0,0.06);
        box-shadow: 0 2px 8px rgba(0,0,0,0.02);
        transition: all 0.3s ease;
        height: 180px; /* Locked height for density */
        display: flex;
        flex-direction: column;
        justify-content: flex-start;
        align-items: center;
        text-align: center;
        margin-bottom: 10px;
    }}
    .tool-card:hover {{
        transform: translateY(-4px);
        box-shadow: 0 12px 24px rgba(232, 73, 31, 0.08);
        border-color: rgba(232, 73, 31, 0.3);
    }}
    
    .card-icon {{ font-size: 2.2rem; margin-bottom: 8px; }}
    .card-title {{
        font-family: 'Syne', sans-serif;
        font-weight: 700;
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #1A1A1A;
        line-height: 1.2;
        height: 2rem; /* Keep titles uniform */
        display: flex;
        align-items: center;
    }}
    .card-desc {{ 
        font-size: 0.72rem; 
        color: #777; 
        line-height: 1.3; 
        margin-top: 5px;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }}

    /* 3. Sleek Action Buttons */
    div.stButton > button {{
        background-color: transparent !important;
        color: #E8491F !important;
        border: 1.2px solid #E8491F !important;
        border-radius: 8px !important;
        font-size: 9px !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
        padding: 5px 10px !important;
        height: 28px !important;
        margin-top: 10px;
        width: 100% !important;
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
                
                if st.button(f"Launch {idx}", key=f"btn_{idx}", use_container_width=True):
                    try: st.switch_page(f"tools/{tool['filename']}")
                    except: st.info(f"Navigating...")
    else:
        st.warning("No tools found.")

    st.markdown("""
    <div style="text-align:center; margin-top:3rem; padding:1.5rem 0; border-top:1px solid #EEE; color:#E8491F; font-weight:700; font-size:0.65rem; text-transform:uppercase; letter-spacing:0.1em;">
        Powered by CRAWL-X Engine | GBSMA2
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    render()

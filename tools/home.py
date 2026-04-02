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
    # --- DATA PREP ---
    now = datetime.now().strftime("%d %b %Y")
    user_name = st.session_state.get("user_id", "Admin").upper()

    st.markdown(f"""
    <style>
    /* 1. Header Bar (Top Right) */
    .top-header-bar {{
        display: flex;
        justify-content: flex-end;
        align-items: center;
        padding: 0 0 20px 0;
        font-family: 'Inter', sans-serif;
        font-size: 0.7rem;
        color: #AAA;
        letter-spacing: 0.1em;
        text-transform: uppercase;
    }}
    .status-pill {{
        background: rgba(40, 167, 69, 0.1);
        color: #28a745;
        padding: 2px 8px;
        border-radius: 12px;
        margin-left: 15px;
        font-weight: 700;
        display: flex;
        align-items: center;
    }}
    .dot {{ height: 6px; width: 6px; background: #28a745; border-radius: 50%; margin-right: 5px; }}

    /* 2. Focused Hero */
    .hero-wrapper {{
        background: radial-gradient(circle at center, rgba(232, 73, 31, 0.05) 0%, transparent 70%);
        padding: 40px 0 50px;
        text-align: center;
    }}
    .hero-title {{
        font-family: 'Syne', sans-serif;
        font-weight: 800;
        font-size: 3.8rem;
        color: #1A1A1A;
        letter-spacing: -0.04em;
        margin: 0;
    }}
    .hero-title span {{ color: #E8491F; }}

    /* 3. Refined Cards */
    .tool-card {{
        background: #FFFFFF;
        padding: 30px 20px 20px;
        border-radius: 20px;
        border: 1px solid rgba(0,0,0,0.06);
        box-shadow: 0 4px 12px rgba(0,0,0,0.02);
        transition: all 0.3s ease;
        height: 180px;
        display: flex;
        flex-direction: column;
        align-items: center;
        text-align: center;
        margin-bottom: 12px;
    }}
    .tool-card:hover {{
        transform: translateY(-5px);
        box-shadow: 0 15px 35px rgba(232, 73, 31, 0.1);
    }}
    .card-icon {{ font-size: 2.5rem; margin-bottom: 12px; }}
    .card-title {{
        font-family: 'Syne', sans-serif;
        font-weight: 700;
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: #1A1A1A;
    }}
    .card-desc {{ font-size: 0.75rem; color: #777; line-height: 1.4; margin-top: 8px; }}

    div.stButton > button {{
        background-color: transparent !important;
        color: #E8491F !important;
        border: 1.5px solid #E8491F !important;
        border-radius: 10px !important;
        font-size: 10px !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
    }}
    div.stButton > button:hover {{
        background-color: #E8491F !important;
        color: white !important;
    }}
    </style>

    <div class="top-header-bar">
        Welcome: {user_name} • {now}
        <div class="status-pill"><span class="dot"></span> LIVE</div>
    </div>

    <div class="hero-wrapper">
        <h1 class="hero-title">Crawl. Audit. <span>Dominate.</span></h1>
    </div>
    """, unsafe_allow_html=True)

    # --- DYNAMIC GRID ---
    tools = get_all_tools()
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
            if st.button(f"Open {tool['title']}", key=f"btn_{idx}", use_container_width=True):
                try: st.switch_page(f"tools/{tool['filename']}")
                except: st.info(f"Launching {tool['title']}...")

    st.markdown("""
    <div style="text-align:center; margin-top:5rem; padding:2rem 0; border-top:1px solid #EEE; color:#E8491F; font-weight:700; font-size:0.75rem; text-transform:uppercase; letter-spacing:0.1em;">
        Powered by CRAWL-X Engine | BSH Corporate Edition | GBSMA2
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    render()
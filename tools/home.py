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

    # ─── REFINED 3-COLUMN CSS ──────────────────────────────────────────────
    st.markdown(f"""
    <style>
    /* 1. Header Bar */
    .top-header-bar {{
        display: flex;
        justify-content: flex-end;
        align-items: center;
        padding: 0 0 10px 0;
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

    /* 2. Hero Section */
    .hero-wrapper {{
        background: radial-gradient(circle at center, rgba(232, 73, 31, 0.05) 0%, transparent 70%);
        padding: 20px 0 40px;
        text-align: center;
    }}
    .hero-title {{
        font-family: 'Syne', sans-serif;
        font-weight: 800;
        font-size: 3.5rem;
        color: #1A1A1A;
        letter-spacing: -0.04em;
        margin: 0;
    }}
    .hero-title span {{ color: #E8491F; }}

    /* 3. The Responsive Card (3-Column Optimization) */
    .tool-card {{
        background: #FFFFFF;
        padding: 30px 20px 20px;
        border-radius: 24px;
        border: 1px solid rgba(0,0,0,0.06);
        box-shadow: 0 4px 12px rgba(0,0,0,0.02);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        min-height: 240px; /* Increased height for better spacing */
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        align-items: center;
        text-align: center;
        margin-bottom: 15px;
    }}
    .tool-card:hover {{
        transform: translateY(-8px);
        box-shadow: 0 20px 40px rgba(232, 73, 31, 0.12);
        border-color: rgba(232, 73, 31, 0.3);
    }}
    
    .card-icon {{ font-size: 3rem; margin-bottom: 10px; }}
    .card-title {{
        font-family: 'Syne', sans-serif;
        font-weight: 700;
        font-size: 1rem;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: #1A1A1A;
        line-height: 1.2;
    }}
    .card-desc {{ 
        font-size: 0.8rem; 
        color: #777; 
        line-height: 1.5; 
        margin-top: 10px;
        flex-grow: 1;
    }}

    /* 4. Button Fix (No More Overflow) */
    div.stButton > button {{
        background-color: transparent !important;
        color: #E8491F !important;
        border: 1.8px solid #E8491F !important;
        border-radius: 12px !important;
        font-size: 10px !important;
        font-weight: 800 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.08em !important;
        padding: 10px 15px !important;
        width: 100% !important;
        transition: 0.3s all !important;
        margin-top: 15px;
        white-space: normal !important; /* Fix for long text */
        height: auto !important;
    }}
    div.stButton > button:hover {{
        background-color: #E8491F !important;
        color: white !important;
        box-shadow: 0 8px 20px rgba(232, 73, 31, 0.2) !important;
    }}
    </style>

    <div class="top-header-bar">
        USER: {user_name} • {now}
        <div class="status-pill"><span class="dot"></span> LIVE</div>
    </div>

    <div class="hero-wrapper">
        <h1 class="hero-title">Crawl. Audit. <span>Dominate.</span></h1>
    </div>
    """, unsafe_allow_html=True)

    # ─── DYNAMIC 3-COLUMN GRID ──────────────────────────────────────────────
    tools = get_all_tools()
    
    if tools:
        # Changed to 3 columns for better spacing
        cols = st.columns(3)
        for idx, tool in enumerate(tools):
            col_idx = idx % 3
            with cols[col_idx]:
                st.markdown(f"""
                <div class="tool-card">
                    <div>
                        <div class="card-icon">{tool['icon']}</div>
                        <div class="card-title">{tool['title']}</div>
                        <div class="card-desc">{tool['description']}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # The Button Logic
                if st.button(f"Open {tool['title']}", key=f"btn_{idx}", use_container_width=True):
                    try:
                        st.switch_page(f"tools/{tool['filename']}")
                    except:
                        st.info(f"Navigating to {tool['title']}...")
    else:
        st.warning("No tools found.")

    st.markdown("""
    <div style="text-align:center; margin-top:5rem; padding:2rem 0; border-top:1px solid #EEE; color:#E8491F; font-weight:700; font-size:0.75rem; text-transform:uppercase; letter-spacing:0.1em;">
        Powered by CRAWL-X Engine | BSH Corporate Edition | GBSMA2
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    render()

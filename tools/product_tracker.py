import streamlit as st

# 📦 BARE MINIMUM METADATA DECLARATION
INFO = {
    "title": "Product Delta Tracker",
    "icon": "📦",
    "description": "System connectivity validation demo test page."
}

def render():
    st.title("📦 Product Delta Tracker (Demo Mode)")
    st.write("---")
    st.success("🎉 If you can see this page, the file loading and registration framework is working perfectly!")
    
    st.info("Let's test basic slider interaction:")
    test_slider = st.slider("Adjust baseline index", 0, 100, 50)
    st.write(f"Active index value: **{test_slider}**")

# This fallback block ensures it can run independently if loaded directly
if __name__ == "__main__":
    render()

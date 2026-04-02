import streamlit as st
import pandas as pd
from analytics.db import get_conn

def render():
    st.markdown("## 📊 Analytics Dashboard")

    user_id = st.session_state.get("user_id", "admin")
    conn = get_conn()
    df = pd.read_sql_query("SELECT * FROM jobs WHERE user_id=?", conn, params=(user_id,))
    conn.close()

    if df.empty:
        st.info("Analytics will appear once you run your first tool!")
        return

    # Metrics
    total = len(df)
    completed = len(df[df["status"] == "completed"])
    success_rate = (completed / total * 100) if total > 0 else 0
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Audits", total)
    m2.metric("Success Rate", f"{success_rate:.1f}%")
    m3.metric("Tools Active", df['tool'].nunique())

    st.divider()

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Tool Usage")
        st.bar_chart(df['tool'].value_counts())
    with c2:
        st.subheader("Status Breakdown")
        st.pie_chart(df['status'].value_counts())
if __name__ == "__main__":
    render()
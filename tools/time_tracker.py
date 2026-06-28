import streamlit as st
import pandas as pd
from datetime import datetime

# --- Configuration & Setup ---
st.set_page_config(page_title="Team Time Tracker", page_icon="⏱️", layout="wide")
DEFAULT_NAMES = ["Arjun", "Jawahar", "Nupur", "Rashmi", "Rahul"]

# --- Password Protection Check ---
def check_password():
    """Returns True if the user entered the correct password."""
    # Check if the secret code is configured in Streamlit Secrets
    if "general" in st.secrets and "tool_secret_code" in st.secrets["general"]:
        expected_password = st.secrets["general"]["tool_secret_code"]
    else:
        st.error("🔑 Security configuration missing. Please add 'tool_secret_code' to secrets.")
        return False

    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if st.session_state.authenticated:
        return True

    # Show password entry form
    st.subheader("🔐 Restricted Access Tool")
    user_code = st.text_input("Enter the secret access code:", type="password")
    
    if st.button("Unlock Tool", type="primary"):
        if user_code == expected_password:
            st.session_state.authenticated = True
            st.success("Access Granted!")
            st.rerun()
        else:
            st.error("❌ Invalid secret code. Access denied.")
            
    return False

# Stop execution right here if password check fails
if check_password():

    # --- Database Connection ---
    # CRITICAL FIX: Removed url="sqlite:///..." to force it to use Secrets!
    conn = st.connection("time_tracker_db", type="sql")

    def init_db():
        """Creates the database table if it doesn't exist."""
        try:
            conn.query("SELECT 1 FROM work_logs LIMIT 1", ttl=0)
        except Exception:
            df = pd.DataFrame(columns=[
                "Date", "Name", "Start Time", "End Time", "Duration (Hours)", "Task Description"
            ])
            df.to_sql("work_logs", con=conn.engine, if_exists="replace", index=False)

    def load_data():
        """Loads all work logs from the SQL database."""
        try:
            df = conn.query("SELECT * FROM work_logs", ttl=0)
            return df
        except Exception:
            return pd.DataFrame()

    def save_entry(entry_dict):
        """Saves a new log entry directly to the SQL database."""
        df = pd.DataFrame([entry_dict])
        df.to_sql("work_logs", con=conn.engine, if_exists="append", index=False)
        st.cache_data.clear()

    # --- Session State Initialization ---
    if "is_working" not in st.session_state:
        st.session_state.is_working = False
    if "start_time" not in st.session_state:
        st.session_state.start_time = None
    if "pending_log" not in st.session_state:
        st.session_state.pending_log = None 

    init_db()

    # --- Application Header ---
    st.title("⏱️ Team Time Tracker")
    st.markdown("Select your name, start your work, and log your tasks.")
    
    if st.sidebar.button("🔒 Lock Tool"):
        st.session_state.authenticated = False
        st.rerun()

    # Create tabs for the app
    tab_logger, tab_dashboard = st.tabs(["📝 Log Work", "📊 Dashboard"])

    # ==========================================
    # TAB 1: LOG WORK
    # ==========================================
    with tab_logger:
        st.subheader("Time Logger")
        
        col1, col2 = st.columns([1, 2])
        with col1:
            selected_name = st.selectbox("Select your Name", DEFAULT_NAMES + ["Other..."])
            if selected_name == "Other...":
                user_name = st.text_input("Enter your name:")
            else:
                user_name = selected_name

        if user_name:
            if not st.session_state.is_working and st.session_state.pending_log is None:
                st.info(f"Welcome, {user_name}! Ready to start?")
                if st.button("▶️ Start Work", type="primary", use_container_width=True):
                    st.session_state.is_working = True
                    st.session_state.start_time = datetime.now()
                    st.rerun()

            elif st.session_state.is_working:
                start_str = st.session_state.start_time.strftime("%I:%M %p")
                st.success(f"👷 **{user_name}** is currently working. Started at: **{start_str}**")
                
                if st.button("⏹️ End Work", type="primary", use_container_width=True):
                    end_time = datetime.now()
                    duration = end_time - st.session_state.start_time
                    hours_worked = round(duration.total_seconds() / 3600, 2)
                    
                    st.session_state.pending_log = {
                        "Date": st.session_state.start_time.strftime("%Y-%m-%d"),
                        "Name": user_name,
                        "Start Time": st.session_state.start_time.strftime("%Y-%m-%d %H:%M:%S"),
                        "End Time": end_time.strftime("%Y-%m-%d %H:%M:%S"),
                        "Calculated Hours": hours_worked
                    }
                    st.session_state.is_working = False
                    st.session_state.start_time = None
                    st.rerun()

            elif st.session_state.pending_log is not None:
                st.warning("Work ended! Please review your hours and add a description.")
                
                with st.form("log_form"):
                    st.write(f"**Name:** {st.session_state.pending_log['Name']}")
                    
                    adjusted_hours = st.number_input(
                        "Adjust Hours (if needed):", 
                        value=float(st.session_state.pending_log["Calculated Hours"]), 
                        min_value=0.0, 
                        step=0.25
                    )
                    
                    task_description = st.text_area("What did you work on?", placeholder="E.g., Fixed bugs, meeting, project planning...")
                    
                    submit_log = st.form_submit_button("💾 Save Work Log")
                    
                    if submit_log:
                        if not task_description.strip():
                            st.error("Please enter a task description before saving.")
                        else:
                            final_entry = {
                                "Date": st.session_state.pending_log["Date"],
                                "Name": st.session_state.pending_log["Name"],
                                "Start Time": st.session_state.pending_log["Start Time"],
                                "End Time": st.session_state.pending_log["End Time"],
                                "Duration (Hours)": adjusted_hours,
                                "Task Description": task_description
                            }
                            
                            save_entry(final_entry)
                            st.session_state.pending_log = None
                            st.success("Log saved successfully!")
                            st.rerun()
                
            if st.button("Cancel & Discard Log"):
                st.session_state.pending_log = None
                st.rerun()
        else:
            st.warning("Please select or enter your name to begin.")

    # ==========================================
    # TAB 2: DASHBOARD
    # ==========================================
    with tab_dashboard:
        st.subheader("Analytics & Records")
        
        df = load_data()
        
        if df.empty:
            st.info("No work logs found. Start logging work to see data here.")
        else:
            df['Date'] = pd.to_datetime(df['Date'])
            df['Duration (Hours)'] = pd.to_numeric(df['Duration (Hours)'])
            df['Week'] = df['Date'].dt.strftime('%Y-W%U')
            df['Month'] = df['Date'].dt.strftime('%Y-%m')
            
            col_agg, col_filter = st.columns(2)
            with col_agg:
                view_type = st.radio("Group By:", ["Weekly", "Monthly"], horizontal=True)
            with col_filter:
                unique_names = df['Name'].unique()
                selected_names_filter = st.multiselect("Filter by Name:", unique_names, default=unique_names)

            filtered_df = df[df['Name'].isin(selected_names_filter)]
            
            if filtered_df.empty:
                st.warning("No data for the selected users.")
            else:
                if view_type == "Weekly":
                    agg_column = 'Week'
                else:
                    agg_column = 'Month'
                    
                summary = filtered_df.groupby([agg_column, 'Name'])['Duration (Hours)'].sum().reset_index()
                chart_data = summary.pivot(index=agg_column, columns='Name', values='Duration (Hours)').fillna(0)
                
                st.markdown(f"### Total Hours ({view_type})")
                st.bar_chart(chart_data)
                
                st.markdown("### Detailed Logs")
                display_df = filtered_df.drop(columns=['Week', 'Month']).sort_values(by="Date", ascending=False)
                st.dataframe(display_df, use_container_width=True, hide_index=True)
                
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download All Data as CSV",
                    data=csv,
                    file_name="team_work_logs.csv",
                    mime="text/csv",
                )

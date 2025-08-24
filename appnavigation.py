import streamlit as st

# Check authentication status - handle None values properly
user_info = st.session_state.get('user_info')
is_authenticated = ('auth_token' in st.session_state and 
                   'user_info' in st.session_state and 
                   user_info is not None and 
                   user_info.get('username'))

# Ensure session state keys are initialized
if "video_memories" not in st.session_state:
    st.session_state["video_memories"] = {}

# Conditional navigation based on authentication
if is_authenticated:
    # User is logged in - show main app pages
    home = st.Page("home.py", title="Home")
    stream_analysis = st.Page("stream_analysis.py", title="Stream Analysis")
    wait_list = st.Page("wait_list.py", title="Join Waiting List")
    contact = st.Page("contact.py", title="Contact Us")
    pg = st.navigation([home, stream_analysis, wait_list, contact])
else:
    # User is not logged in - show only login page
    login = st.Page("login.py", title="Login / Register")
    pg = st.navigation([login])

pg.run()

# Sidebar is now handled in home.py
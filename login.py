import streamlit as st
import requests
import os

st.set_page_config(page_title="Login | CCTV Chat", page_icon="🔒")

from config import Config

API_URL = Config.get_api_url()

# Set a flag to indicate we're on the login page
st.session_state['current_page'] = 'login'

# For Hugging Face deployment, show a different message
if API_URL is None:
    st.error("🚧 **Backend Setup Required** 🚧")
    st.markdown("""
    This application requires a backend server to be deployed separately.
    
    **For Local Development:**
    - Run `python backend.py` to start the backend server
    - Then run `streamlit run appnavigation.py` for the frontend
    
    **For Hugging Face Deployment:**
    - Deploy the backend to a service like Railway, Render, or Heroku
    - Update the API_URL in the code to point to your deployed backend
    - Set up environment variables for database and API keys
    """)
    st.stop()

st.markdown("""
<style>
.login-container {
    max-width: 400px;
    margin: 3em auto;
    padding: 2em 2.5em;
    background: #f8f9fa;
    border-radius: 16px;
    box-shadow: 0 2px 16px rgba(0,0,0,0.08);
}
.login-title {
    font-size: 2em;
    font-weight: 700;
    color: #2d3a4a;
    margin-bottom: 0.5em;
    text-align: center;
}
.stTextInput > div > input {
    font-size: 1.1em;
    padding: 0.7em;
}
.stButton > button {
    font-size: 1.1em;
    padding: 0.6em 1.5em;
    border-radius: 8px;
}
.switch-link {
    color: #1a73e8;
    cursor: pointer;
    text-decoration: underline;
    font-size: 1em;
    display: block;
    text-align: center;
    margin-top: 1em;
}
</style>
""", unsafe_allow_html=True)

if 'auth_mode' not in st.session_state:
    st.session_state['auth_mode'] = 'login'
if 'auth_token' not in st.session_state:
    st.session_state['auth_token'] = None
if 'user_info' not in st.session_state:
    st.session_state['user_info'] = None
if 'login_attempted' not in st.session_state:
    st.session_state['login_attempted'] = False

def switch_mode():
    st.session_state['auth_mode'] = 'register' if st.session_state['auth_mode'] == 'login' else 'login'

with st.container():
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    if st.session_state['auth_mode'] == 'login':
        st.markdown('<div class="login-title">Sign In to CCTV Chat</div>', unsafe_allow_html=True)
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Sign In", key="login_btn"):
            if not email or not password:
                st.error("Please enter both email and password.")
            else:
                st.session_state['login_attempted'] = True
                try:
                    resp = requests.post(f"{API_URL}/login", json={"email": email, "password": password}, timeout=10)
                    if resp.status_code == 200:
                        data = resp.json()
                        st.session_state['auth_token'] = resp.cookies.get('session')
                        # Create user_info object with the expected format
                        st.session_state['user_info'] = {
                            'id': data.get('user_id'),
                            'username': data.get('username'),
                            'email': email  # We have the email from the form
                        }
                        st.session_state['current_page'] = 'home'  # Set current page to home
                        st.success("Login successful! Redirecting...")
                        st.info(f"Debug: auth_token={st.session_state['auth_token']}, user_info={st.session_state['user_info']}")
                        st.rerun()
                    else:
                        st.error(resp.json().get('error', 'Login failed.'))
                        st.session_state['login_attempted'] = False
                except Exception as e:
                    st.error(f"Error: {e}")
                    st.session_state['login_attempted'] = False
        st.markdown('<span class="switch-link" onclick="window.location.reload()">Don\'t have an account? <b>Register</b></span>', unsafe_allow_html=True)
        if st.button("Switch to Register", key="switch_to_register"):
            switch_mode()
    else:
        st.markdown('<div class="login-title">Create Your CCTV Chat Account</div>', unsafe_allow_html=True)
        email = st.text_input("Email", key="register_email")
        username = st.text_input("Username", key="register_username")
        password = st.text_input("Password", type="password", key="register_password")
        if st.button("Register", key="register_btn"):
            if not email or not username or not password:
                st.error("Please fill in all fields.")
            else:
                try:
                    resp = requests.post(f"{API_URL}/register", json={"email": email, "username": username, "password": password}, timeout=10)
                    if resp.status_code == 201:
                        st.success("Registration successful! Please sign in.")
                        st.session_state['auth_mode'] = 'login'
                    else:
                        st.error(resp.json().get('error', 'Registration failed.'))
                except Exception as e:
                    st.error(f"Error: {e}")
        st.markdown('<span class="switch-link" onclick="window.location.reload()">Already have an account? <b>Sign In</b></span>', unsafe_allow_html=True)
        if st.button("Switch to Login", key="switch_to_login"):
            switch_mode()
    st.markdown('</div>', unsafe_allow_html=True) 
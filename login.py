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

# Initialize session state
if 'auth_mode' not in st.session_state:
    st.session_state['auth_mode'] = 'login'
if 'auth_token' not in st.session_state:
    st.session_state['auth_token'] = None
if 'user_info' not in st.session_state:
    st.session_state['user_info'] = None
if 'login_attempted' not in st.session_state:
    st.session_state['login_attempted'] = False
if 'force_rerun' not in st.session_state:
    st.session_state['force_rerun'] = False

def switch_to_register():
    st.session_state['auth_mode'] = 'register'
    st.session_state['force_rerun'] = True

def switch_to_login():
    st.session_state['auth_mode'] = 'login'
    st.session_state['force_rerun'] = True

# Handle force rerun
if st.session_state.get('force_rerun', False):
    st.session_state['force_rerun'] = False
    st.rerun()

with st.container():
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    
    if st.session_state['auth_mode'] == 'login':
        st.markdown('<div class="login-title">Sign In to CCTV Chat</div>', unsafe_allow_html=True)
        
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        
        col1, col2 = st.columns([1, 1])
        with col1:
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
                            st.rerun()
                        else:
                            st.error(resp.json().get('error', 'Login failed.'))
                            st.session_state['login_attempted'] = False
                    except Exception as e:
                        st.error(f"Error: {e}")
                        st.session_state['login_attempted'] = False
        
        with col2:
            if st.button("Switch to Register", key="switch_to_register", on_click=switch_to_register):
                pass
        
        st.markdown('<div style="text-align: center; margin-top: 1em; color: #666;">Don\'t have an account? Click "Switch to Register" above</div>', unsafe_allow_html=True)
        
    else:  # Register mode
        st.markdown('<div class="login-title">Create Your CCTV Chat Account</div>', unsafe_allow_html=True)
        
        email = st.text_input("Email", key="register_email")
        username = st.text_input("Username", key="register_username")
        password = st.text_input("Password", type="password", key="register_password")
        confirm_password = st.text_input("Confirm Password", type="password", key="confirm_password")
        
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Register", key="register_btn"):
                if not email or not username or not password or not confirm_password:
                    st.error("Please fill in all fields.")
                elif password != confirm_password:
                    st.error("Passwords do not match. Please try again.")
                elif len(password) < 6:
                    st.error("Password must be at least 6 characters long.")
                else:
                    try:
                        resp = requests.post(f"{API_URL}/register", json={"email": email, "username": username, "password": password}, timeout=10)
                        if resp.status_code == 201:
                            st.success("Registration successful! Please sign in.")
                            st.session_state['auth_mode'] = 'login'
                            st.rerun()
                        else:
                            st.error(resp.json().get('error', 'Registration failed.'))
                    except Exception as e:
                        st.error(f"Error: {e}")
        
        with col2:
            if st.button("Switch to Login", key="switch_to_login", on_click=switch_to_login):
                pass
        
        st.markdown('<div style="text-align: center; margin-top: 1em; color: #666;">Already have an account? Click "Switch to Login" above</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True) 
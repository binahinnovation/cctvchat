import streamlit as st
import os
import base64
import requests
import json
from PIL import Image
import time
from openai import OpenAI

st.set_page_config(
    page_title="Surveillance Chat | Summary of your CCTV Footage by AI",
    page_icon=""
)

from config import Config

API_URL = Config.get_api_url()

# Check if user is authenticated, but only if we're not on the login page
current_page = st.session_state.get('current_page', 'home')
user_info = st.session_state.get('user_info')

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

if current_page != 'login' and (not st.session_state.get('auth_token') or 
                               not st.session_state.get('user_info') or 
                               user_info is None or 
                               not user_info.get('username')):
    st.error("Please log in to access this page.")
    st.stop()

# Cache management
def get_cached_videos(params):
    """Get videos from cache or fetch from API"""
    cache_key = f"videos_{hash(str(params))}"
    cache_timeout = 300  # 5 minutes
    
    if 'video_cache' not in st.session_state:
        st.session_state['video_cache'] = {}
    
    cache = st.session_state['video_cache']
    current_time = time.time()
    
    # Check if cache is valid
    if cache_key in cache:
        cached_data, timestamp = cache[cache_key]
        if current_time - timestamp < cache_timeout:
            return cached_data
    
    # Fetch from API
    try:
        resp = requests.get(f"{API_URL}/videos", params=params, cookies={"session": st.session_state.get('auth_token')})
        if resp.status_code == 200:
            data = resp.json()
            # Cache the result
            cache[cache_key] = (data, current_time)
            return data
        else:
            return None
    except Exception:
        return None

def get_cached_chat_history(video_id):
    """Get chat history from cache or fetch from API"""
    cache_key = f"chat_history_{video_id}"
    cache_timeout = 300  # 5 minutes
    
    if 'chat_cache' not in st.session_state:
        st.session_state['chat_cache'] = {}
    
    cache = st.session_state['chat_cache']
    current_time = time.time()
    
    # Check if cache is valid
    if cache_key in cache:
        cached_data, timestamp = cache[cache_key]
        if current_time - timestamp < cache_timeout:
            return cached_data
    
    # Fetch from API
    try:
        resp = requests.get(f"{API_URL}/chat_history/{video_id}", cookies={"session": st.session_state.get('auth_token')})
        if resp.status_code == 200:
            data = resp.json()
            # Cache the result
            cache[cache_key] = (data, current_time)
            return data
        else:
            return None
    except Exception:
        return None

def invalidate_cache(cache_type=None):
    """Invalidate cache when data changes"""
    if cache_type == 'videos' or cache_type is None:
        if 'video_cache' in st.session_state:
            st.session_state['video_cache'] = {}
    if cache_type == 'chat' or cache_type is None:
        if 'chat_cache' in st.session_state:
            st.session_state['chat_cache'] = {}

# Notification system
def add_notification(message, notification_type="info"):
    """Add a notification to the session state"""
    if 'notifications' not in st.session_state:
        st.session_state['notifications'] = []
    
    notification = {
        'message': message,
        'type': notification_type,
        'timestamp': time.time(),
        'id': len(st.session_state['notifications']) + 1
    }
    st.session_state['notifications'].append(notification)

def display_notifications():
    """Display notifications in the sidebar"""
    if 'notifications' in st.session_state and st.session_state['notifications']:
        with st.sidebar:
            st.subheader("🔔 Recent Activity")
            
            # Show last 5 notifications
            recent_notifications = st.session_state['notifications'][-5:]
            
            for notification in recent_notifications:
                icon = "✅" if notification['type'] == 'success' else "❌" if notification['type'] == 'error' else "ℹ️"
                st.write(f"{icon} {notification['message']}")
            
            if len(st.session_state['notifications']) > 5:
                if st.button("Clear All Notifications", key="clear_notifications"):
                    st.session_state['notifications'] = []
                    st.rerun()

# Authentication check is already done at the top of the file

# Sidebar for user info and logout
with st.sidebar:
    st.title("🎥 CCTV Chat")
    user_info = st.session_state['user_info']
    st.write(f"👤 Welcome, {user_info.get('username', 'User')}!")
    st.write(f"📧 {user_info.get('email', '')}")
    
    # Display notifications
    display_notifications()
    
    # Profile editing section
    with st.expander("⚙️ Edit Profile"):
        st.subheader("Profile Settings")
        
        # Edit username
        new_username = st.text_input("Username", value=user_info.get('username', ''), key="edit_username")
        if st.button("Update Username", key="update_username_btn"):
            if new_username and new_username != user_info.get('username', ''):
                try:
                    resp = requests.post(f"{API_URL}/profile", json={"username": new_username}, cookies={"session": st.session_state.get('auth_token')})
                    if resp.status_code == 200:
                        st.session_state['user_info']['username'] = new_username
                        add_notification("Username updated successfully!", "success")
                        st.toast("Username updated successfully!", icon="✅")
                        st.rerun()
                    else:
                        add_notification("Username update failed.", "error")
                        st.toast(resp.json().get('error', 'Username update failed.'), icon="❌")
                except Exception as e:
                    add_notification(f"Error updating username: {e}", "error")
                    st.toast(f"Error: {e}", icon="❌")
        
        # Change password
        st.subheader("Change Password")
        current_password = st.text_input("Current Password", type="password", key="current_password")
        new_password = st.text_input("New Password", type="password", key="new_password")
        confirm_password = st.text_input("Confirm New Password", type="password", key="confirm_password")
        
        if st.button("Change Password", key="change_password_btn"):
            if not current_password or not new_password or not confirm_password:
                add_notification("Please fill in all password fields.", "error")
                st.toast("Please fill in all password fields.", icon="❌")
            elif new_password != confirm_password:
                add_notification("New passwords do not match.", "error")
                st.toast("New passwords do not match.", icon="❌")
            elif len(new_password) < 6:
                add_notification("Password must be at least 6 characters long.", "error")
                st.toast("Password must be at least 6 characters long.", icon="❌")
            else:
                try:
                    resp = requests.post(f"{API_URL}/profile/password", json={
                        "current_password": current_password,
                        "new_password": new_password
                    }, cookies={"session": st.session_state.get('auth_token')})
                    if resp.status_code == 200:
                        add_notification("Password changed successfully!", "success")
                        st.toast("Password changed successfully!", icon="✅")
                        # Clear password fields
                        st.session_state['current_password'] = ""
                        st.session_state['new_password'] = ""
                        st.session_state['confirm_password'] = ""
                        st.rerun()
                    else:
                        add_notification("Password change failed.", "error")
                        st.toast(resp.json().get('error', 'Password change failed.'), icon="❌")
                except Exception as e:
                    add_notification(f"Error changing password: {e}", "error")
                    st.toast(f"Error: {e}", icon="❌")
    
    # Logout button
    if st.button("🚪 Logout", key="logout_btn"):
        try:
            resp = requests.post(f"{API_URL}/logout", cookies={"session": st.session_state.get('auth_token')})
            if resp.status_code == 200:
                # Clear session state
                for key in ['auth_token', 'user_info']:
                    if key in st.session_state:
                        del st.session_state[key]
                add_notification("Logged out successfully!", "success")
                st.toast("Logged out successfully!", icon="✅")
                st.rerun()
            else:
                add_notification("Logout failed.", "error")
                st.toast("Logout failed.", icon="❌")
        except Exception as e:
            add_notification(f"Error during logout: {e}", "error")
            st.toast(f"Error during logout: {e}", icon="❌")
    
    st.divider()

# Hardcoded API key for testing
DASHSCOPE_API_KEY = "sk-1c0c9b47d8244a0484498296fb8d3f1c"

UPLOAD_FOLDER = 'upload'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize OpenAI client for DashScope (for small files)
client = OpenAI(
    api_key=DASHSCOPE_API_KEY,
    base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
)

# Create a container for the logo with responsive width
logo_container = st.container()
with logo_container:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image("static/surveillance.chat.png", caption="Summary of your CCTV Footage by AI.", use_container_width=True)
        
st.text("""Chat with your Security Camera using our AI Agent. The quickest way to review your security.""")
st.caption("""Even at x32 speed, reviewing 24 hours of surveillance footage will take about 45 minutes. Now you can simply ask!""")

# Model selection dropdown with current model as default
model_options = {
    "qwen-vl-max": "Qwen-VL Max (Current - Best for detailed analysis)",
    "qwen-vl-plus": "Qwen-VL Plus (Balanced performance)"
}

selected_model = st.selectbox(
    "Choose AI Model:",
    options=list(model_options.keys()),
    format_func=lambda x: model_options[x],
    index=0  # Default to qwen-vl-max (your current model)
)

# Fixed FPS setting (hidden from user, optimized for surveillance)
FIXED_FPS = 1  # Best balance for surveillance footage

# Sample video links for testing
SAMPLE_VIDEOS = [
    ("We Are Going On Bullrun", "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/WeAreGoingOnBullrun.mp4"),
    ("Subaru Outback On Street And Dirt", "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/SubaruOutbackOnStreetAndDirt.mp4"),
]

# Refined/predefined prompts for video analysis
PREDEFINED_PROMPTS = [
    "How many people are in the video?",
    "What happens at the end?",
    "Describe the main events in the video.",
    "Is there any suspicious activity?",
    "What vehicles appear in the video?",
    "What is the weather like in the video?",
    "Summarize the video in one sentence.",
    "Are there any animals in the video?",
    "What is the location or setting?",
    "What time of day does the video appear to be?"
]

# Input method selection
input_method = st.radio(
    "Choose input method:",
    ["Upload Video File", "Video URL"],
    horizontal=True
)

# Show sample video links for testing (only for Video URL input)
if input_method == "Video URL":
    st.markdown("**Sample Video URLs for Testing:**")
    for name, url in SAMPLE_VIDEOS:
        if st.button(f"Use: {name}"):
            st.session_state["video_url_input"] = url

# Get user question
st.markdown("**Choose a predefined question or type your own:**")
col_prompt, col_custom = st.columns([2, 3])

# If a predefined prompt is selected, set it as the value of the predefined question input (not the chat input)
def set_predefined_prompt():
    if (
        st.session_state.get("predefined_prompt_select")
        and st.session_state["predefined_prompt_select"] != "(Choose a prompt)"
    ):
        st.session_state["predefined_question_input"] = st.session_state["predefined_prompt_select"]

with col_prompt:
    st.selectbox(
        "Predefined Prompts:",
        ["(Choose a prompt)"] + PREDEFINED_PROMPTS,
        key="predefined_prompt_select",
        on_change=set_predefined_prompt
    )
with col_custom:
    question = st.text_input(
        "Ask Your CCTV (Type in your question or select a prompt)",
        key="predefined_question_input"
    )

# File uploader or URL input based on selection
uploaded_file = None
video_url = None

if input_method == "Upload Video File":
    st.markdown("<span style='color: #e67e22; font-weight: bold;'>Limit: 100MB per file • Formats: MP4, MOV, AVI, MKV, FLV, WMV</span>", unsafe_allow_html=True)
    uploaded_file = st.file_uploader(
        "Upload your surveillance video", 
        type=["mp4", "mov", "avi", "mkv", "flv", "wmv"],
        help="Limit: 100MB per file • Formats: MP4, MOV, AVI, MKV, FLV, WMV"
    )
    if uploaded_file is not None:
        if uploaded_file.size > 100 * 1024 * 1024:
            st.error("You cannot upload files larger than 100MB.")
        else:
            if st.button("Upload Video", key="upload_btn"):
                files = {"file": (uploaded_file.name, uploaded_file, uploaded_file.type)}
                try:
                    # Progress bar for upload
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    with st.spinner("Uploading video..."):
                        status_text.text("Preparing upload...")
                        progress_bar.progress(10)
                        
                        # Simulate progress for large files
                        if uploaded_file.size > 10 * 1024 * 1024:  # Files larger than 10MB
                            progress_bar.progress(25)
                            status_text.text("Uploading file...")
                            time.sleep(0.5)  # Simulate upload time
                            progress_bar.progress(50)
                            status_text.text("Processing video...")
                            time.sleep(0.5)
                            progress_bar.progress(75)
                            status_text.text("Finalizing...")
                        
                        resp = requests.post(f"{API_URL}/upload_video", files=files, cookies={"session": st.session_state.get('auth_token')})
                        
                        progress_bar.progress(100)
                        status_text.text("Upload complete!")
                        time.sleep(0.5)
                        
                    if resp.status_code == 201:
                        invalidate_cache('videos')  # Invalidate video cache
                        add_notification("Video uploaded successfully!", "success")
                        st.toast("Video uploaded successfully!", icon="✅")
                        st.rerun()
                    else:
                        add_notification("Upload failed.", "error")
                        st.toast(resp.json().get('error', 'Upload failed.'), icon="❌")
                except Exception as e:
                    add_notification(f"Error uploading video: {e}", "error")
                    st.toast(f"Error: {e}", icon="❌")
                finally:
                    # Clear progress indicators
                    progress_bar.empty()
                    status_text.empty()
else:
    st.markdown("<span style='color: #e67e22; font-weight: bold;'>Limit: 1GB per file (URL) • Formats: MP4, MOV, AVI, MKV, FLV, WMV</span>", unsafe_allow_html=True)
    video_url = st.text_input(
        "Enter video URL",
        value=st.session_state.get("video_url_input", ""),
        key="video_url_input",
        placeholder="https://example.com/video.mp4",
        help="Limit: 1GB per file (URL) • Formats: MP4, MOV, AVI, MKV, FLV, WMV"
    )
    video_name = st.text_input("Video Name", key="video_url_name")
    if st.button("Add Video by URL", key="add_url_btn"):
        if not video_url or not video_name:
            st.error("Please provide both a video URL and a name.")
        else:
            data = {"video_name": video_name, "video_type": "url", "file_path_or_url": video_url}
            try:
                resp = requests.post(f"{API_URL}/add_video", json=data, cookies={"session": st.session_state.get('auth_token')})
                if resp.status_code == 201:
                    invalidate_cache('videos')  # Invalidate video cache
                    add_notification("Video added successfully!", "success")
                    st.toast("Video added successfully!", icon="✅")
                    st.rerun()
                else:
                    add_notification("Add video failed.", "error")
                    st.toast(resp.json().get('error', 'Add video failed.'), icon="❌")
            except Exception as e:
                add_notification(f"Error adding video: {e}", "error")
                st.toast(f"Error: {e}", icon="❌")

# List user's videos
st.header("Your Videos")

# Video History Section
st.subheader("📹 Your Video History")

# Search and Filter Section
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    search_query = st.text_input("🔍 Search videos by name", placeholder="Enter video name...")
with col2:
    type_filter = st.selectbox("📁 Filter by type", ["All", "upload", "camera", "url"])
with col3:
    favorite_filter = st.selectbox("⭐ Filter by favorite", ["All", "Favorites", "Not Favorites"])

# Pagination controls
col1, col2 = st.columns([1, 1])
with col1:
    per_page = st.selectbox("Items per page", [5, 10, 20, 50], index=1)
with col2:
    current_page = st.number_input("Page", min_value=1, value=1, step=1)

# Build API parameters
params = {
    'page': current_page,
    'per_page': per_page
}
if search_query:
    params['search'] = search_query
if type_filter != "All":
    params['type'] = type_filter
if favorite_filter == "Favorites":
    params['favorite'] = 'true'
elif favorite_filter == "Not Favorites":
    params['favorite'] = 'false'

# Fetch videos with search/filter and pagination
try:
    data = get_cached_videos(params)
    if data:
        videos = data.get('videos', [])
        pagination = data.get('pagination', {})
        
        if not videos:
            st.info("No videos found matching your criteria.")
        else:
            st.write(f"Showing {len(videos)} of {pagination.get('total', 0)} video(s) (Page {pagination.get('page', 1)} of {pagination.get('pages', 1)})")
            
            # Pagination navigation
            if pagination.get('pages', 1) > 1:
                col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
                with col1:
                    if pagination.get('has_prev', False):
                        if st.button("← Previous", key="prev_page"):
                            st.session_state['current_page'] = current_page - 1
                            st.rerun()
                with col2:
                    st.write(f"Page {pagination.get('page', 1)}")
                with col3:
                    if pagination.get('has_next', False):
                        if st.button("Next →", key="next_page"):
                            st.session_state['current_page'] = current_page + 1
                            st.rerun()
                with col4:
                    if st.button("First", key="first_page"):
                        st.session_state['current_page'] = 1
                        st.rerun()
            
            for v in videos:
                # Sort videos: favorites first, then by upload date
                star_icon = "⭐" if v.get('is_favorite', False) else "☆"
                with st.expander(f"{star_icon} {v['video_name']} ({v['video_type']})"):
                    st.write(f"Uploaded: {v['upload_date']}")
                    st.write(f"Size: {v['file_size']} bytes")
                    st.write(f"Type: {v['video_type']}")
                    st.write(f"Source: {v['file_path_or_url']}")
                    # Video preview
                    if v['video_type'] == 'upload' and v['file_path_or_url']:
                        try:
                            st.video(v['file_path_or_url'])
                        except Exception:
                            st.info("Video preview not available.")
                    elif v['video_type'] == 'url' and v['file_path_or_url']:
                        try:
                            st.video(v['file_path_or_url'])
                        except Exception:
                            st.info("Video preview not available.")
                    elif v.get('thumbnail_path'):
                        st.image(v['thumbnail_path'], caption="Thumbnail")
                    # Toggle favorite
                    favorite_text = "Remove from Favorites" if v.get('is_favorite', False) else "Add to Favorites"
                    if st.button(favorite_text, key=f"favorite_{v['id']}"):
                        try:
                            resp = requests.post(f"{API_URL}/video/{v['id']}/favorite", cookies={"session": st.session_state.get('auth_token')})
                            if resp.status_code == 200:
                                invalidate_cache('videos')  # Invalidate cache
                                add_notification("Favorite status updated!", "success")
                                st.toast("Favorite status updated!", icon="✅")
                                st.rerun()
                            else:
                                st.error("Failed to update favorite status.")
                        except Exception as e:
                            st.error(f"Error updating favorite: {e}")
                    
                    # Rename video
                    new_name = st.text_input("Rename video", value=v['video_name'], key=f"rename_{v['id']}")
                    if new_name != v['video_name']:
                        if st.button("Save new name", key=f"save_rename_{v['id']}"):
                            try:
                                resp = requests.post(f"{API_URL}/video/{v['id']}/rename", 
                                                   json={"new_name": new_name}, 
                                                   cookies={"session": st.session_state.get('auth_token')})
                                if resp.status_code == 200:
                                    invalidate_cache('videos')
                                    add_notification("Video renamed successfully!", "success")
                                    st.toast("Video renamed successfully!", icon="✅")
                                    st.rerun()
                                else:
                                    st.error("Failed to rename video.")
                            except Exception as e:
                                st.error(f"Error renaming video: {e}")
                    
                    # Delete video
                    if st.button("Delete video", key=f"delete_{v['id']}", type="secondary"):
                        try:
                            resp = requests.delete(f"{API_URL}/video/{v['id']}", 
                                                cookies={"session": st.session_state.get('auth_token')})
                            if resp.status_code == 200:
                                invalidate_cache('videos')
                                add_notification("Video deleted successfully!", "success")
                                st.toast("Video deleted successfully!", icon="✅")
                                st.rerun()
                            else:
                                st.error("Failed to delete video.")
                        except Exception as e:
                            st.error(f"Error deleting video: {e}")
                    
                    # Chat history for this video
                    st.subheader("💬 Chat History")
                    chat_history = get_cached_chat_history(v['id'])
                    if chat_history:
                        for chat in chat_history:
                            with st.expander(f"Q: {chat['question']} - {chat['timestamp']}"):
                                st.write(f"**Question:** {chat['question']}")
                                st.write(f"**Answer:** {chat['answer']}")
                                st.write(f"**Timestamp:** {chat['timestamp']}")
                                
                                # Delete individual Q&A
                                if st.button("Delete this Q&A", key=f"delete_chat_{chat['id']}", type="secondary"):
                                    try:
                                        resp = requests.delete(f"{API_URL}/chat/{chat['id']}", 
                                                            cookies={"session": st.session_state.get('auth_token')})
                                        if resp.status_code == 200:
                                            invalidate_cache('chat_history')
                                            add_notification("Q&A deleted successfully!", "success")
                                            st.toast("Q&A deleted successfully!", icon="✅")
                                            st.rerun()
                                        else:
                                            st.error("Failed to delete Q&A.")
                                    except Exception as e:
                                        st.error(f"Error deleting Q&A: {e}")
                    else:
                        st.info("No chat history for this video.")
                    
                    # Ask new question about this video
                    st.subheader("🤖 Ask AI About This Video")
                    user_question = st.text_input(
                        "Ask Your CCTV (Type in your question or select a prompt)",
                        key=f"question_{v['id']}",
                        placeholder="What's happening in this video?"
                    )
                    
                    # Predefined prompts
                    predefined_prompts = [
                        "How many people are in this video?",
                        "What activities are happening?",
                        "Describe the main events in this video",
                        "Are there any unusual activities?",
                        "What objects or vehicles are visible?",
                        "Describe the environment and setting",
                        "What happens at the end of the video?",
                        "Are there any safety concerns visible?",
                        "What time of day does this appear to be?",
                        "Describe the overall mood or atmosphere"
                    ]
                    
                    selected_prompt = st.selectbox(
                        "Or choose a predefined prompt:",
                        ["Select a prompt..."] + predefined_prompts,
                        key=f"prompt_{v['id']}"
                    )
                    
                    if selected_prompt != "Select a prompt...":
                        user_question = selected_prompt
                        st.session_state[f"question_{v['id']}"] = user_question
                    
                    if st.button("Ask AI", key=f"ask_{v['id']}"):
                        if user_question:
                            with st.spinner("Analyzing video..."):
                                try:
                                    # Prepare the request
                                    request_data = {
                                        "video_id": v['id'],
                                        "question": user_question
                                    }
                                    
                                    resp = requests.post(f"{API_URL}/analyze_video", 
                                                       json=request_data,
                                                       cookies={"session": st.session_state.get('auth_token')})
                                    
                                    if resp.status_code == 200:
                                        result = resp.json()
                                        answer = result.get('answer', 'No answer received.')
                                        
                                        # Add to chat history
                                        chat_data = {
                                            "video_id": v['id'],
                                            "question": user_question,
                                            "answer": answer
                                        }
                                        
                                        chat_resp = requests.post(f"{API_URL}/add_chat", 
                                                                 json=chat_data,
                                                                 cookies={"session": st.session_state.get('auth_token')})
                                        
                                        if chat_resp.status_code == 200:
                                            invalidate_cache('chat_history')
                                            add_notification("Analysis completed!", "success")
                                            st.toast("Analysis completed!", icon="✅")
                                            st.rerun()
                                        else:
                                            st.error("Failed to save chat history.")
                                    else:
                                        st.error(f"Analysis failed: {resp.text}")
                                except Exception as e:
                                    st.error(f"Error analyzing video: {e}")
                        else:
                            st.warning("Please enter a question.")
    else:
        st.error("Failed to fetch videos.")
except Exception as e:
    st.error(f"Error loading videos: {e}")
    add_notification(f"Error loading videos: {e}", "error")


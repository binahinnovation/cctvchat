import streamlit as st
import cv2
import time
import tempfile
import os
import threading
import numpy as np

st.set_page_config(page_title="Video Stream Analysis", page_icon="📹")
st.title("Video Stream Analysis")

st.markdown("""
Easily connect to your IP cameras, preview live streams, and perform efficient frame sampling for advanced AI-powered surveillance analysis.
""")

# --- Camera Configuration (Simple Form with Optional Fields) ---
if "camera_configs" not in st.session_state:
    st.session_state["camera_configs"] = []

with st.expander("Add Camera"):
    cam_name = st.text_input("Camera Name", key="cam_name_input")
    cam_url = st.text_input("RTSP URL (if known)", key="cam_url_input")
    username = st.text_input("Username (optional)", key="cam_user_input")
    password = st.text_input("Password (optional)", type="password", key="cam_pass_input")
    port = st.text_input("Port (optional, default 554)", key="cam_port_input")
    if st.button("Add Camera"):
        # If RTSP URL is provided, use it directly
        if cam_url:
            url = cam_url
        else:
            # Build RTSP URL from components if possible
            if not username:
                username = ""
            if not password:
                password = ""
            if not port:
                port = "554"
            auth = f"{username}:{password}@" if username and password else (f"{username}@" if username else "")
            url = f"rtsp://{auth}{{CAMERA_IP}}:{port}"
        if cam_name and url:
            st.session_state["camera_configs"].append({
                "name": cam_name,
                "rtsp_url": url,
                "username": username,
                "password": password,
                "port": port
            })
            st.success(f"Added camera: {cam_name}")
            st.rerun()
        else:
            st.error("Please enter at least a name and RTSP URL or enough info to build one.")

# Show current cameras
if st.session_state["camera_configs"]:
    st.markdown("**Configured Cameras:**")
    for idx, cam in enumerate(st.session_state["camera_configs"]):
        st.write(f"{idx+1}. {cam['name']} - {cam['rtsp_url']}")
        if st.button(f"Remove", key=f"remove_cam_{idx}"):
            st.session_state["camera_configs"].pop(idx)
            st.rerun()
else:
    st.info("No cameras configured yet.")

# --- Camera Selection ---
camera_names = [c["name"] for c in st.session_state["camera_configs"]]
selected_camera = st.selectbox("Select Camera", camera_names) if camera_names else None
rtsp_url = None
if selected_camera:
    for c in st.session_state["camera_configs"]:
        if c["name"] == selected_camera:
            rtsp_url = c["rtsp_url"]
            break

# --- Hardcoded Sampling Parameters ---
sampling_rate = 1  # frames per second
batch_interval = 60  # seconds
st.markdown(f"**Sampling Rate:** {sampling_rate} fps (fixed)")
st.markdown(f"**Batch Interval:** {batch_interval} seconds (fixed)")

# --- Stream Preview Logic ---
def preview_stream(rtsp_url, seconds=5):
    with st.spinner("Previewing stream..."):
        cap = cv2.VideoCapture(rtsp_url)
        frames = []
        start = time.time()
        frame_placeholder = st.empty()
        while time.time() - start < seconds:
            ret, frame = cap.read()
            if not ret:
                break
            frames.append(frame)
            # Show the latest frame
            frame_placeholder.image(frame, channels="BGR", caption="Live Preview")
            time.sleep(1/10)  # Show at ~10 fps
        cap.release()
        if not frames:
            st.error("Could not retrieve frames from the camera. Check the RTSP URL and network.")

if rtsp_url:
    if st.button("Preview Stream"):
        preview_stream(rtsp_url)

# --- Stream Sampling Logic ---
run_stream = st.button("Start Sampling Stream", key="start_stream")
stop_stream = st.button("Stop Sampling", key="stop_stream")

if "stream_thread" not in st.session_state:
    st.session_state["stream_thread"] = None
# Ensure session state keys are initialized
if "stream_running" not in st.session_state:
    st.session_state["stream_running"] = False
if "sampled_frames" not in st.session_state:
    st.session_state["sampled_frames"] = []

# Helper function to sample frames in a thread
def stream_worker(rtsp_url, sampling_rate, batch_interval):
    cap = cv2.VideoCapture(rtsp_url)
    buffer = []
    start_time = time.time()
    while st.session_state["stream_running"]:
        ret, frame = cap.read()
        if not ret:
            time.sleep(1)
            continue
        now = time.time()
        if int(now * sampling_rate) % sampling_rate == 0:
            buffer.append(frame)
            # Show the latest frame in Streamlit
            st.session_state["sampled_frames"] = [frame]
        # Every batch_interval seconds, clear buffer (simulate batch analysis)
        if now - start_time >= batch_interval:
            # Here you would call your AI analysis function with the buffer
            # For now, just clear the buffer
            buffer.clear()
            start_time = now
        time.sleep(1.0 / sampling_rate)
    cap.release()

# Start/Stop logic
if run_stream and rtsp_url:
    if st.session_state["stream_thread"] is None or not st.session_state["stream_thread"].is_alive():
        st.session_state["stream_running"] = True
        st.session_state["stream_thread"] = threading.Thread(
            target=stream_worker,
            args=(rtsp_url, sampling_rate, batch_interval),
            daemon=True
        )
        st.session_state["stream_thread"].start()
        st.success("Started stream sampling!")
if stop_stream:
    st.session_state["stream_running"] = False
    st.success("Stopped stream sampling.")

# Display sampled frame
if st.session_state["sampled_frames"]:
    st.image(st.session_state["sampled_frames"][0], channels="BGR", caption="Latest Sampled Frame") 
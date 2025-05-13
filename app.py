import streamlit as st
import os
import subprocess
import threading
from datetime import datetime
import time

# Page configuration
st.set_page_config(
    page_title="YouTube Live Streaming Dashboard",
    page_icon="🎥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for styling
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(to bottom right, #0f172a, #1e293b);
        color: white;
    }
    .stButton>button {
        width: 100%;
        background-color: #4f46e5;
        color: white;
        border: none;
        padding: 0.5rem 1rem;
        border-radius: 0.375rem;
    }
    .stButton>button:hover {
        background-color: #4338ca;
    }
    .danger-button>button {
        background-color: #dc2626;
    }
    .danger-button>button:hover {
        background-color: #b91c1c;
    }
    .card {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 0.75rem;
        padding: 1.5rem;
        margin-bottom: 1rem;
    }
    .status-indicator {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        margin-right: 8px;
    }
    .status-offline {
        background-color: #6b7280;
    }
    .status-preparing {
        background-color: #fbbf24;
    }
    .status-live {
        background-color: #dc2626;
        animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.5; }
        100% { opacity: 1; }
    }
    .log-viewer {
        background-color: #0f172a;
        border: 1px solid #334155;
        border-radius: 0.5rem;
        padding: 1rem;
        font-family: monospace;
        height: 300px;
        overflow-y: auto;
        color: #e2e8f0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'streaming_status' not in st.session_state:
    st.session_state.streaming_status = 'offline'
if 'logs' not in st.session_state:
    st.session_state.logs = []
if 'ffmpeg_thread' not in st.session_state:
    st.session_state.ffmpeg_thread = None

def add_log(message):
    timestamp = datetime.now().strftime('%H:%M:%S')
    st.session_state.logs.append(f"[{timestamp}] {message}")

def run_ffmpeg(video_path, stream_key, is_shorts):
    st.session_state.streaming_status = 'preparing'
    add_log("Preparing stream...")
    time.sleep(2)  # Simulate connection delay
    
    output_url = f"rtmp://a.rtmp.youtube.com/live2/{stream_key}"
    scale = "scale=720:1280" if is_shorts else "scale=1920:1080"
    
    cmd = [
        "ffmpeg", "-re", "-stream_loop", "-1", "-i", video_path,
        "-c:v", "libx264", "-preset", "veryfast", "-b:v", "2500k",
        "-maxrate", "2500k", "-bufsize", "5000k",
        "-vf", scale,
        "-g", "60", "-keyint_min", "60",
        "-c:a", "aac", "-b:a", "128k",
        "-f", "flv", output_url
    ]
    
    add_log(f"Starting FFmpeg with configuration: {' '.join(cmd)}")
    st.session_state.streaming_status = 'live'
    
    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                add_log(output.strip())
    except Exception as e:
        add_log(f"Error: {str(e)}")
    finally:
        st.session_state.streaming_status = 'offline'
        add_log("Stream ended")

# Header
st.title("🎥 Live Streaming Dashboard")
st.markdown("---")

# Main content
col1, col2 = st.columns([1, 1])

with col1:
    # Video Selection Card
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Video Selection")
    
    # List available videos
    video_files = [f for f in os.listdir('.') if f.endswith(('.mp4', '.flv'))]
    selected_video = st.selectbox(
        "Choose an existing video",
        ["Select a video..."] + video_files,
        disabled=(st.session_state.streaming_status != 'offline')
    )
    
    st.markdown("### Or upload a new video:")
    uploaded_file = st.file_uploader(
        "Upload video file",
        type=['mp4', 'flv'],
        disabled=(st.session_state.streaming_status != 'offline')
    )
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Video Preview Card
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Stream Preview")
    if uploaded_file or (selected_video and selected_video != "Select a video..."):
        video_file = uploaded_file if uploaded_file else selected_video
        st.video(video_file)
    else:
        st.info("No video selected")
    
    is_shorts = st.checkbox(
        "Shorts Mode (9:16)",
        disabled=(st.session_state.streaming_status != 'offline')
    )
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    # Stream Configuration Card
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Stream Configuration")
    
    stream_key = st.text_input(
        "YouTube Stream Key",
        type="password",
        disabled=(st.session_state.streaming_status != 'offline')
    )
    
    col_date, col_time = st.columns(2)
    with col_date:
        scheduled_date = st.date_input(
            "Scheduled Date",
            disabled=(st.session_state.streaming_status != 'offline')
        )
    with col_time:
        scheduled_time = st.time_input(
            "Scheduled Time",
            disabled=(st.session_state.streaming_status != 'offline')
        )
    
    show_ads = st.checkbox("Show Advertisements", value=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Streaming Controls Card
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Streaming Controls")
    
    col_start, col_stop = st.columns(2)
    with col_start:
        if st.button(
            "Start Streaming",
            disabled=(
                st.session_state.streaming_status != 'offline' or
                not stream_key or
                (not uploaded_file and (not selected_video or selected_video == "Select a video..."))
            )
        ):
            video_path = uploaded_file.name if uploaded_file else selected_video
            st.session_state.ffmpeg_thread = threading.Thread(
                target=run_ffmpeg,
                args=(video_path, stream_key, is_shorts),
                daemon=True
            )
            st.session_state.ffmpeg_thread.start()
    
    with col_stop:
        stop_button = st.markdown(
            '<div class="danger-button">',
            unsafe_allow_html=True
        )
        if st.button(
            "Stop Streaming",
            disabled=(st.session_state.streaming_status == 'offline')
        ):
            os.system("pkill ffmpeg")
            st.session_state.streaming_status = 'offline'
            add_log("Stream stopped by user")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Stream Status
    status_color = {
        'offline': 'status-offline',
        'preparing': 'status-preparing',
        'live': 'status-live'
    }[st.session_state.streaming_status]
    
    st.markdown(f"""
        <p>Stream Status: 
            <span class="status-indicator {status_color}"></span>
            {st.session_state.streaming_status.title()}
        </p>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Stream Logs Card
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Stream Logs")
    st.markdown('<div class="log-viewer">', unsafe_allow_html=True)
    for log in st.session_state.logs[-20:]:
        st.text(log)
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# Show ads section if enabled
if show_ads:
    st.markdown("---")
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Sponsored Content")
    st.markdown("""
        <div style="background-color: #1e293b; padding: 2rem; border-radius: 0.5rem; text-align: center;">
            <p>Advertisement Space</p>
            <p style="font-size: 0.875rem; color: #64748b; margin-top: 0.5rem;">Ads would appear here</p>
        </div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

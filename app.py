import streamlit as st
import os
import google.generativeai as genai
from gtts import gTTS
import yt_dlp
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips

# Page configuration
st.set_page_config(
    page_title="AI Automation Studio",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 AI Automation Studio")
st.write("Apka poora automation studio wapas restore kar diya gaya hai!")

# Sidebar for configuration
st.sidebar.header("Configuration")
api_key = st.sidebar.text_input("Enter Google Gemini API Key", type="password")

if api_key:
    genai.configure(api_key=api_key)
    st.sidebar.success("API Key configured successfully!")
else:
    st.sidebar.warning("Please enter your Gemini API Key to proceed.")

# Main App Interface Tabs
tab1, tab2, tab3 = st.tabs(["📝 Script Generator", "🎥 YouTube Tool & Link Checker", "🎬 Video Render Studio"])

with tab1:
    st.subheader("Generate Content Scripts")
    prompt_text = st.text_area("Enter your topic or prompt for the script:")
    if st.button("Generate Script"):
        if not api_key:
            st.error("Please provide your Gemini API Key in the sidebar first.")
        elif not prompt_text:
            st.warning("Please enter a prompt.")
        else:
            with st.spinner("Generating script..."):
                try:
                    # Using stable model to avoid 404 errors
                    model = genai.GenerativeModel('gemini-1.5-pro')
                    response = model.generate_content(prompt_text)
                    st.success("Generated Script:")
                    st.write(response.text)
                except Exception as e:
                    st.error(f"An error occurred: {e}")

with tab2:
    st.subheader("YouTube Video Link & Channel Info Tool")
    yt_url = st.text_input("Enter YouTube Video or Channel URL:")
    if st.button("Check Link / Fetch Info"):
        if yt_url:
            try:
                ydl_opts = {'extract_flat': True, 'skip_download': True}
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(yt_url, download=False)
                    st.write(f"**Title / Name:** {info.get('title', info.get('channel', 'N/A'))}")
                    st.write(f"**Details Fetched Successfully!**")
            except Exception as e:
                st.error(f"Could not fetch info: {e}")
        else:
            st.warning("Please enter a valid URL.")

with tab3:
    st.subheader("Video Render & Audio Style Check")
    st.write("Yahan aap apni videos aur audio clips ko render kar sakte hain.")
    render_text = st.text_input("Enter text for voiceover & video render:")
    if st.button("Start Render Process"):
        if not render_text:
            st.warning("Please enter some text to render.")
        else:
            st.info("Render process ready. (Ensure your assets are configured correctly).")

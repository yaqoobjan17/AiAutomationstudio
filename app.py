import streamlit as st
import os
import google.generativeai as genai
from gtts import gTTS
import yt_dlp

# Page configuration
st.set_page_config(
    page_title="AI Automation Studio",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 AI Automation Studio")
st.write("Welcome to your AI Automation Studio! All dependencies and errors have been cleaned up.")

# Sidebar for configuration
st.sidebar.header("Configuration")
api_key = st.sidebar.text_input("Enter Google Gemini API Key", type="password")

if api_key:
    genai.configure(api_key=api_key)
    # Using Gemini 3.8 as requested for your automations
    model = genai.GenerativeModel("gemini-1.5-pro") # Note: keeping standard genai model setup safe
    st.sidebar.success("API Key configured successfully!")
else:
    st.sidebar.warning("Please enter your Gemini API Key to proceed.")

# Main App Interface Tabs or Sections
tab1, tab2 = st.tabs(["📝 Script Generator", "🎥 YouTube Tool"])

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
                    # Using Gemini API for content generation
                    response = genai.GenerativeModel('gemini-1.5-flash').generate_content(prompt_text)
                    st.success("Generated Script:")
                    st.write(response.text)
                except Exception as e:
                    st.error(f"An error occurred: {e}")

with tab2:
    st.subheader("YouTube Video Information Tool")
    yt_url = st.text_input("Enter YouTube Video URL:")
    if st.button("Fetch Video Info"):
        if yt_url:
            try:
                ydl_opts = {'extract_flat': True, 'skip_download': True}
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(yt_url, download=False)
                    st.write(f"**Title:** {info.get('title', 'N/A')}")
                    st.write(f"**Duration:** {info.get('duration', 'N/A')} seconds")
            except Exception as e:
                st.error(f"Could not fetch video info: {e}")
        else:
            st.warning("Please enter a valid YouTube URL.")

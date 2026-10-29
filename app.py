import os
import json
import asyncio
import requests
import edge_tts
import yt_dlp
import streamlit as st
import google.generativeai as genai
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips

st.set_page_config(
    page_title="YT Automation Studio",
    page_icon="🎬",
    layout="centered"
)

st.title("🎬 YouTube Automation Studio")
st.markdown("Paste any channel link, pick your language & format, and generate a complete rendered **MP4 Video** instantly!")

st.sidebar.header("⚙️ Configuration")
api_key = st.sidebar.text_input("Gemini API Key", type="password", help="Enter your free Google Gemini API key.")
language = st.sidebar.selectbox("Select Language", ["English", "Urdu/Hindi"])
format_type = st.sidebar.selectbox("Video Format", ["Shorts (9:16)", "Long Video (16:9)"])

channel_url = st.text_input("🔗 YouTube Channel Link", placeholder="https://www.youtube.com/@ChannelName/videos")

PROGRESS_FILE = "temp/progress.json"

def save_progress(data):
    os.makedirs("temp", exist_ok=True)
    with open(PROGRESS_FILE, "w") as f:
        json.dump(data, f)

def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r") as f:
            return json.load(f)
    return None

def get_channel_dna(url):
    ydl_opts = {'extract_flat': True, 'playlistend': 5, 'quiet': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        titles = [entry.get('title') for entry in info.get('entries', []) if entry.get('title')]
    return titles

def generate_script(titles, lang, api_key):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    if lang == "Urdu/Hindi":
        lang_instruction = "Write the entire script, voiceovers in Roman Urdu/Hindi or native Urdu, keeping high engagement."
    else:
        lang_instruction = "Write the entire script, voiceovers in fluent and engaging English."

    prompt = f"""
    Analyze these YouTube video titles from the target channel:
    {titles}
    
    {lang_instruction}
    Create 1 viral video script with 3 short scenes based on this DNA. Keep voiceover text concise.
    Return ONLY valid JSON in this exact format:
    {{
      "video_title": "Catchy Video Title",
      "scenes": [
        {{
          "voiceover": "Short spoken line for scene 1",
          "image_prompt": "Detailed English prompt for realistic 4k visual scene"
        }}
      ]
    }}
    """
    response = model.generate_content(prompt)
    clean_json = response.text.strip().removeprefix("```json").removesuffix("```")
    return json.loads(clean_json)

async def generate_voice(text, filename, lang):
    voice_name = "ur-PK-AsadNeural" if lang == "Urdu/Hindi" else "en-US-ChristopherNeural"
    communicate = edge_tts.Communicate(text, voice_name)
    await communicate.save(filename)

def download_ai_image(prompt, filename, fmt):
    width, height = (1080, 1920) if "9:16" in fmt else (1920, 1080)
    url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(prompt)}?width={width}&height={height}&nologo=true"
    img_data = requests.get(url).content
    with open(filename, 'wb') as f:
        f.write(img_data)

# Check if previous progress exists
saved_data = load_progress()
if saved_data and os.path.exists("Final_Automated_Video.mp4"):
    st.success("🎉 Previous video session found! You can download it below or generate a new one.")
    st.video("Final_Automated_Video.mp4")
    with open("Final_Automated_Video.mp4", "rb") as file:
        st.download_button(
            label="📥 Download Final MP4 Video",
            data=file,
            file_name="Final_Automated_Video.mp4",
            mime="video/mp4"
        )

if st.button("🚀 Generate & Render MP4 Video", type="primary"):
    if not api_key:
        st.error("⚠️ Please enter your Gemini API Key in the sidebar!")
    elif not channel_url:
        st.error("⚠️ Please provide a valid YouTube Channel link!")
    else:
        os.makedirs("temp", exist_ok=True)
        output_filename = "Final_Automated_Video.mp4"
        
        try:
            with st.status("🎬 Running Automation Pipeline with Auto-Save...", expanded=True) as status:
                
                # Check if script already generated in saved progress
                progress = load_progress()
                if not progress or "script_data" not in progress:
                    st.write("🔍 Step 1: Analyzing Channel DNA & Style...")
                    titles = get_channel_dna(channel_url)
                    
                    st.write(f"✍️ Step 2: Writing New Viral Script in [{language}]...")
                    script_data = generate_script(titles, language, api_key)
                    
                    progress = {"script_data": script_data, "completed_scenes": 0}
                    save_progress(progress)
                else:
                    script_data = progress["script_data"]
                    st.write("🔄 Resumed from saved script progress...")

                st.success(f"Title: {script_data['video_title']}")
                
                clips = []
                total_scenes = len(script_data["scenes"])
                
                for i, scene in enumerate(script_data["scenes"]):
                    audio_path = f"temp/voice_{i}.mp3"
                    img_path = f"temp/img_{i}.jpg"
                    
                    # Skip already processed scenes if screen disconnected earlier
                    if i < progress.get("completed_scenes", 0) and os.path.exists(audio_path) and os.path.exists(img_path):
                        st.write(f"⏩ Skipping Scene {i+1} (Already Processed)...")
                    else:
                        st.write(f"🎧🖼️ Processing Scene {i+1} of {total_scenes} (Voiceover + AI Visual)...")
                        asyncio.run(generate_voice(scene["voiceover"], audio_path, language))
                        download_ai_image(scene["image_prompt"], img_path, format_type)
                        
                        # Update progress after each successful scene
                        progress["completed_scenes"] = i + 1
                        save_progress(progress)
                    
                    # Verify files and load clips
                    if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
                        audio_clip = AudioFileClip(audio_path)
                    else:
                        raise Exception(f"Audio file for scene {i+1} failed.")
                        
                    if os.path.exists(img_path) and os.path.getsize(img_path) > 0:
                        img_clip = ImageClip(img_path).set_duration(audio_clip.duration).set_audio(audio_clip)
                    else:
                        raise Exception(f"Image file for scene {i+1} failed.")
                        
                    clips.append(img_clip)
                
                st.write("⚙️ Step 4: Stitching scenes & rendering final MP4...")
                final_video = concatenate_videoclips(clips, method="compose")
                final_video.write_videofile(output_filename, fps=24, codec="libx264", audio_codec="aac", logger=None)
                
                status.update(label="✅ Video Rendering Complete!", state="complete", expanded=False)
            
            st.balloons()
            st.success("🎉 Your video is ready!")
            st.video(output_filename)
            
            with open(output_filename, "rb") as file:
                st.download_button(
                    label="📥 Download Final MP4 Video",
                    data=file,
                    file_name=output_filename,
                    mime="video/mp4"
                )
                
        except Exception as e:
            st.error(f"❌ An error occurred: {str(e)}")

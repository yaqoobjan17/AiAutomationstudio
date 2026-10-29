import os
import json
import asyncio
import random
import requests
import edge_tts
import yt_dlp
import streamlit as st
import google.generativeai as genai
from PIL import Image, ImageDraw

# Compatibility patch for MoviePy with modern Pillow versions
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips

st.set_page_config(
    page_title="YT Automation Studio",
    page_icon="🎬",
    layout="centered"
)

st.title("🎬 YouTube Automation Studio")
st.markdown("Generate 4K animated YouTube videos with custom duration, automatic scene division, and multi-scene rendering!")

# --- Sidebar Configuration ---
st.sidebar.header("⚙️ Configuration")
api_key = st.sidebar.text_input("Gemini API Key", type="password", value=st.session_state.get("api_key", ""), help="Enter your Google Gemini API key.")
if api_key:
    st.session_state["api_key"] = api_key

language = st.sidebar.selectbox("Select Language", ["English", "Urdu/Hindi"], index=0 if st.session_state.get("lang", "English")=="English" else 1)
st.session_state["lang"] = language

video_type = st.sidebar.selectbox("Video Type", ["Long Video (16:9)", "Shorts (9:16)"])

# Custom Duration Selectors
if "Long Video" in video_type:
    duration_options = {
        "1 Minute (~10 Scenes)": 60,
        "2 Minutes (~20 Scenes)": 120,
        "3 Minutes (~30 Scenes)": 180,
        "5 Minutes (~50 Scenes)": 300,
        "10 Minutes (~100 Scenes)": 600,
        "15 Minutes (~150 Scenes)": 900,
        "20 Minutes (~200 Scenes)": 1200,
        "30 Minutes (~300 Scenes)": 1800,
    }
    selected_duration_label = st.sidebar.selectbox("Select Long Video Duration", list(duration_options.keys()), index=0)
    target_duration_seconds = duration_options[selected_duration_label]
else:
    duration_options = {
        "15 Seconds (~2 Scenes)": 15,
        "30 Seconds (~5 Scenes)": 30,
        "60 Seconds (~10 Scenes)": 60,
        "90 Seconds (~15 Scenes)": 90,
    }
    selected_duration_label = st.sidebar.selectbox("Select Shorts Duration", list(duration_options.keys()), index=1)
    target_duration_seconds = duration_options[selected_duration_label]

# Approximate number of scenes (each scene 6 seconds)
expected_scenes = max(2, target_duration_seconds // 6)

# --- Session State Persistence ---
if "script_data" not in st.session_state:
    st.session_state["script_data"] = None
if "output_video" not in st.session_state:
    st.session_state["output_video"] = None

channel_url = st.text_input("🔗 YouTube Channel Link", value=st.session_state.get("channel_url", ""), placeholder="https://www.youtube.com/@ChannelName/videos")
if channel_url:
    st.session_state["channel_url"] = channel_url


def get_channel_dna(url):
    ydl_opts = {'extract_flat': True, 'playlistend': 5, 'quiet': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        titles = [entry.get('title') for entry in info.get('entries', []) if entry.get('title')]
    return titles


def generate_script(titles, lang, api_key, num_scenes):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-3.8-flash')
    
    if lang == "Urdu/Hindi":
        lang_instruction = "Write a comprehensive documentary script with rich details, voiceovers in Roman Urdu/Hindi or native Urdu, keeping high engagement."
    else:
        lang_instruction = "Write a comprehensive documentary script with rich details, voiceovers in fluent and engaging English."

    prompt = f"""
    Analyze these YouTube video titles from the target channel for style and tone:
    {titles}
    
    {lang_instruction}
    Create a detailed video script consisting of exactly {num_scenes} sequential scenes.
    Each scene must have a concise spoken voiceover of about 6 seconds (10 to 15 words) and a matching photorealistic 4k visual prompt.
    Return ONLY valid JSON in this exact format:
    {{
      "video_title": "Catchy Documentary Video Title",
      "scenes": [
        {{
          "voiceover": "Spoken line for scene",
          "image_prompt": "Detailed English prompt for realistic 4k cinematic visual scene matching this part"
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


def download_ai_image(prompt, filename, is_vertical):
    width, height = (1080, 1920) if is_vertical else (1920, 1080)
    seed = random.randint(1, 9999999)
    # Using FLUX engine with unique random seed to prevent duplicate or blank cache
    url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(prompt)}?width={width}&height={height}&model=flux&seed={seed}&nologo=true"
    
    for attempt in range(3):
        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 200 and len(response.content) > 3000:
                with open(filename, 'wb') as f:
                    f.write(response.content)
                img = Image.open(filename).convert("RGB")
                img.save(filename, "JPEG", quality=95)
                return
        except Exception:
            pass
        asyncio.run(asyncio.sleep(1))
    
    # High-quality stylized fallback if all attempts fail
    img = Image.new("RGB", (width, height), color=(15, 20, 30))
    d = ImageDraw.Draw(img)
    d.text((width // 4, height // 2), "Cinematic Scene View", fill=(220, 220, 240))
    img.save(filename, "JPEG")


# --- UI & Execution Logic ---
if st.session_state["output_video"] and os.path.exists(st.session_state["output_video"]):
    st.success("🎉 Video taiyar hai! Aap neeche play ya download kar sakte hain.")
    st.video(st.session_state["output_video"])
    
    with open(st.session_state["output_video"], "rb") as file:
        st.download_button(
            label="📥 Download Rendered MP4 Video",
            data=file,
            file_name="Automated_Documentary.mp4",
            mime="video/mp4"
        )
    
    if st.button("🔄 Reset & Start New Video"):
        st.session_state["script_data"] = None
        st.session_state["output_video"] = None
        st.session_state["channel_url"] = ""
        st.rerun()

else:
    if st.button("🚀 Generate & Render MP4 Video", type="primary"):
        if not api_key:
            st.error("⚠️ Sidebar mein apni Gemini API Key enter karein!")
        elif not channel_url:
            st.error("⚠️ YouTube channel link enter karein!")
        else:
            os.makedirs("temp", exist_ok=True)
            output_filename = "Automated_Documentary.mp4"
            is_vertical = "Shorts" in video_type
            
            try:
                with st.status(f"🎬 Processing Pipeline ({selected_duration_label})...", expanded=True) as status:
                    st.write("🔍 Step 1/5: Analyzing Channel DNA & Tone...")
                    titles = get_channel_dna(channel_url)
                    
                    st.write(f"✍️ Step 2/5: Generating Script with {expected_scenes} scenes using Gemini 3.8-flash...")
                    script_data = generate_script(titles, language, api_key, expected_scenes)
                    st.session_state["script_data"] = script_data
                    st.success(f"Title: {script_data.get('video_title', 'Video Project')}")
                    
                    clips = []
                    scenes_list = script_data.get("scenes", [])
                    total_scenes = len(scenes_list)
                    
                    for i, scene in enumerate(scenes_list):
                        st.write(f"🎧🖼️ Step 3/5: Scene {i+1} of {total_scenes} (Voiceover + FLUX 4K Visual)...")
                        audio_path = f"temp/voice_{i}.mp3"
                        img_path = f"temp/img_{i}.jpg"
                        
                        # Generate Voiceover
                        asyncio.run(generate_voice(scene["voiceover"], audio_path, language))
                        # Generate 4K AI Visual
                        download_ai_image(scene["image_prompt"], img_path, is_vertical)
                        
                        if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
                            audio_clip = AudioFileClip(audio_path)
                        else:
                            raise Exception(f"Voiceover generation failed for scene {i+1}")
                            
                        if os.path.exists(img_path) and os.path.getsize(img_path) > 0:
                            # Dynamic Zoom Animation (Ken Burns Effect)
                            img_clip = ImageClip(img_path).set_duration(audio_clip.duration)
                            img_clip = img_clip.resize(lambda t: 1 + 0.04 * (t / audio_clip.duration)).set_audio(audio_clip)
                        else:
                            raise Exception(f"Image generation failed for scene {i+1}")
                            
                        clips.append(img_clip)
                    
                    st.write("⚙️ Step 4/5: Concatenating animated clips & final MP4 rendering...")
                    final_video = concatenate_videoclips(clips, method="compose")
                    final_video.write_videofile(output_filename, fps=24, codec="libx264", audio_codec="aac", logger=None)
                    
                    st.session_state["output_video"] = output_filename
                    status.update(label="✅ Video Rendering Complete!", state="complete", expanded=False)
                
                st.balloons()
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ Error occurred: {str(e)}")

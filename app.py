import os
import json
import time
import random
import asyncio
import requests
import edge_tts
import yt_dlp
import streamlit as st
import google.generativeai as genai
from PIL import Image

# Modern Pillow compatibility fix
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips

st.set_page_config(
    page_title="YT Automation Studio",
    page_icon="🎬",
    layout="centered"
)

st.title("🎬 YouTube Automation Studio")
st.markdown("Persistent 4K Automation: Real visuals guaranteed bina kisi blank black screen ke!")

WORKDIR = "project_cache"
os.makedirs(WORKDIR, exist_ok=True)
STATE_FILE = os.path.join(WORKDIR, "state.json")
SCRIPT_FILE = os.path.join(WORKDIR, "script.json")
OUTPUT_VIDEO = os.path.join(WORKDIR, "Final_Rendered_Video.mp4")

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_state(data):
    current = load_state()
    current.update(data)
    with open(STATE_FILE, "w") as f:
        json.dump(current, f)

state_data = load_state()

# --- Sidebar Configuration ---
st.sidebar.header("⚙️ Configuration")
default_api = state_data.get("api_key", "")
api_key = st.sidebar.text_input("Gemini API Key", type="password", value=default_api)
if api_key and api_key != default_api:
    save_state({"api_key": api_key})

language = st.sidebar.selectbox("Select Language", ["English", "Urdu/Hindi"], index=0 if state_data.get("language", "English") == "English" else 1)
save_state({"language": language})

video_type = st.sidebar.selectbox("Video Type", ["Long Video (16:9)", "Shorts (9:16)"], index=0 if "Long" in state_data.get("video_type", "Long") else 1)
save_state({"video_type": video_type})

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

expected_scenes = max(2, target_duration_seconds // 6)

def get_channel_dna(url):
    ydl_opts = {'extract_flat': True, 'playlistend': 5, 'quiet': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return [entry.get('title') for entry in info.get('entries', []) if entry.get('title')]

def generate_script(titles, lang, key, num_scenes):
    genai.configure(api_key=key)
    model = genai.GenerativeModel('gemini-3.8-flash')
    
    lang_instruction = "Write a comprehensive documentary script with rich details, voiceovers in Roman Urdu/Hindi or native Urdu, keeping high engagement." if lang == "Urdu/Hindi" else "Write a comprehensive documentary script with rich details, voiceovers in fluent and engaging English."

    prompt = f"""
    Analyze these YouTube video titles:
    {titles}
    
    {lang_instruction}
    Create a detailed video script consisting of exactly {num_scenes} sequential scenes.
    Each scene must have a concise spoken voiceover of about 6 seconds (10 to 15 words) and a matching photorealistic visual prompt.
    Return ONLY valid JSON in this exact format:
    {{
      "video_title": "Catchy Documentary Video Title",
      "scenes": [
        {{
          "voiceover": "Spoken line for scene",
          "image_prompt": "cinematic hyperrealistic 4k shot of classic luxury car"
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

def fetch_real_image(prompt, filename, is_vertical):
    w, h = (1080, 1920) if is_vertical else (1920, 1080)
    seed = random.randint(100, 999999)
    encoded_prompt = requests.utils.quote(prompt.replace('\n', ' ').strip())

    # Source 1: Pollinations Turbo/Flux with seed
    urls = [
        f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={w}&height={h}&seed={seed}&nologo=true",
        f"https://image.pollinations.ai/prompt/{requests.utils.quote('luxury classic vintage vehicle 4k hyperrealistic')}?width={w}&height={h}&seed={seed}&nologo=true",
        f"https://picsum.photos/{w}/{h}?random={seed}"
    ]

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    for url in urls:
        try:
            res = requests.get(url, headers=headers, timeout=25)
            if res.status_code == 200 and len(res.content) > 5000:
                with open(filename, 'wb') as f:
                    f.write(res.content)
                img = Image.open(filename).convert("RGB")
                img = img.resize((w, h), Image.Resampling.LANCZOS)
                img.save(filename, "JPEG", quality=95)
                return True
        except Exception:
            continue
        time.sleep(1)

    return False

# --- App Interface ---
channel_url = st.text_input("🔗 YouTube Channel Link", value=state_data.get("channel_url", ""), placeholder="https://www.youtube.com/@ChannelName/videos")
if channel_url and channel_url != state_data.get("channel_url", ""):
    save_state({"channel_url": channel_url})

if os.path.exists(OUTPUT_VIDEO) and os.path.getsize(OUTPUT_VIDEO) > 0:
    st.success("🎉 Video taiyar ho chuki hai! Neeche se download karein.")
    st.video(OUTPUT_VIDEO)
    
    with open(OUTPUT_VIDEO, "rb") as file:
        st.download_button(
            label="📥 Download Rendered MP4 Video",
            data=file,
            file_name="Automated_Documentary.mp4",
            mime="video/mp4"
        )
    
    if st.button("🔄 Start New Video (Clean Setup)"):
        for f in os.listdir(WORKDIR):
            if f != "state.json":
                try:
                    os.remove(os.path.join(WORKDIR, f))
                except Exception:
                    pass
        current = load_state()
        current.pop("channel_url", None)
        with open(STATE_FILE, "w") as f:
            json.dump(current, f)
        st.rerun()

else:
    btn_label = "▶️ Resume / Run Automation Pipeline" if os.path.exists(SCRIPT_FILE) else "🚀 Generate & Render MP4 Video"
    
    if st.button(btn_label, type="primary"):
        active_key = api_key or state_data.get("api_key")
        active_url = channel_url or state_data.get("channel_url")
        
        if not active_key:
            st.error("⚠️ Pehle Sidebar mein Gemini API Key enter karein!")
        elif not active_url:
            st.error("⚠️ YouTube channel link enter karein!")
        else:
            is_vertical = "Shorts" in video_type
            
            with st.status(f"🎬 Processing Pipeline ({selected_duration_label})...", expanded=True) as status:
                if os.path.exists(SCRIPT_FILE):
                    st.write("📂 Saved script mil gayi hai! Gemini API call skip kar di gayi hai.")
                    with open(SCRIPT_FILE, "r") as f:
                        script_data = json.load(f)
                else:
                    st.write("🔍 Step 1/5: Analyzing Channel DNA...")
                    titles = get_channel_dna(active_url)
                    
                    st.write(f"✍️ Step 2/5: Generating Script ({expected_scenes} scenes) via Gemini 3.8-flash...")
                    script_data = generate_script(titles, language, active_key, expected_scenes)
                    with open(SCRIPT_FILE, "w") as f:
                        json.dump(script_data, f)
                        
                st.success(f"Title: {script_data.get('video_title', 'Video Project')}")
                
                scenes_list = script_data.get("scenes", [])
                total_scenes = len(scenes_list)
                clips = []
                
                for i, scene in enumerate(scenes_list):
                    audio_path = os.path.join(WORKDIR, f"voice_{i}.mp3")
                    img_path = os.path.join(WORKDIR, f"img_{i}.jpg")
                    
                    if not (os.path.exists(audio_path) and os.path.getsize(audio_path) > 0):
                        st.write(f"🎧 Voiceover {i+1} of {total_scenes}...")
                        asyncio.run(generate_voice(scene["voiceover"], audio_path, language))
                        
                    if not (os.path.exists(img_path) and os.path.getsize(img_path) > 1000):
                        st.write(f"🖼️ Downloading Real 4K Visual {i+1} of {total_scenes}...")
                        fetch_real_image(scene["image_prompt"], img_path, is_vertical)
                        
                    audio_clip = AudioFileClip(audio_path)
                    img_clip = ImageClip(img_path).set_duration(audio_clip.duration).set_audio(audio_clip)
                    clips.append(img_clip)
                    
                st.write("⚙️ Step 4/5: Stitching scenes & rendering final MP4 (MoviePy)...")
                final_video = concatenate_videoclips(clips, method="compose")
                final_video.write_videofile(
                    OUTPUT_VIDEO,
                    fps=24,
                    codec="libx264",
                    audio_codec="aac",
                    temp_audiofile=os.path.join(WORKDIR, "temp-audio.m4a"),
                    remove_temp=True,
                    logger=None
                )
                
                status.update(label="✅ Video Rendering Complete!", state="complete", expanded=False)
                st.balloons()
                st.rerun()

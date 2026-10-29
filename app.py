import os
import json
import asyncio
import requests
import edge_tts
import yt_dlp
import streamlit as st
import google.generativeai as genai
from PIL import Image, ImageDraw
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips

st.set_page_config(
    page_title="YT Automation Studio",
    page_icon="🎬",
    layout="centered"
)

st.title("🎬 YouTube Automation Studio")
st.markdown("Generate professional long-form automated videos with multiple fast-paced scenes and animated zoom visuals!")

st.sidebar.header("⚙️ Configuration")
api_key = st.sidebar.text_input("Gemini API Key", type="password", help="Enter your free Google Gemini API key.")
language = st.sidebar.selectbox("Select Language", ["English", "Urdu/Hindi"])
format_type = st.sidebar.selectbox("Video Format", ["Shorts (9:16)", "Long Video (16:9)"])

channel_url = st.text_input("🔗 YouTube Channel Link", placeholder="https://www.youtube.com/@ChannelName/videos")

def get_channel_dna(url):
    ydl_opts = {'extract_flat': True, 'playlistend': 5, 'quiet': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        titles = [entry.get('title') for entry in info.get('entries', []) if entry.get('title')]
    return titles

def generate_script(titles, lang, api_key):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-3.8-flash')
    
    if lang == "Urdu/Hindi":
        lang_instruction = "Write a comprehensive, deep-dive video script with rich details, voiceovers in Roman Urdu/Hindi or native Urdu, keeping high engagement."
    else:
        lang_instruction = "Write a comprehensive, deep-dive video script with rich details, voiceovers in fluent and engaging English."

    prompt = f"""
    Analyze these YouTube video titles from the target channel for style and tone:
    {titles}
    
    {lang_instruction}
    Create a detailed long-form video script consisting of 15 to 20 short, fast-paced scenes (each scene should have a concise 5 to 7 second voiceover line) based on this DNA.
    Return ONLY valid JSON in this exact format:
    {{
      "video_title": "Catchy Documentary Video Title",
      "scenes": [
        {{
          "voiceover": "Short spoken line for scene",
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

def download_ai_image(prompt, filename, fmt):
    width, height = (1080, 1920) if "9:16" in fmt else (1920, 1080)
    url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(prompt)}?width={width}&height={height}&nologo=true"
    
    try:
        response = requests.get(url, timeout=20)
        if response.status_code == 200 and len(response.content) > 1000:
            with open(filename, 'wb' ) as f:
                f.write(response.content)
            img = Image.open(filename).convert("RGB")
            img.save(filename, "JPEG")
            return
    except Exception:
        pass
    
    # Fallback image
    img = Image.new("RGB", (width, height), color=(15, 15, 25))
    d = ImageDraw.Draw(img)
    d.text((width//10, height//2), "Cinematic Visual", fill=(255, 255, 255))
    img.save(filename, "JPEG")

if st.button("🚀 Generate Animated Long-Form Video", type="primary"):
    if not api_key:
        st.error("⚠️ Please enter your Gemini API Key in the sidebar!")
    elif not channel_url:
        st.error("⚠️ Please provide a valid YouTube Channel link!")
    else:
        os.makedirs("temp", exist_ok=True)
        output_filename = "Final_Animated_Documentary.mp4"
        
        try:
            with st.status("🎬 Running Advanced Automation Pipeline...", expanded=True) as status:
                st.write("🔍 Step 1/5: Analyzing Channel DNA & Style...")
                titles = get_channel_dna(channel_url)
                
                st.write(f"✍️ Step 2/5: Writing Multi-Scene Script (15+ Scenes) in [{language}]...")
                script_data = generate_script(titles, language, api_key)
                st.success(f"Title: {script_data['video_title']}")
                
                clips = []
                total_scenes = len(script_data["scenes"])
                
                for i, scene in enumerate(script_data["scenes"]):
                    st.write(f"🎧🖼️ Step 3/5: Processing Scene {i+1} of {total_scenes} (Voice + Animated Visual)...")
                    audio_path = f"temp/voice_{i}.mp3"
                    img_path = f"temp/img_{i}.jpg"
                    
                    asyncio.run(generate_voice(scene["voiceover"], audio_path, language))
                    download_ai_image(scene["image_prompt"], img_path, format_type)
                    
                    if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
                        audio_clip = AudioFileClip(audio_path)
                    else:
                        raise Exception(f"Audio file for scene {i+1} failed.")
                        
                    if os.path.exists(img_path) and os.path.getsize(img_path) > 0:
                        # Create Image clip with smooth zoom animation effect (Ken Burns style)
                        img_clip = ImageClip(img_path).set_duration(audio_clip.duration)
                        # Smooth zoom-in over time
                        img_clip = img_clip.resize(lambda t: 1 + 0.04 * (t / audio_clip.duration)).set_audio(audio_clip)
                    else:
                        raise Exception(f"Image file for scene {i+1} failed.")
                        
                    clips.append(img_clip)
                
                st.write("⚙️ Step 4/5: Stitching all animated scenes & rendering final MP4...")
                final_video = concatenate_videoclips(clips, method="compose")
                final_video.write_videofile(output_filename, fps=24, codec="libx264", audio_codec="aac", logger=None)
                
                status.update(label="✅ Video Rendering Complete!", state="complete", expanded=False)
            
            st.balloons()
            st.success("🎉 Aapki animated documentary video taiyar hai!")
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

import streamlit as st
import yt_dlp
import google.generativeai as genai

st.set_page_config(
    page_title="YouTube Channel DNA & Title Generator",
    page_icon="🔥",
    layout="centered"
)

st.title("🔥 YouTube Viral Title Generator")
st.markdown("Competitor channel ka link lagayein aur unke style DNA ke mutabiq **15–20 High-CTR Viral Titles** hasil karein.")

# Sidebar Configuration
st.sidebar.header("⚙️ Settings")
api_key = st.sidebar.text_input("Gemini API Key", type="password", help="Enter your Google Gemini API key.")

channel_url = st.text_input("🔗 Competitor YouTube Channel Link", placeholder="https://www.youtube.com/@ChannelName/videos")

def get_channel_dna(url):
    ydl_opts = {
        'extract_flat': True,
        'playlistend': 10,
        'quiet': True
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        titles = [entry.get('title') for entry in info.get('entries', []) if entry.get('title')]
    return titles

def generate_viral_titles(titles, api_key):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-3.8-flash')
    
    prompt = f"""
    You are an expert YouTube title strategist specializing in automotive and high-retention viral content.
    
    Analyze these successful video titles from a competitor channel to extract their exact Title DNA (emojis, capitalization, price tags, emotional triggers, curiosity hooks, year tags, vs comparisons):
    {titles}
    
    Based strictly on this channel's formula, generate 20 BRAND NEW, unique, and high-CTR viral video title ideas for this niche.
    
    Requirements:
    - Match the exact tone, style, and formatting (caps, emojis, urgency, shock-value) of the sample titles.
    - Provide exactly 20 numbered titles.
    - Do not add explanations or intros, just output the numbered list of 20 titles.
    """
    
    response = model.generate_content(prompt)
    return response.text.strip()

if st.button("🚀 Analyze Channel DNA & Generate Titles", type="primary"):
    if not api_key:
        st.error("⚠️ Sidebar mein apni Gemini API Key enter karein!")
    elif not channel_url:
        st.error("⚠️ YouTube channel link enter karein!")
    else:
        try:
            with st.spinner("🔍 Channel DNA analyze kiya ja raha hai aur viral titles generate ho rahe hain..."):
                recent_titles = get_channel_dna(channel_url)
                
                if not recent_titles:
                    st.error("❌ Channel se titles fetch nahi ho sake. Link check karein.")
                else:
                    st.subheader("📊 Analyzed Competitor Titles:")
                    for t in recent_titles[:5]:
                        st.caption(f"• {t}")
                        
                    titles_output = generate_viral_titles(recent_titles, api_key)
                    
                    st.success("✅ 20 High-CTR Viral Titles Taiyar Hain!")
                    st.markdown(titles_output)
                    
                    # Copy / Download helper
                    st.download_button(
                        label="📥 Download Titles (TXT)",
                        data=titles_output,
                        file_name="Viral_YouTube_Titles.txt",
                        mime="text/plain"
                    )
                    
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")

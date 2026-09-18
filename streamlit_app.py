import streamlit as st
import os
import time
import asyncio
import edge_tts
import ffmpeg
from google import genai

API_KEYS = st.secrets.get("GEMINI_API_KEYS", "").split(",")
if not API_KEYS or API_KEYS[0] == "":
    API_KEYS = [st.secrets.get("GEMINI_API_KEY", "")]

LANGUAGE = "Myanmar"
MODEL = "gemini-3.6-flash"


class KeyManager:
    def __init__(self, keys):
        self.keys = [k.strip() for k in keys if k.strip()]
        self.current_index = 0
        self.exhausted = set()

    def get_client(self):
        if len(self.exhausted) >= len(self.keys):
            self.exhausted.clear()
            self.current_index = 0
        return genai.Client(api_key=self.keys[self.current_index])

    def rotate(self):
        self.exhausted.add(self.current_index)
        for i in range(len(self.keys)):
            nxt = (self.current_index + 1 + i) % len(self.keys)
            if nxt not in self.exhausted:
                self.current_index = nxt
                return True
        return False

    def remaining(self):
        return len(self.keys) - len(self.exhausted)
      

def call_gemini(contents, km):
    attempts = 0
    while attempts < len(km.keys) * 3:
        if km.remaining() == 0:
            km.exhausted.clear()
            km.current_index = 0
        client = km.get_client()
        try:
            return client.models.generate_content(model=MODEL, contents=contents)
        except Exception as e:
            err = str(e)
            if "429" in err or "RESOURCE_EXHAUSTED" in err:
                km.rotate()
                attempts += 1
            elif "503" in err or "UNAVAILABLE" in err:
                time.sleep(3)
                attempts += 1
            else:
                raise e
    raise Exception("Retry ကုန်ပါပြီ။")


def run_tts(text, output_path):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(
            edge_tts.Communicate(text, 'my-MM-ThihaNeural').save(output_path)
        )
    finally:
        loop.close()
      

st.set_page_config(page_title="🎬 Movie Recap Generator", page_icon="🎬")
st.title("🎬 Movie Recap Generator")
st.write("ဗီဒီယို upload တင်ပြီး မြန်မာလို Recap ဖန်တီးပါ")

video_file = st.file_uploader("📹 ဗီဒီယို Upload", type=["mp4", "mov", "avi", "mkv"])

if video_file is not None:
    if st.button("🚀 Generate Recap", type="primary"):
        km = KeyManager(API_KEYS)

        with st.spinner("ဗီဒီယို စစ်ဆေးနေသည်..."):
            video_filename = "input_video.mp4"
            with open(video_filename, "wb") as f:
                f.write(video_file.read())
            probe = ffmpeg.probe(video_filename)
            video_duration = float(probe['format']['duration'])
            st.write(f"📹 အရှည်: {video_duration:.2f} စက္ကန့်")

        with st.spinner("Gemini → Script ရေးနေသည်..."):
            client = km.get_client()
            gfile = client.files.upload(file=video_filename)
            while gfile.state.name == "PROCESSING":
                time.sleep(3)
                gfile = client.files.get(name=gfile.name)
            prompt = (
                f"Watch this video carefully and write a clear, continuous movie recap script "
                f"in {LANGUAGE} language for audio narration that matches the length of the video. "
                f"Return plain speech text only without markdown titles."
            )
            response = call_gemini([gfile, prompt], km)
            script = response.text.strip()
            st.write(f"✅ Script ({len(script)} စာလုံး)")

        with st.spinner("🎙️ အသံဖိုင် ဖန်တီးနေသည်..."):
            audio_path = "recap_voice.mp3"
            run_tts(script, audio_path)
            audio_dur = float(ffmpeg.probe(audio_path)['format']['duration'])
            tempo = max(0.5, min(2.0, audio_dur / video_duration))

        with st.spinner("🎬 Recap Video Render..."):
            final_path = "final_recap.mp4"
            input_video = ffmpeg.input(video_filename)
            input_audio = ffmpeg.input(audio_path).audio.filter('atempo', tempo)
            stream = ffmpeg.output(
                input_video.video, input_audio, final_path,
                vcodec='libx264', acodec='aac'
            )
            ffmpeg.run(stream, overwrite_output=True)

        st.success("✅ ပြီးပါပြီ!")
        st.video(final_path)

        with open(final_path, "rb") as f:
            st.download_button("📥 Recap Video Download", f, file_name="final_recap.mp4")

        with st.expander("📝 Script"):
            st.text(script)

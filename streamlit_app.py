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

    def info(self):
        return f"Key [{self.current_index + 1}/{len(self.keys)}]"

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
    max_total = len(km.keys) * 3

    while attempts < max_total:
        if km.remaining() == 0:
            km.exhausted.clear()
            km.current_index = 0

        client = km.get_client()
        try:
            return client.models.generate_content(model=MODEL, contents=contents)
        except Exception as e:
            err = str(e)
            if "429" in err or "RESOURCE_EXHAUSTED" in err:
                if not km.rotate():
                    km.exhausted.clear()
                attempts += 1
            elif "503" in err or "UNAVAILABLE" in err:
                time.sleep(3)
                attempts += 1
            elif "401" in err or "403" in err:
                if not km.rotate():
                    km.exhausted.clear()
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
      

# ===== Streamlit UI =====
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
            recap_path = "recap_no_subs.mp4"
            input_video = ffmpeg.input(video_filename)
            input_audio = ffmpeg.input(audio_path).audio.filter('atempo', tempo)
            stream = ffmpeg.output(
                input_video.video, input_audio, recap_path,
                vcodec='libx264', acodec='aac'
            )
            ffmpeg.run(stream, overwrite_output=True)

        with st.spinner("📝 SRT ဖန်တီးနေသည်..."):
            afile = client.files.upload(file=audio_path)
            while afile.state.name == "PROCESSING":
                time.sleep(3)
                afile = client.files.get(name=afile.name)

            srt_prompt = (
                "Listen to this audio. Generate SRT subtitle in Myanmar Unicode (မြန်မာစာ).\n"
                "RULES:\n"
                "1. Format: number, timestamp (HH:MM:SS,mmm --> HH:MM:SS,mmm), text\n"
                "2. Millisecond precision\n"
                "3. Max 40 chars per line\n"
                "4. Myanmar Unicode ONLY\n"
                "5. Return ONLY raw SRT. No markdown."
            )
            srt_response = call_gemini([afile, srt_prompt], km)
            srt_content = srt_response.text.strip()
            if srt_content.startswith("```"):
                lines = [l for l in srt_content.split("\n") if not l.strip().startswith("```")]
                srt_content = "\n".join(lines).strip()

            srt_path = "recap_subtitle.srt"
            with open(srt_path, "w", encoding="utf-8") as f:
                f.write(srt_content)

        with st.spinner("🎨 Subtitles ထည့်နေသည်..."):
            final_path = "final_recap_with_subs.mp4"
            try:
                input_video = ffmpeg.input(recap_path)
                stream = ffmpeg.output(
                    input_video.video.filter(
                        'subtitles', srt_path,
                        force_style='FontName=Noto Sans Myanmar,FontSize=18,'
                                    'PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,'
                                    'BorderStyle=1,Outline=2,Shadow=1'
                    ),
                    input_video.audio,
                    final_path,
                    vcodec='libx264', acodec='copy'
                )
                ffmpeg.run(stream, overwrite_output=True)
            except Exception as e:
                st.warning(f"Subtitle error: {e}")
                final_path = recap_path

        st.success("✅ ပြီးပါပြီ!")
        st.video(final_path)

        with open(final_path, "rb") as f:
            st.download_button("📥 Recap Video Download", f, file_name="final_recap.mp4")

        with open(srt_path, "rb") as f:
            st.download_button("📥 SRT Download", f, file_name="recap_subtitle.srt")

        with st.expander("📝 Script"):
            st.text(script)

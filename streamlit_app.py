import streamlit as st
import os
import re
import time
import ffmpeg
import shutil
import subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import cv2
from gradio_client import Client, handle_file

# ============================================================
# Config
# ============================================================
VOXCPM_SPACES = [
    {"name": "Primary — VoxCPM Demo", "space": "openbmb/VoxCPM-Demo", "type": "demo"},
    {"name": "Fallback — Burmese TTS", "space": "hgghfhjfhjguyjf/Voxcpm-Burmese-Tts", "type": "burmese"},
]

PASSWORD = "voxcpm2026"
FONT_FILE = "MyanmarPadaung.ttf"

DEFAULT_SUB_POSITION = "center"
DEFAULT_FONT_SIZE = 30
DEFAULT_BLUR_HEIGHT = 100
DEFAULT_BLUR_ALPHA = 100

# ============================================================
# Page Config
# ============================================================
st.set_page_config(
    page_title="VoxCPM2 Movie Recap",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============================================================
# Custom CSS
# ============================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;900&display=swap');
    * { font-family: 'Inter', 'Pyidaungsu', 'Myanmar Text', sans-serif; }
    .stApp {
        background: radial-gradient(circle at 20% 20%, #1a1a3e 0%, #0a0a1f 50%, #000000 100%);
        color: #ffffff;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .hero-container {
        text-align: center;
        padding: 40px 20px 20px 20px;
    }
    .hero-title {
        font-size: 3rem;
        font-weight: 900;
        background: linear-gradient(135deg, #ff6b9d 0%, #c66bff 50%, #6ba8ff 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin: 0;
        letter-spacing: -2px;
        line-height: 1.1;
        filter: drop-shadow(0 0 30px rgba(198, 107, 255, 0.4));
    }
    .hero-sub {
        color: #8888aa;
        font-size: 1.05rem;
        margin-top: 12px;
        letter-spacing: 0.5px;
    }
    .hero-line {
        width: 100px;
        height: 3px;
        background: linear-gradient(90deg, transparent, #c66bff, transparent);
        margin: 20px auto 0 auto;
        border-radius: 3px;
    }
    .status-row {
        display: flex;
        justify-content: center;
        gap: 12px;
        flex-wrap: wrap;
        margin: 25px 0;
    }
    .status-pill {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 8px 18px;
        border-radius: 50px;
        font-size: 0.82rem;
        font-weight: 600;
        color: #ccccdd;
        display: inline-flex;
        align-items: center;
        gap: 6px;
        transition: all 0.3s;
    }
    .status-pill:hover {
        border-color: rgba(198, 107, 255, 0.5);
        box-shadow: 0 0 20px rgba(198, 107, 255, 0.3);
    }
    .status-pill.green { border-color: rgba(56, 239, 125, 0.4); color: #38ef7d; }
    .status-pill.red { border-color: rgba(235, 51, 73, 0.4); color: #eb3349; }
    .status-pill.purple { border-color: rgba(198, 107, 255, 0.4); color: #c66bff; }
    .status-pill.orange { border-color: rgba(242, 153, 74, 0.4); color: #f2994a; }
    .step-card {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 20px;
        padding: 24px 28px;
        margin: 20px 0;
        position: relative;
        overflow: hidden;
        transition: all 0.4s;
    }
    .step-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 4px;
        height: 100%;
        background: linear-gradient(180deg, #ff6b9d, #c66bff, #6ba8ff);
        border-radius: 4px;
    }
    .step-card:hover {
        border-color: rgba(198, 107, 255, 0.3);
        box-shadow: 0 20px 60px rgba(198, 107, 255, 0.15);
        transform: translateY(-2px);
    }
    .step-num {
        display: inline-block;
        width: 42px;
        height: 42px;
        background: linear-gradient(135deg, #ff6b9d, #c66bff);
        border-radius: 12px;
        text-align: center;
        line-height: 42px;
        font-size: 1.2rem;
        font-weight: 800;
        color: white;
        margin-right: 12px;
        box-shadow: 0 6px 20px rgba(198, 107, 255, 0.4);
    }
    .step-title {
        font-size: 1.3rem;
        font-weight: 700;
        color: #ffffff;
        display: inline-block;
        vertical-align: middle;
    }
    .glass-info {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.1), rgba(198, 107, 255, 0.08));
        backdrop-filter: blur(10px);
        border: 1px solid rgba(198, 107, 255, 0.2);
        border-radius: 16px;
        padding: 18px 22px;
        margin: 15px 0;
        color: #d0d0e0;
        font-size: 0.95rem;
        line-height: 1.6;
    }
    .glass-info a {
        color: #c66bff !important;
        font-weight: 600;
        text-decoration: none;
    }
    .metric-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
        gap: 12px;
        margin: 15px 0;
    }
    .metric-tile {
        background: rgba(255, 255, 255, 0.04);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 14px;
        padding: 16px 12px;
        text-align: center;
        transition: all 0.3s;
    }
    .metric-tile:hover {
        background: rgba(198, 107, 255, 0.08);
        border-color: rgba(198, 107, 255, 0.3);
        transform: translateY(-3px);
    }
    .metric-icon { font-size: 1.5rem; margin-bottom: 6px; }
    .metric-val {
        font-size: 1.5rem;
        font-weight: 800;
        background: linear-gradient(135deg, #ff6b9d, #c66bff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    .metric-lbl {
        font-size: 0.75rem;
        color: #8888aa;
        margin-top: 4px;
        text-transform: uppercase;
    }
    .stButton > button {
        background: linear-gradient(135deg, #ff6b9d 0%, #c66bff 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 14px !important;
        padding: 14px 24px !important;
        font-size: 1rem !important;
        font-weight: 700 !important;
        transition: all 0.3s !important;
        box-shadow: 0 8px 25px rgba(198, 107, 255, 0.35) !important;
    }
    .stButton > button:hover {
        transform: translateY(-3px) !important;
        box-shadow: 0 12px 35px rgba(198, 107, 255, 0.5) !important;
    }
    .stTextArea textarea, .stTextInput input {
        background: rgba(255, 255, 255, 0.04) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        color: #ffffff !important;
        border-radius: 14px !important;
        padding: 14px !important;
    }
    .stTextArea textarea:focus, .stTextInput input:focus {
        border-color: #c66bff !important;
        box-shadow: 0 0 0 3px rgba(198, 107, 255, 0.2) !important;
    }
    .stFileUploader {
        background: rgba(255, 255, 255, 0.02);
        border-radius: 14px;
        padding: 12px;
        border: 2px dashed rgba(198, 107, 255, 0.3);
    }
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f0c29, #1a1a3e);
    }
    hr {
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(198, 107, 255, 0.3), transparent);
        margin: 30px 0;
    }
    .stAlert { border-radius: 14px !important; border: none !important; }
</style>
""", unsafe_allow_html=True)
# ============================================================
# Password
# ============================================================
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown("""
        <div style='text-align:center; padding: 40px 0;'>
            <h1 style='font-size: 3rem;'>🔐</h1>
            <h2 style='color:#e0e0ff;'>Private App</h2>
            <p style='color:#a0a0c0;'>Password ထည့်ပြီး ဝင်ပါ</p>
        </div>
    """, unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        pwd = st.text_input("Password", type="password", label_visibility="collapsed", placeholder="Password")
        if st.button("Login", use_container_width=True):
            if pwd == PASSWORD:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Password မှား")
    st.stop()

# ============================================================
# Helper Functions
# ============================================================
def get_video_info(video_path):
    probe = ffmpeg.probe(video_path)
    vs = next(s for s in probe['streams'] if s['codec_type'] == 'video')
    duration = float(probe['format']['duration'])
    return int(vs['width']), int(vs['height']), duration


def srt_time(sec):
    ms = int(round((sec - int(sec)) * 1000))
    total = int(sec)
    if ms >= 1000:
        total += 1
        ms = 0
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def ts_to_sec(ts):
    ts = ts.strip()
    m = re.match(r'^(\d{1,2}):(\d{2}):(\d{2})[,.](\d{1,3})$', ts)
    if m:
        h, mi, se, ms = m.groups()
        return int(h)*3600 + int(mi)*60 + int(se) + int(ms.ljust(3, '0')) / 1000.0
    m = re.match(r'^(\d{1,2}):(\d{2})[,.](\d{1,3})$', ts)
    if m:
        mi, se, ms = m.groups()
        return int(mi)*60 + int(se) + int(ms.ljust(3, '0')) / 1000.0
    return None


def render_subtitle_png(text, output_path, font_path,
                         width, height, font_size=30,
                         position="center", blur_height=120,
                         blur_alpha=160):
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(font_path, font_size)
    except Exception:
        font = ImageFont.load_default()
    if position == "bottom":
        box_y = height - blur_height
    elif position == "center":
        box_y = (height - blur_height) // 2
    else:
        box_y = 0
    draw.rectangle([0, box_y, width, box_y + blur_height], fill=(0, 0, 0, blur_alpha))
    max_chars_per_line = max(15, int(width / (font_size * 0.9)))
    words = text.split()
    lines = []
    cur = ""
    for w in words:
        if len(cur) + len(w) + 1 <= max_chars_per_line:
            cur = cur + " " + w if cur else w
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    line_h = int(font_size * 1.3)
    total_h = len(lines) * line_h
    text_y = box_y + (blur_height - total_h) // 2
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_w = bbox[2] - bbox[0]
        line_x = (width - line_w) // 2
        for dx in [-2, -1, 0, 1, 2]:
            for dy in [-2, -1, 0, 1, 2]:
                draw.text((line_x + dx, text_y + dy), line, font=font, fill=(0, 0, 0, 255))
        draw.text((line_x, text_y), line, font=font, fill=(255, 255, 255, 255))
        text_y += line_h
    img.save(output_path, "PNG")
    return output_path


def script_to_srt(script, audio_duration, srt_path, max_chars=30):
    sentences = script.replace("။", "။|").split("|")
    sentences = [s.strip() + "။" for s in sentences if s.strip()]
    if not sentences:
        return None
    split_sentences = []
    for sent in sentences:
        sent = sent.replace("။။", "။")
        if len(sent) <= max_chars:
            split_sentences.append(sent)
        else:
            words = sent.split()
            cur = ""
            for w in words:
                if len(cur) + len(w) + 1 <= max_chars:
                    cur = cur + " " + w if cur else w
                else:
                    if cur:
                        split_sentences.append(cur.strip())
                    cur = w
            if cur:
                split_sentences.append(cur.strip())
    if not split_sentences:
        return None
    total_chars = sum(len(s) for s in split_sentences)
    current = 0.0
    with open(srt_path, "w", encoding="utf-8") as f:
        for i, sent in enumerate(split_sentences, 1):
            dur = (len(sent) / total_chars) * audio_duration
            f.write(f"{i}\n{srt_time(current)} --> {srt_time(current + dur)}\n{sent}\n\n")
            current += dur
    return srt_path


def parse_srt(srt_path):
    with open(srt_path, "r", encoding="utf-8") as f:
        raw = f.read().replace("\r\n", "\n").replace("\r", "\n")
    chunks = re.split(r"\n\s*\n", raw.strip())
    segments = []
    for chunk in chunks:
        lines = [ln for ln in chunk.split("\n") if ln.strip()]
        if len(lines) < 3:
            continue
        ts_line = next((ln for ln in lines if "-->" in ln), None)
        if not ts_line:
            continue
        parts = re.split(r"\s*-->\s*", ts_line)
        if len(parts) != 2:
            continue
        start = ts_to_sec(parts[0])
        end = ts_to_sec(parts[1])
        if start is None or end is None:
            continue
        ts_idx = lines.index(ts_line)
        text = " ".join(lines[ts_idx + 1:]).strip()
        if text:
            segments.append({"start": start, "end": end, "text": text})
    return segments


def overlay_subtitle_on_video(video_path, srt_path, output_path,
                                font_path, font_size=30,
                                position="center", blur_height=120,
                                blur_alpha=160):
    W, H, duration = get_video_info(video_path)
    segments = parse_srt(srt_path)
    if not segments:
        raise Exception("SRT — segments မရှိ")
    png_dir = "subtitle_pngs"
    os.makedirs(png_dir, exist_ok=True)
    png_files = []
    for i, seg in enumerate(segments):
        png_path = os.path.join(png_dir, f"sub_{i:04d}.png")
        render_subtitle_png(
            text=seg["text"], output_path=png_path, font_path=font_path,
            width=W, height=H, font_size=font_size, position=position,
            blur_height=blur_height, blur_alpha=blur_alpha
        )
        png_files.append({"path": png_path, "start": seg["start"], "end": seg["end"]})
    cmd = ["ffmpeg", "-y", "-i", video_path]
    for p in png_files:
        cmd += ["-i", p["path"]]
    filters = []
    current = "[0:v]"
    for i, p in enumerate(png_files):
        out_label = f"[v{i}]"
        filters.append(
            f"{current}[{i+1}:v]overlay=0:0:"
            f"enable='between(t,{p['start']:.3f},{p['end']:.3f})'"
            f"{out_label}"
        )
        current = out_label
    filter_complex = ";".join(filters)
    cmd += [
        "-filter_complex", filter_complex, "-map", current, "-map", "0:a?",
        "-c:v", "libx264", "-crf", "18", "-preset", "medium",
        "-c:a", "copy", output_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    if result.returncode != 0:
        raise Exception(f"FFmpeg error:\n{(result.stderr or '')[-1000:]}")
    for p in png_files:
        try:
            os.remove(p["path"])
        except Exception:
            pass
    return output_path


def split_script(text, max_chars=400):
    sentences = text.replace("။", "။|").split("|")
    sentences = [s.strip() + "။" for s in sentences if s.strip()]
    chunks = []
    current = ""
    for s in sentences:
        if len(current) + len(s) <= max_chars:
            current += s
        else:
            if current:
                chunks.append(current)
            if len(s) > max_chars:
                for i in range(0, len(s), max_chars):
                    chunks.append(s[i:i + max_chars])
                current = ""
            else:
                current = s
    if current:
        chunks.append(current)
    return chunks


def tts_demo(chunks, ref_audio_path, space, progress_callback=None):
    client = Client(space)
    audio_files = []
    ref_file = handle_file(ref_audio_path) if ref_audio_path else None
    for i, chunk in enumerate(chunks):
        if progress_callback:
            progress_callback(i, len(chunks), chunk)
        result = client.predict(
            text_input=chunk,
            control_instruction="A warm young woman, calm and expressive",
            reference_wav_path_input=ref_file,
            use_prompt_text=False,
            prompt_text_input="",
            cfg_value_input=2.0,
            do_normalize=True,
            denoise=False,
            api_name="/generate",
        )
        audio_path = result[0] if isinstance(result, (tuple, list)) else result
        chunk_path = f"chunk_demo_{i}.wav"
        shutil.copy(audio_path, chunk_path)
        audio_files.append(chunk_path)
    return audio_files


def tts_burmese(chunks, ref_audio_path, space, progress_callback=None):
    client = Client(space)
    audio_files = []
    if not ref_audio_path:
        raise Exception(f"{space} — Reference Audio လိုတယ်")
    ref_file = handle_file(ref_audio_path)
    for i, chunk in enumerate(chunks):
        if progress_callback:
            progress_callback(i, len(chunks), chunk)
        result = client.predict(
            target_text=chunk,
            ref_audio=ref_file,
            ref_text="မြန်မာ အသံနမူနာ",
            cfg_value=2.0,
            inference_timesteps=10,
            api_name="/tts"
        )
        audio_path = result[0] if isinstance(result, (tuple, list)) else result
        chunk_path = f"chunk_burmese_{i}.wav"
        shutil.copy(audio_path, chunk_path)
        audio_files.append(chunk_path)
    return audio_files


def run_tts_chunked(text, output_path, ref_audio_path=None, progress_callback=None):
    chunks = split_script(text, max_chars=400)
    audio_files = None
    last_error = None
    for space_info in VOXCPM_SPACES:
        space = space_info["space"]
        name = space_info["name"]
        space_type = space_info["type"]
        try:
            st.info(f"{name}...")
            if space_type == "demo":
                audio_files = tts_demo(chunks, ref_audio_path, space, progress_callback)
            else:
                audio_files = tts_burmese(chunks, ref_audio_path, space, progress_callback)
            st.success(f"{name} — အောင်မြင်")
            break
        except Exception as e:
            last_error = str(e)
            st.warning(f"{name} — Fail: {last_error[:120]}")
            audio_files = None
            continue
    if audio_files is None:
        raise Exception(f"Space အားလုံး — Fail\nLast error: {last_error}")
    with open("concat_list.txt", "w", encoding="utf-8") as f:
        for audio in audio_files:
            f.write(f"file '{audio}'\n")
    ffmpeg.input("concat_list.txt", format="concat", safe=0).output(
        output_path, acodec="libmp3lame", audio_bitrate="192k", ar=48000
    ).run(overwrite_output=True)
    return output_path
# ============================================================
# HERO HEADER
# ============================================================
st.markdown("""
    <div class='hero-container'>
        <h1 class='hero-title'>VoxCPM2 Movie Recap</h1>
        <p class='hero-sub'>Gemini Web → Script → VoxCPM2 → မြန်မာ Recap</p>
        <div class='hero-line'></div>
    </div>
""", unsafe_allow_html=True)

font_ok = os.path.exists(FONT_FILE)
st.markdown(f"""
<div class='status-row'>
    <span class='status-pill {"green" if font_ok else "red"}'>
        {"✓" if font_ok else "✗"} Font {"Ready" if font_ok else "Missing"}
    </span>
    <span class='status-pill purple'>Private</span>
    <span class='status-pill orange'>VoxCPM2</span>
    <span class='status-pill'>Myanmar TTS</span>
</div>
""", unsafe_allow_html=True)

# ============================================================
# STEP 1
# ============================================================
st.markdown("""
<div class='step-card'>
    <span class='step-num'>1</span>
    <span class='step-title'>Gemini Web → Script</span>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class='glass-info'>
    <b>Gemini Web ကို ဖွင့်ပါ:</b> 
    <a href='https://gemini.google.com' target='_blank'>gemini.google.com</a><br>
    Video Upload → Prompt Paste → Script Copy
</div>
""", unsafe_allow_html=True)

with st.expander("Prompt (Copy → Gemini Web)", expanded=True):
    st.code(
        "Watch this video carefully and write a clear, continuous movie recap script "
        "in Myanmar language for audio narration that matches the length of the video. "
        "Return plain speech text only without markdown titles.",
        language="text"
    )

# ============================================================
# STEP 2
# ============================================================
st.markdown("""
<div class='step-card'>
    <span class='step-num'>2</span>
    <span class='step-title'>Script Paste</span>
</div>
""", unsafe_allow_html=True)

if "script_text" not in st.session_state:
    st.session_state.script_text = ""

script = st.text_area(
    "Script",
    value=st.session_state.script_text,
    height=250,
    placeholder="မြန်မာ Script ကို ဒီမှာ paste လုပ်ပါ...",
    label_visibility="collapsed"
)
st.session_state.script_text = script

col1, col2 = st.columns([3, 1])
with col1:
    char_count = len(script)
    if char_count > 100:
        color, status = "#38ef7d", "Ready"
    elif char_count > 0:
        color, status = "#f2c94c", "Short"
    else:
        color, status = "#eb3349", "Empty"
    st.markdown(
        f"<div style='padding:12px 0;'>"
        f"<span style='color:{color}; font-weight:700; font-size:1rem;'>"
        f"{char_count:,} စာလုံး</span>"
        f"<span style='color:#8888aa; margin-left:12px; font-size:0.85rem;'>• {status}</span>"
        f"</div>",
        unsafe_allow_html=True
    )
with col2:
    if st.button("Clear", use_container_width=True):
        st.session_state.script_text = ""
        st.rerun()

# ============================================================
# STEP 3
# ============================================================
st.markdown("""
<div class='step-card'>
    <span class='step-num'>3</span>
    <span class='step-title'>Reference Audio + Video</span>
</div>
""", unsafe_allow_html=True)

if "ref_audio_path" not in st.session_state:
    st.session_state.ref_audio_path = None

col1, col2 = st.columns(2)

with col1:
    st.markdown("##### 🎤 Reference Audio")
    st.caption("Optional — Voice Cloning အတွက်")
    ref_audio = st.file_uploader(
        "Reference Audio",
        type=["wav", "mp3", "m4a"],
        label_visibility="collapsed",
        key="ref_up"
    )
    if ref_audio is not None:
        ref_path = "reference_voice.wav"
        with open(ref_path, "wb") as f:
            f.write(ref_audio.read())
        st.session_state.ref_audio_path = ref_path
        st.markdown(
            "<span class='status-pill green' style='display:inline-flex;'>✓ Audio Ready</span>",
            unsafe_allow_html=True
        )

with col2:
    st.markdown("##### 📹 Video Upload")
    st.caption("MP4, MOV, AVI, MKV")
    video_file = st.file_uploader(
        "Video Upload",
        type=["mp4", "mov", "avi", "mkv"],
        label_visibility="collapsed",
        key="vid_up"
    )
    if video_file is not None:
        size_mb = video_file.size / (1024 * 1024)
        st.markdown(
            f"<span class='status-pill green' style='display:inline-flex;'>✓ {size_mb:.1f} MB</span>",
            unsafe_allow_html=True
        )
    ✨ <b>Ready to Go!</b><br>
    st.markdown("""
<div class='glass-info'>
    ✨ <b>Ready to Go!</b><br>
# ============================================================
# STEP 4 — SUBTITLE SETTINGS
# ============================================================
st.markdown("""
<div class='step-card'>
    <span class='step-num'>4</span>
    <span class='step-title'>Subtitle Settings</span>
</div>
""", unsafe_allow_html=True)

use_subtitle = st.toggle("စာတန်းထိုး (Burn-in)", value=True)

sub_position = DEFAULT_SUB_POSITION
sub_font_size = DEFAULT_FONT_SIZE
blur_height = DEFAULT_BLUR_HEIGHT
blur_alpha = DEFAULT_BLUR_ALPHA

st.markdown(f"""
<div class='metric-grid'>
    <div class='metric-tile'>
        <div class='metric-icon'>📍</div>
        <div class='metric-val'>Center</div>
        <div class='metric-lbl'>Position</div>
    </div>
    <div class='metric-tile'>
        <div class='metric-icon'>🔤</div>
        <div class='metric-val'>{sub_font_size}</div>
        <div class='metric-lbl'>Font Size</div>
    </div>
    <div class='metric-tile'>
        <div class='metric-icon'>⬛</div>
        <div class='metric-val'>{blur_height}px</div>
        <div class='metric-lbl'>Blur Box</div>
    </div>
    <div class='metric-tile'>
        <div class='metric-icon'>🎨</div>
        <div class='metric-val'>{blur_alpha}</div>
        <div class='metric-lbl'>Opacity</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ============================================================
# PREVIEW
# ============================================================
if video_file is not None and use_subtitle:
    st.markdown("""
    <div class='step-card'>
        <span class='step-num'>5</span>
        <span class='step-title'>Live Preview</span>
    </div>
    """, unsafe_allow_html=True)

    with st.spinner("Preview ဖန်တီးနေသည်..."):
        temp_video_preview = "preview_video.mp4"
        video_file.seek(0)
        with open(temp_video_preview, "wb") as f:
            f.write(video_file.read())

        W, H, _ = get_video_info(temp_video_preview)
        preview_png = "preview_sub.png"
        render_subtitle_png(
            text="စာတန်းထိုး Preview",
            output_path=preview_png,
            font_path=FONT_FILE,
            width=W,
            height=H,
            font_size=sub_font_size,
            position=sub_position,
            blur_height=blur_height,
            blur_alpha=blur_alpha
        )

        cap = cv2.VideoCapture(temp_video_preview)
        ret, frame = cap.read()
        cap.release()

        if ret:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            bg = Image.fromarray(frame_rgb).convert("RGBA")
            fg = Image.open(preview_png).convert("RGBA")
            composite = Image.alpha_composite(bg, fg)

            pw = 720
            ph = int(H * (pw / W))
            composite.resize((pw, ph), Image.LANCZOS).convert("RGB").save("preview_result.png")
            st.image("preview_result.png", caption="Preview", use_container_width=True)

# ============================================================
# STEP 6 — GENERATE
# ============================================================
st.markdown("""
<div class='step-card'>
    <span class='step-num'>6</span>
    <span class='step-title'>Generate Recap Video</span>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class='glass-info'>
    <b>Ready to Go!</b><br>
    Script + Video ပြည့်စုံပြီဆိုရင် — အောက်က Button ကို နှိပ်လိုက်ပါ။<br>
    AI က VoxCPM2 အသံနဲ့ မြန်မာ Recap Video ကို ဖန်တီးပေးပါမယ်။
</div>
""", unsafe_allow_html=True)

generate_clicked = st.button("Generate Recap Video", type="primary", use_container_width=True)

if generate_clicked:
    if not script.strip():
        st.error("Script paste လုပ်ပါ — Step 2")
        st.stop()
    if video_file is None:
        st.error("Video Upload တင်ပါ — Step 3")
        st.stop()

    with st.spinner("Video စစ်ဆေးနေသည်..."):
        video_filename = "input_video.mp4"
        video_file.seek(0)
        with open(video_filename, "wb") as f:
            f.write(video_file.read())
        W, H, video_duration = get_video_info(video_filename)

    st.info("VoxCPM2 → အသံ ဖန်တီးနေသည်...")

    progress_bar = st.progress(0)
    status_text = st.empty()

    def update_progress(i, total, chunk):
        progress_bar.progress((i + 1) / total)
        status_text.markdown(
            f"<span class='status-pill purple'>[{i+1}/{total}] — {len(chunk)} စာလုံး</span>",
            unsafe_allow_html=True
        )

    audio_path = "recap_voice.mp3"

    try:
        run_tts_chunked(script, audio_path,
                        ref_audio_path=st.session_state.ref_audio_path,
                        progress_callback=update_progress)
        st.success("အသံ ထုတ်ပြီး")
        audio_dur = float(ffmpeg.probe(audio_path)['format']['duration'])
        st.markdown(
            f"<span class='status-pill green' style='display:inline-flex;'>Audio: {audio_dur:.1f}s</span>",
            unsafe_allow_html=True
        )
    except Exception as e:
        st.error(f"VoxCPM2 error: {e}")
        st.stop()

    tempo = audio_dur / video_duration
    tempo = max(0.5, min(2.0, tempo))
    st.markdown(
        f"<span class='status-pill orange' style='display:inline-flex;'>Audio Speed: {tempo:.2f}x</span>",
        unsafe_allow_html=True
    )

    srt_path = None
    if use_subtitle:
        with st.spinner("Script → SRT..."):
            srt_path = script_to_srt(script, video_duration, "recap.srt")
            if srt_path and os.path.exists(srt_path):
                st.success("SRT ဖန်တီးပြီး")

    with st.spinner("Recap Video Render..."):
        temp_video = "temp_recap.mp4"
        input_video = ffmpeg.input(video_filename)
        input_audio = ffmpeg.input(audio_path).audio.filter('atempo', tempo)

        stream = ffmpeg.output(
            input_video.video, input_audio, temp_video,
            vcodec='libx264', crf=18, preset='medium',
            acodec='aac', audio_bitrate='192k',
            shortest=None
        )
        ffmpeg.run(stream, overwrite_output=True)

        final_path = "final_recap.mp4"

        if use_subtitle and srt_path:
            with st.spinner("Subtitle Overlay..."):
                overlay_subtitle_on_video(
                    video_path=temp_video,
                    srt_path=srt_path,
                    output_path=final_path,
                    font_path=FONT_FILE,
                    font_size=sub_font_size,
                    position=sub_position,
                    blur_height=blur_height,
                    blur_alpha=blur_alpha
                )
                st.success("Subtitle Overlay ပြီး")
        else:
            shutil.copy(temp_video, final_path)

    st.success("ပြီးပါပြီ!")
    st.video(final_path)

    f = open(final_path, "rb")
    st.download_button("Recap Video Download", f, file_name="final_recap.mp4")
    f.close()   
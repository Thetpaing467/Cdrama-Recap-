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
    .stApp {
        background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
        color: #ffffff;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .main-title {
        font-size: 2.5rem;
        font-weight: 900;
        background: linear-gradient(90deg, #667eea, #764ba2, #f093fb, #f5576c);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        text-align: center;
        margin-bottom: 0.3rem;
    }
    .sub-title {
        text-align: center;
        color: #a0a0c0;
        font-size: 1rem;
        margin-bottom: 1.5rem;
    }
    .section-header {
        background: linear-gradient(90deg, rgba(102,126,234,0.15), rgba(118,75,162,0.05));
        border-left: 4px solid #667eea;
        padding: 12px 18px;
        border-radius: 8px;
        margin: 20px 0 15px 0;
        font-size: 1.2rem;
        font-weight: 700;
        color: #e0e0ff;
    }
    .pill {
        display: inline-block;
        background: linear-gradient(90deg, #667eea, #764ba2);
        color: white;
        padding: 6px 14px;
        border-radius: 50px;
        font-size: 0.85rem;
        font-weight: 600;
        margin: 4px;
    }
    .pill-green { background: linear-gradient(90deg, #11998e, #38ef7d); }
    .pill-red { background: linear-gradient(90deg, #eb3349, #f45c43); }
    .pill-orange { background: linear-gradient(90deg, #f2994a, #f2c94c); }
    .info-box {
        background: linear-gradient(90deg, rgba(102,126,234,0.15), rgba(118,75,162,0.15));
        border-left: 4px solid #667eea;
        padding: 14px 18px;
        border-radius: 10px;
        margin: 12px 0;
        color: #d0d0ff;
    }
    .stButton > button {
        background: linear-gradient(90deg, #667eea, #764ba2);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 14px 20px;
        font-size: 1rem;
        font-weight: 700;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(102, 126, 234, 0.6);
    }
    .stTextArea textarea, .stTextInput input {
        background: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        color: #ffffff !important;
        border-radius: 12px !important;
    }
    .stFileUploader {
        background: rgba(255, 255, 255, 0.03);
        border-radius: 12px;
        padding: 10px;
        border: 1px dashed rgba(102, 126, 234, 0.5);
    }
    hr { border-color: rgba(255, 255, 255, 0.1); margin: 25px 0; }
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a2e, #16213e);
    }
    .metric-card {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        padding: 15px;
        text-align: center;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    .metric-value {
        font-size: 1.6rem;
        font-weight: 800;
        color: #667eea;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #a0a0c0;
        margin-top: 4px;
    }
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
# HEADER
# ============================================================
st.markdown("""
    <div style='text-align:center; padding: 20px 0 10px 0;'>
        <h1 class='main-title'>VoxCPM2 Movie Recap</h1>
        <p class='sub-title'>Gemini Web → Script → VoxCPM2 → မြန်မာ Recap Video</p>
    </div>
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)
with col1:
    font_status = "Font Ready" if os.path.exists(FONT_FILE) else "Font Missing"
    font_pill = "pill-green" if os.path.exists(FONT_FILE) else "pill-red"
    st.markdown(f"<div style='text-align:center;'><span class='pill {font_pill}'>{font_status}</span></div>", unsafe_allow_html=True)
with col2:
    st.markdown("<div style='text-align:center;'><span class='pill'>Private App</span></div>", unsafe_allow_html=True)
with col3:
    st.markdown("<div style='text-align:center;'><span class='pill pill-orange'>VoxCPM2 Engine</span></div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# STEP 1
st.markdown("<div class='section-header'>Step 1: Gemini Web → Script</div>", unsafe_allow_html=True)
st.markdown("""
<div class='info-box'>
    <b>Gemini Web:</b> <a href='https://gemini.google.com' target='_blank' style='color:#a0c0ff;'>gemini.google.com</a> →
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

# STEP 2
st.markdown("<div class='section-header'>Step 2: Script Paste</div>", unsafe_allow_html=True)
if "script_text" not in st.session_state:
    st.session_state.script_text = ""

script = st.text_area(
    "Script",
    value=st.session_state.script_text,
    height=250,
    placeholder="မြန်မာ Script paste...",
    label_visibility="collapsed"
)
st.session_state.script_text = script

col1, col2 = st.columns([3, 1])
with col1:
    char_count = len(script)
    word_color = "#38ef7d" if char_count > 50 else "#f2c94c" if char_count > 0 else "#f45c43"
    st.markdown(
        f"<div style='padding:10px;'><span style='color:{word_color}; font-weight:600;'>စာလုံး: {char_count:,}</span></div>",
        unsafe_allow_html=True
    )
with col2:
    if st.button("ဖျက်မယ်", use_container_width=True):
        st.session_state.script_text = ""
        st.rerun()

# STEP 3
st.markdown("<div class='section-header'>Step 3: Reference Audio + Video</div>", unsafe_allow_html=True)
if "ref_audio_path" not in st.session_state:
    st.session_state.ref_audio_path = None

col1, col2 = st.columns(2)
with col1:
    st.markdown("**Reference Audio** (Optional)")
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
        st.markdown("<span class='pill pill-green'>Reference Audio Ready</span>", unsafe_allow_html=True)
with col2:
    st.markdown("**Video Upload**")
    video_file = st.file_uploader(
        "Video Upload",
        type=["mp4", "mov", "avi", "mkv"],
        label_visibility="collapsed",
        key="vid_up"
    )
    if video_file is not None:
        size_mb = video_file.size / (1024 * 1024)
        st.markdown(f"<span class='pill pill-green'>Video: {size_mb:.1f} MB</span>", unsafe_allow_html=True)

# SUBTITLE SETTINGS
st.markdown("<div class='section-header'>Subtitle Settings</div>", unsafe_allow_html=True)
use_subtitle = st.toggle("စာတန်းထိုး (Burn-in)", value=True)

sub_position = DEFAULT_SUB_POSITION
sub_font_size = DEFAULT_FONT_SIZE
blur_height = DEFAULT_BLUR_HEIGHT
blur_alpha = DEFAULT_BLUR_ALPHA

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown("<div class='metric-card'><div class='metric-value'>📍</div><div class='metric-label'>အလယ်</div></div>", unsafe_allow_html=True)
with col2:
    st.markdown(f"<div class='metric-card'><div class='metric-value'>{sub_font_size}</div><div class='metric-label'>Font Size</div></div>", unsafe_allow_html=True)
with col3:
    st.markdown(f"<div class='metric-card'><div class='metric-value'>{blur_height}px</div><div class='metric-label'>Blur Box</div></div>", unsafe_allow_html=True)
with col4:
    st.markdown(f"<div class='metric-card'><div class='metric-value'>{blur_alpha}</div><div class='metric-label'>Opacity</div></div>", unsafe_allow_html=True)

# PREVIEW
if video_file is not None and use_subtitle:
    st.markdown("<div class='section-header'>Preview</div>", unsafe_allow_html=True)
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

# STEP 4
st.markdown("<div class='section-header'>Step 4: Generate Recap</div>", unsafe_allow_html=True)
st.markdown("""
<div class='info-box'>
    <b>Ready?</b> Script + Video ပြည့်စုံရင် — Generate ကို နှိပ်လိုက်ပါ။<br>
    AI က VoxCPM2 အသံနဲ့ မြန်မာ Recap Video ကို ဖန်တီးပေးပါမယ်။
</div>
""", unsafe_allow_html=True)

generate_clicked = st.button("Generate Recap Video", type="primary", use_container_width=True)

if generate_clicked:
    if not script.strip():
        st.error("Script paste — Step 2")
        st.stop()
    if video_file is None:
        st.error("Video Upload — Step 3")
        st.stop()
    with st.spinner("Video — စစ်ဆေးနေသည်..."):
        video_filename = "input_video.mp4"
        video_file.seek(0)
        with open(video_filename, "wb") as f:
            f.write(video_file.read())
        W, H, video_duration = get_video_info(video_filename)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"<div class='metric-card'><div class='metric-value'>{W}x{H}</div><div class='metric-label'>Resolution</div></div>", unsafe_allow_html=True)
        with col2:
            st.markdown(f"<div class='metric-card'><div class='metric-value'>{video_duration:.1f}s</div><div class='metric-label'>Duration</div></div>", unsafe_allow_html=True)
        with col3:
            st.markdown(f"<div class='metric-card'><div class='metric-value'>{len(script)}</div><div class='metric-label'>Characters</div></div>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    st.info("VoxCPM2 → အသံ ဖန်တီးနေသည်...")
    progress_bar = st.progress(0)
    status_text = st.empty()
    def update_progress(i, total, chunk):
        progress_bar.progress((i + 1) / total)
        status_text.markdown(f"<span class='pill'>[{i+1}/{total}] ({len(chunk)} စာလုံး)</span>", unsafe_allow_html=True)
    audio_path = "recap_voice.mp3"
    try:
        run_tts_chunked(script, audio_path,
                        ref_audio_path=st.session_state.ref_audio_path,
                        progress_callback=update_progress)
        st.success("အသံ ထုတ်ပြီး")
        audio_dur = float(ffmpeg.probe(audio_path)['format']['duration'])
        st.markdown(f"<span class='pill pill-green'>Audio: {audio_dur:.1f}s</span>", unsafe_allow_html=True)
    except Exception as e:
        st.error(f"VoxCPM2 error: {e}")
        st.stop()
    tempo = audio_dur / video_duration
    tempo = max(0.5, min(2.0, tempo))
    st.markdown(f"<span class='pill pill-orange'>Audio Speed: {tempo:.2f}x</span>", unsafe_allow_html=True)
    srt_path = None
    if use_subtitle:
        with st.spinner("Script → SRT..."):
            srt_path = script_to_srt(script, video_duration, "recap.srt")
            if srt_path and os.path.exists(srt_path):
                st.success("SRT — ဖန်တီးပြီး")
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
            with st.spinner("Subtitle Overlay — လုပ်နေသည်..."):
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
                st.success("Subtitle — Overlay ပြီး")
        else:
            shutil.copy(temp_video, final_path)
    st.success("ပြီးပါပြီ!")
    st.video(final_path)
    f = open(final_path, "rb")
    st.download_button("Recap Video Download", f, file_name="final_recap.mp4")
    f.close()
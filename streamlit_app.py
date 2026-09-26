import streamlit as st
import os
import re
import ffmpeg
import shutil
import subprocess
from PIL import Image, ImageDraw, ImageFont
import cv2
from gradio_client import Client, handle_file

# ============================================================
# Config
# ============================================================
SPACES = [
    {"space": "openbmb/VoxCPM-Demo", "type": "demo"},
    {"space": "hgghfhjfhjguyjf/Voxcpm-Burmese-Tts", "type": "burmese"},
]
PASSWORD = "voxcpm2026"
FONT_FILE = "MyanmarPadaung.ttf"

# ပုံသေ တန်ဖိုး — Slider မလိုဘူး
FIXED_FONT_SIZE = 30
FIXED_BOX_HEIGHT = 100
FIXED_OPACITY = 100

st.set_page_config(page_title="VoxCPM2 Recap", page_icon="🎬", layout="centered")

# ============================================================
# Custom CSS — လှလှလေး
# ============================================================
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(160deg, #0f0f23 0%, #1a1a35 50%, #0f0f23 100%);
        color: #e8e8f0;
    }
    #MainMenu, footer, header { visibility: hidden; }

    h1 { color: #fff !important; font-weight: 800 !important; letter-spacing: -0.5px; }
    h2 { color: #e0e0f0 !important; font-weight: 700 !important; }
    h3 { color: #c8c8e0 !important; font-weight: 600 !important; }

    .main-title {
        text-align: center;
        font-size: 2.2rem;
        font-weight: 900;
        background: linear-gradient(90deg, #ff6b9d, #c66bff, #6ba8ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 4px;
    }
    .main-sub {
        text-align: center;
        color: #8888aa;
        font-size: 0.9rem;
        margin-bottom: 20px;
    }

    .stButton > button {
        background: linear-gradient(135deg, #667eea, #764ba2) !important;
        color: #fff !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 12px 20px !important;
        font-weight: 600 !important;
        transition: all 0.2s !important;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3) !important;
    }
    .stButton > button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.5) !important;
    }

    .stTextArea textarea {
        background: rgba(255, 255, 255, 0.04) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        color: #fff !important;
        border-radius: 10px !important;
    }
    .stTextArea textarea:focus {
        border-color: #667eea !important;
        box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.2) !important;
    }

    .stFileUploader {
        background: rgba(255, 255, 255, 0.02);
        border-radius: 10px;
        padding: 8px;
    }

    .stAlert {
        border-radius: 10px !important;
        border: none !important;
    }

    hr {
        border-color: rgba(255, 255, 255, 0.08);
        margin: 24px 0;
    }

    section[data-testid="stSidebar"] {
        background: #0a0a1a;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# Password
# ============================================================
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.markdown("<div class='main-title'>🔐 Private App</div>", unsafe_allow_html=True)
    st.markdown("<div class='main-sub'>Password ထည့်ပြီး ဝင်ပါ</div>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        pwd = st.text_input("Password", type="password", label_visibility="collapsed", placeholder="Password")
        if st.button("Login", use_container_width=True):
            if pwd == PASSWORD:
                st.session_state.auth = True
                st.rerun()
            else:
                st.error("Password မှား")
    st.stop()


# ============================================================
# Helper Functions
# ============================================================
def vid_info(p):
    pr = ffmpeg.probe(p)
    v = next(s for s in pr['streams'] if s['codec_type'] == 'video')
    return int(v['width']), int(v['height']), float(pr['format']['duration'])


def t2s(s):
    ms = int(round((s - int(s)) * 1000))
    tot = int(s)
    if ms >= 1000:
        tot += 1
        ms = 0
    h, r = divmod(tot, 3600)
    m, sec = divmod(r, 60)
    return f"{h:02d}:{m:02d}:{sec:02d},{ms:03d}"


def s2t(ts):
    ts = ts.strip()
    m = re.match(r'^(\d{1,2}):(\d{2}):(\d{2})[,.](\d{1,3})$', ts)
    if m:
        h, mi, se, ms = m.groups()
        return int(h)*3600 + int(mi)*60 + int(se) + int(ms.ljust(3, '0'))/1000
    m = re.match(r'^(\d{1,2}):(\d{2})[,.](\d{1,3})$', ts)
    if m:
        mi, se, ms = m.groups()
        return int(mi)*60 + int(se) + int(ms.ljust(3, '0'))/1000
    return None


def render_png(text, out, font_path, W, H, fs=30, pos="center", bh=100, ba=100):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    try:
        f = ImageFont.truetype(font_path, fs)
    except:
        f = ImageFont.load_default()
    by = (H - bh)//2 if pos == "center" else (H - bh if pos == "bottom" else 0)
    d.rectangle([0, by, W, by + bh], fill=(0, 0, 0, ba))
    mc = max(15, int(W / (fs * 0.9)))
    lines, cur = [], ""
    for w in text.split():
        if len(cur) + len(w) + 1 <= mc:
            cur = cur + " " + w if cur else w
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    lh = int(fs * 1.3)
    ty = by + (bh - len(lines)*lh)//2
    for ln in lines:
        bb = d.textbbox((0, 0), ln, font=f)
        lw = bb[2] - bb[0]
        lx = (W - lw)//2
        for dx in [-2, -1, 0, 1, 2]:
            for dy in [-2, -1, 0, 1, 2]:
                d.text((lx+dx, ty+dy), ln, font=f, fill=(0, 0, 0, 255))
        d.text((lx, ty), ln, font=f, fill=(255, 255, 255, 255))
        ty += lh
    img.save(out, "PNG")
    return out


def scr_to_srt(scr, dur, path, mc=30):
    sents = scr.replace("။", "။|").split("|")
    sents = [s.strip()+"။" for s in sents if s.strip()]
    if not sents: return None
    parts = []
    for s in sents:
        s = s.replace("။။", "။")
        if len(s) <= mc:
            parts.append(s)
        else:
            cur = ""
            for w in s.split():
                if len(cur)+len(w)+1 <= mc:
                    cur = cur+" "+w if cur else w
                else:
                    if cur: parts.append(cur.strip())
                    cur = w
            if cur: parts.append(cur.strip())
    if not parts: return None
    tot = sum(len(p) for p in parts)
    cur = 0.0
    with open(path, "w", encoding="utf-8") as f:
        for i, p in enumerate(parts, 1):
            d = (len(p)/tot)*dur
            f.write(f"{i}\n{t2s(cur)} --> {t2s(cur+d)}\n{p}\n\n")
            cur += d
    return path


def parse_srt(path):
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read().replace("\r\n", "\n").replace("\r", "\n")
    segs = []
    for chunk in re.split(r"\n\s*\n", raw.strip()):
        ls = [l for l in chunk.split("\n") if l.strip()]
        if len(ls) < 3: continue
        ts = next((l for l in ls if "-->" in l), None)
        if not ts: continue
        p = re.split(r"\s*-->\s*", ts)
        if len(p) != 2: continue
        a, b = s2t(p[0]), s2t(p[1])
        if a is None or b is None: continue
        idx = ls.index(ts)
        txt = " ".join(ls[idx+1:]).strip()
        if txt: segs.append({"start": a, "end": b, "text": txt})
    return segs


def overlay(vp, sp, op, fp, fs=30, pos="center", bh=100, ba=100):
    W, H, _ = vid_info(vp)
    segs = parse_srt(sp)
    if not segs: raise Exception("SRT empty")
    os.makedirs("subtitle_pngs", exist_ok=True)
    pngs = []
    for i, s in enumerate(segs):
        p = f"subtitle_pngs/s_{i:04d}.png"
        render_png(s["text"], p, fp, W, H, fs, pos, bh, ba)
        pngs.append({"p": p, "a": s["start"], "b": s["end"]})
    cmd = ["ffmpeg", "-y", "-i", vp] + sum([["-i", x["p"]] for x in pngs], [])
    flt, cur = [], "[0:v]"
    for i, x in enumerate(pngs):
        lbl = f"[v{i}]"
        flt.append(f"{cur}[{i+1}:v]overlay=0:0:enable='between(t,{x['a']:.3f},{x['b']:.3f})'{lbl}")
        cur = lbl
    cmd += ["-filter_complex", ";".join(flt), "-map", cur, "-map", "0:a?",
            "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-c:a", "copy", op]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    if r.returncode != 0: raise Exception(f"FFmpeg: {(r.stderr or '')[-500:]}")
    for x in pngs:
        try: os.remove(x["p"])
        except: pass
    return op


def split_scr(t, mc=400):
    sents = t.replace("။", "။|").split("|")
    sents = [s.strip()+"။" for s in sents if s.strip()]
    out, cur = [], ""
    for s in sents:
        if len(cur)+len(s) <= mc:
            cur += s
        else:
            if cur: out.append(cur)
            if len(s) > mc:
                for i in range(0, len(s), mc): out.append(s[i:i+mc])
                cur = ""
            else:
                cur = s
    if cur: out.append(cur)
    return out


def tts_run(chunks, ref, space, cb=None):
    cl = Client(space)
    files = []
    rf = handle_file(ref) if ref else None
    for i, c in enumerate(chunks):
        if cb: cb(i, len(chunks), c)
        res = cl.predict(
            text_input=c,
            control_instruction="A warm young woman, calm and expressive",
            reference_wav_path_input=rf,
            use_prompt_text=False, prompt_text_input="",
            cfg_value_input=2.0, do_normalize=True, denoise=False,
            api_name="/generate"
        )
        p = res[0] if isinstance(res, (tuple, list)) else res
        dst = f"chunk_{i}.wav"
        shutil.copy(p, dst)
        files.append(dst)
    return files


def tts_burmese(chunks, ref, space, cb=None):
    cl = Client(space)
    files = []
    if not ref: raise Exception("Reference Audio needed")
    rf = handle_file(ref)
    for i, c in enumerate(chunks):
        if cb: cb(i, len(chunks), c)
        res = cl.predict(
            target_text=c, ref_audio=rf, ref_text="မြန်မာ အသံနမူနာ",
            cfg_value=2.0, inference_timesteps=10, api_name="/tts"
        )
        p = res[0] if isinstance(res, (tuple, list)) else res
        dst = f"chunk_b_{i}.wav"
        shutil.copy(p, dst)
        files.append(dst)
    return files


def tts_all(text, out, ref=None, cb=None):
    chunks = split_scr(text, 400)
    files = None
    for s in SPACES:
        try:
            if s["type"] == "demo":
                files = tts_run(chunks, ref, s["space"], cb)
            else:
                files = tts_burmese(chunks, ref, s["space"], cb)
            break
        except Exception:
            files = None
            continue
    if files is None:
        raise Exception("TTS Failed")
    with open("concat.txt", "w", encoding="utf-8") as f:
        for a in files: f.write(f"file '{a}'\n")
    ffmpeg.input("concat.txt", format="concat", safe=0).output(
        out, acodec="libmp3lame", audio_bitrate="192k", ar=48000
    ).run(overwrite_output=True)
    return out
# ============================================================
# Main UI
# ============================================================
st.markdown("<div class='main-title'>🎬 VoxCPM2 Recap</div>", unsafe_allow_html=True)
st.markdown("<div class='main-sub'>Video → မြန်မာ Script → Recap Video</div>", unsafe_allow_html=True)

st.divider()

# ============================================================
# Step 1 — Script
# ============================================================
st.subheader("📝 Step 1 — Gemini Web မှ Script")

col1, col2 = st.columns([1, 1])
with col1:
    st.link_button("🌐 Open Gemini Web", "https://gemini.google.com", use_container_width=True)

with st.expander("📋 Prompt — Copy လုပ်ပါ"):
    st.code(
        "Watch this video carefully and write a clear, continuous movie recap script "
        "in Myanmar language for audio narration that matches the length of the video. "
        "Return plain speech text only without markdown titles.",
        language="text"
    )

st.divider()

# ============================================================
# Step 2 — Script Paste
# ============================================================
st.subheader("📝 Step 2 — Script Paste")

if "script" not in st.session_state:
    st.session_state.script = ""

script = st.text_area(
    "Script",
    value=st.session_state.script,
    height=220,
    label_visibility="collapsed",
    placeholder="မြန်မာ Script paste..."
)
st.session_state.script = script

col1, col2 = st.columns([3, 1])
with col1:
    st.caption(f"📝 စာလုံး — {len(script):,}")
with col2:
    if st.button("🗑️ Clear", use_container_width=True):
        st.session_state.script = ""
        st.rerun()

st.divider()
# ============================================================
# Step 3 — Upload
# ============================================================
st.subheader("📁 Step 3 — Reference Audio + Video")

if "ref" not in st.session_state:
    st.session_state.ref = None

c1, c2 = st.columns(2)
with c1:
    ref = st.file_uploader("🎤 Ref Audio (Optional)", type=["wav", "mp3", "m4a"])
    if ref:
        with open("ref.wav", "wb") as f:
            f.write(ref.read())
        st.session_state.ref = "ref.wav"
        st.success("✅ Ref Audio Ready")

with c2:
    vid = st.file_uploader("📹 Video Upload", type=["mp4", "mov", "avi", "mkv"])
    if vid:
        st.success(f"✅ Video — {vid.size / (1024*1024):.1f} MB")

st.divider()

# ============================================================
# Step 4 — Subtitle Toggle (Slider မပါ)
# ============================================================
st.subheader("📝 Step 4 — Subtitle")

use_sub = st.toggle("စာတန်းထိုး (Burn-in)", value=True)

# ပုံသေ တန်ဖိုး — Slider မလိုဘူး
fs = FIXED_FONT_SIZE     # 30
bh = FIXED_BOX_HEIGHT    # 100
ba = FIXED_OPACITY       # 100

if use_sub:
    st.caption(f"🔤 Font {fs}  •  ⬛ Box {bh}px  •  🎨 Opacity {ba}")

# ============================================================
# Preview
# ============================================================
if vid and use_sub:
    st.markdown("**🖼️ Preview**")
    with st.spinner("Preview ဖန်တီးနေသည်..."):
        vid.seek(0)
        with open("preview.mp4", "wb") as f:
            f.write(vid.read())
        W, H, _ = vid_info("preview.mp4")
        render_png("စာတန်းထိုး Preview", "prev.png", FONT_FILE, W, H, fs, "center", bh, ba)
        cap = cv2.VideoCapture("preview.mp4")
        ok, fr = cap.read()
        cap.release()
        if ok:
            bg = Image.fromarray(cv2.cvtColor(fr, cv2.COLOR_BGR2RGB)).convert("RGBA")
            fg = Image.open("prev.png").convert("RGBA")
            comp = Image.alpha_composite(bg, fg)
            pw = 720
            comp.resize((pw, int(H*(pw/W))), Image.LANCZOS).convert("RGB").save("prev_out.png")
            st.image("prev_out.png", use_container_width=True)

st.divider()

# ============================================================
# Step 5 — Generate
# ============================================================
st.subheader("🚀 Step 5 — Generate Recap")

if st.button("✨ Generate Recap Video", type="primary", use_container_width=True):
    if not script.strip():
        st.error("Script paste လုပ်ပါ — Step 2")
        st.stop()
    if vid is None:
        st.error("Video Upload တင်ပါ — Step 3")
        st.stop()

    vid.seek(0)
    with open("input.mp4", "wb") as f:
        f.write(vid.read())
    _, _, vdur = vid_info("input.mp4")

    pb = st.progress(0)
    txt = st.empty()

    def cb(i, tot, c):
        pb.progress((i + 1) / tot)
        txt.caption(f"[{i+1}/{tot}] {len(c)} စာလုံး")

    try:
        tts_all(script, "voice.mp3", st.session_state.ref, cb)
    except Exception as e:
        st.error(f"TTS Error — {e}")
        st.stop()

    adur = float(ffmpeg.probe("voice.mp3")['format']['duration'])
    tempo = max(0.5, min(2.0, adur / vdur))

    sp = None
    if use_sub:
        sp = scr_to_srt(script, vdur, "sub.srt")

    with st.spinner("🎬 Rendering..."):
        vi = ffmpeg.input("input.mp4")
        va = ffmpeg.input("voice.mp3").audio.filter('atempo', tempo)
        ffmpeg.output(vi.video, va, "temp.mp4",
                       vcodec='libx264', crf=18, preset='medium',
                       acodec='aac', audio_bitrate='192k', shortest=None
                       ).run(overwrite_output=True)
        if use_sub and sp:
            overlay("temp.mp4", sp, "final.mp4", FONT_FILE, fs, "center", bh, ba)
        else:
            shutil.copy("temp.mp4", "final.mp4")

    st.success(f"✅ Done — {adur:.0f}s @ {tempo:.2f}x")
    st.video("final.mp4")

    with open("final.mp4", "rb") as f:
        st.download_button("📥 Download Recap Video", f, file_name="recap.mp4")

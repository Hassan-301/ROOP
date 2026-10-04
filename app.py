import os, shutil, subprocess, tempfile, urllib.request
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.background import BackgroundTask

app = FastAPI(title="Roop Studio")
DEMO = (os.getenv("DEMO_EMAIL", "demo@roop.test"), os.getenv("DEMO_PASSWORD", "Demo@12345"))
MODELS = Path(os.getenv("MODEL_DIR", "models")); MODELS.mkdir(exist_ok=True)
LIPSYNC_CMD = os.getenv("LIPSYNC_CMD")  # optional GPU step, e.g. "python infer.py --face {face} --audio {audio} --out {out}"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
# id: (locale, name, quality, label)
VOICES = {
    "lessac": ("en_US", "lessac", "medium", "Lessac - US woman"),
    "amy":    ("en_US", "amy", "medium", "Amy - US woman"),
    "ryan":   ("en_US", "ryan", "medium", "Ryan - US man"),
    "joe":    ("en_US", "joe", "medium", "Joe - US man"),
    "alan":   ("en_GB", "alan", "medium", "Alan - British man"),
    "alba":   ("en_GB", "alba", "medium", "Alba - Scottish woman"),
}
_whisper = None

def run(cmd, **kw):
    try:
        return subprocess.run(cmd, check=True, capture_output=True, **kw)
    except subprocess.CalledProcessError as e:
        raise HTTPException(500, f"Step failed: {(e.stderr or b'').decode()[-300:]}")

def voice_file(key):
    loc, name, q, _ = VOICES[key]
    f = MODELS / f"{loc}-{name}-{q}.onnx"
    if not f.exists():
        base = f"https://huggingface.co/rhasspy/piper-voices/resolve/main/{loc[:2]}/{loc}/{name}/{q}/{loc}-{name}-{q}"
        for ext in (".onnx.json", ".onnx"):
            urllib.request.urlretrieve(base + ext, str(MODELS / f"{loc}-{name}-{q}{ext}"))
    return f

def transcribe(wav):
    global _whisper
    if _whisper is None:
        from faster_whisper import WhisperModel
        _whisper = WhisperModel(os.getenv("WHISPER_MODEL", "base"), device="cpu", compute_type="int8")
    segs, _ = _whisper.transcribe(str(wav))
    return " ".join(s.text.strip() for s in segs).strip()

@app.get("/api/voices")
def voices():
    return [{"id": k, "label": v[3]} for k, v in VOICES.items()]

@app.post("/api/make")
async def make(email: str = Form(...), password: str = Form(...), voice: str = Form(...),
               consent: bool = Form(False), video: UploadFile = File(...), photo: UploadFile = File(None)):
    if (email, password) != DEMO: raise HTTPException(401, "Wrong demo credentials.")
    if not consent: raise HTTPException(400, "Please confirm the video, voice and photo are yours or licensed.")
    if voice not in VOICES: raise HTTPException(400, "Unknown voice.")
    d = Path(tempfile.mkdtemp())
    try:
        vin = d / "in.mp4"; vin.write_bytes(await video.read())
        run(["ffmpeg", "-y", "-i", str(vin), "-vn", "-ac", "1", "-ar", "16000", str(d / "a.wav")])
        text = transcribe(d / "a.wav")
        if not text: raise HTTPException(400, "No speech found in the video.")
        run(["piper", "--model", str(voice_file(voice)), "--output_file", str(d / "v.wav")], input=text.encode())
        wm = (f"drawtext=fontfile={FONT}:text='AI-generated voice and avatar':fontcolor=white:fontsize=26:"
              "box=1:boxcolor=black@0.6:boxborderw=8:x=(w-text_w)/2:y=h-70")
        out = d / "out.mp4"
        if photo is not None and photo.filename:
            face = d / "face.jpg"; face.write_bytes(await photo.read())
            src = face
            if LIPSYNC_CMD:
                run(LIPSYNC_CMD.format(face=face, audio=d / "v.wav", out=d / "ls.mp4"), shell=True)
                run(["ffmpeg", "-y", "-i", str(d / "ls.mp4"), "-vf", wm, "-c:a", "copy", str(out)])
            else:
                run(["ffmpeg", "-y", "-loop", "1", "-i", str(face), "-i", str(d / "v.wav"), "-vf",
                     "scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280," + wm,
                     "-shortest", "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p", "-c:a", "aac", str(out)])
        else:
            run(["ffmpeg", "-y", "-i", str(vin), "-i", str(d / "v.wav"), "-map", "0:v:0", "-map", "1:a:0",
                 "-vf", wm, "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(out)])
        return FileResponse(out, media_type="video/mp4", filename="roop.mp4",
                            background=BackgroundTask(shutil.rmtree, d, ignore_errors=True))
    except Exception:
        shutil.rmtree(d, ignore_errors=True); raise

app.mount("/", StaticFiles(directory="static", html=True), name="static")

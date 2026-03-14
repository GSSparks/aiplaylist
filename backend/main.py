from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response

import subprocess
import requests
import json
import os
import glob
import random
import difflib
import string
import tempfile

from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote, urljoin, unquote

from fastapi.staticfiles import StaticFiles

# Mount frontend folder
app.mount("/", StaticFiles(directory="../frontend", html=True), name="frontend")

try:
    from mutagen import File as MutagenFile
    MUTAGEN_AVAILABLE = True
except Exception:
    MUTAGEN_AVAILABLE = False

# ---------------- CONFIG ----------------

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LOCAL_LLM_URL = "http://localhost:8080/v1/chat/completions"
LOCAL_MUSIC_DIR = "/mnt/server/Music"

NUM_TRACKS = 12
LIB_INDEX = []

if not OPENAI_API_KEY:
    print("⚠️ OPENAI_API_KEY not set")

# ---------------- FASTAPI ----------------

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- MODELS ----------------

class Prompt(BaseModel):
    prompt: str
    mode: str = "openai"   # "openai" or "local"
    source: str = "youtube"  # "youtube" or "local"

# ---------------- UTILITIES ----------------

def safe_json(text: str):
    """
    Parse JSON returned by an LLM and normalize to {"playlist": ["Song - Artist", ...]}.
    Handles:
      - {"playlist": ["Song - Artist", ...]}
      - {"songs": [{"title": "...", "artist": "..."}, ...]}
      - LLM returning extra text around JSON
    """
    # strip code blocks
    text = text.replace("```json", "").replace("```", "").strip()

    try:
        data = json.loads(text)
    except Exception:
        print("⚠️ Invalid JSON from LLM:")
        print(text)
        return None

    # Case: LLM returned "songs" array
    if "songs" in data:
        return {"playlist": [f"{s.get('title','')} - {s.get('artist','')}".strip(" -") for s in data["songs"]]}

    # Case: LLM returned "playlist" key
    if "playlist" in data and isinstance(data["playlist"], list):
        # ensure all items are strings in "Song - Artist" format
        return {"playlist": [str(i) for i in data["playlist"]]}

    # fallback: try to flatten any list of dicts
    if isinstance(data, list) and all(isinstance(i, dict) for i in data):
        playlist = []
        for item in data:
            title = item.get("title", "")
            artist = item.get("artist", "")
            if title:
                playlist.append(f"{title} - {artist}".strip(" -"))
        if playlist:
            return {"playlist": playlist}

    # unknown format
    return None

# ---------------- LLM PLAYLIST ----------------

def generate_playlist_openai(prompt: str):
    payload = {
        "model": "gpt-4o",
        "messages": [
            {"role": "user",
             "content": f"Create a JSON playlist of {NUM_TRACKS} songs for: '{prompt}'. "
                        "Return ONLY JSON with a single key 'playlist' containing a list of 'Song Title - Artist' strings."}
        ],
        "temperature": 0.7
    }
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    r = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=60)
    r.raise_for_status()
    data = safe_json(r.json()["choices"][0]["message"]["content"])
    return data.get("playlist", []) if data else []

def generate_playlist_local_llm(prompt: str):
    payload = {
        "model": "local-model",
        "messages": [
            {"role": "user",
             "content": f"Create JSON playlist of {NUM_TRACKS} songs for: '{prompt}'. "
                        "Return ONLY JSON with a single key 'playlist' containing a list of 'Song Title - Artist' strings."}
        ]
    }
    r = requests.post(LOCAL_LLM_URL, json=payload, timeout=300)
    r.raise_for_status()
    data = safe_json(r.json()["choices"][0]["message"]["content"])
    return data.get("playlist", []) if data else []

def generate_playlist(prompt: str, mode: str):
    try:
        songs = generate_playlist_local_llm(prompt) if mode == "local" else generate_playlist_openai(prompt)
        print("LLM songs:", songs)
        return songs
    except Exception as e:
        print("Playlist generation failed:", e)
        return []

# ---------------- YOUTUBE SEARCH ----------------

def search_youtube(song: str):
    cmd = ["yt-dlp", "-f", "bestaudio", f"ytsearch1:{song}", "--get-url", "--quiet"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    url = result.stdout.strip()
    if not url:
        print("YT search failed:", song)
    return url

# ---------------- LOCAL MUSIC INDEX ----------------

def index_library():
    global LIB_INDEX
    LIB_INDEX = []
    files = glob.glob(os.path.join(LOCAL_MUSIC_DIR, "**/*.mp3"), recursive=True)
    for p in files:
        try:
            basename = os.path.basename(p)
            title_guess = os.path.splitext(basename)[0]
            rel = os.path.relpath(p, LOCAL_MUSIC_DIR)
            parts = rel.split(os.sep)
            artist_guess = parts[0] if len(parts) >= 3 else ""
            title_tag, artist_tag = None, None
            if MUTAGEN_AVAILABLE:
                try:
                    m = MutagenFile(p, easy=True)
                    if m:
                        title_tag = m.get("title", [None])[0]
                        artist_tag = m.get("artist", [None])[0]
                except Exception:
                    pass
            title = title_tag or title_guess
            artist = artist_tag or artist_guess
            norm_title, norm_artist = normalize(title), normalize(artist)
            key = f"{norm_title} - {norm_artist}"
            LIB_INDEX.append({"path": p, "rel": rel, "title": title, "artist": artist,
                              "norm_title": norm_title, "norm_artist": norm_artist, "key": key})
        except Exception as e:
            print("Index error:", p, e)
    print(f"Indexed {len(LIB_INDEX)} tracks")

index_library()

def find_local_track(song_query: str):
    if not song_query:
        return None
    q = song_query.strip()
    title, artist = (q.split(" - ", 1) if " - " in q else (q, ""))
    key = f"{normalize(title)} - {normalize(artist)}"
    for entry in LIB_INDEX:
        if entry["key"] == key or entry["norm_title"] == normalize(title):
            return entry["path"]
    return None

def get_random_local_tracks():
    if not LIB_INDEX:
        index_library()
    sample = random.sample(LIB_INDEX, min(NUM_TRACKS, len(LIB_INDEX)))
    return [e["path"] for e in sample]

# ---------------- ROUTES ----------------

@app.post("/playlist")
def create_playlist(data: Prompt):
    songs = generate_playlist(data.prompt, data.mode)
    tracks = []

    if data.source == "local":
        for song in songs:
            path = find_local_track(song)
            if path:
                tracks.append({"title": os.path.basename(path),
                               "url": f"http://localhost:8000/local/{quote(os.path.relpath(path, LOCAL_MUSIC_DIR))}"})
        if not tracks:
            files = get_random_local_tracks()
            tracks = [{"title": os.path.basename(f),
                       "url": f"http://localhost:8000/local/{quote(os.path.relpath(f, LOCAL_MUSIC_DIR))}"} for f in files]
        return {"tracks": tracks}

    # Youtube mode
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(search_youtube, s): s for s in songs}
        for future in as_completed(futures):
            url = future.result()
            if url:
                tracks.append({"title": futures[future], "url": url})
    if not tracks:
        fallback = search_youtube("chill music mix")
        tracks.append({"title": "Fallback Mix", "url": fallback})
    return {"tracks": tracks}

@app.post("/stt")
async def stt(file: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
    segments, _ = stt_model.transcribe(tmp_path)
    os.unlink(tmp_path)
    return {"text": " ".join(seg.text for seg in segments)}

@app.get("/local/{path:path}")
def serve_local_mp3(path: str):
    safe_path = os.path.normpath(unquote(path)).lstrip("/")
    if safe_path.startswith(".."):
        raise HTTPException(400)
    full_path = os.path.join(LOCAL_MUSIC_DIR, safe_path)
    if not os.path.isfile(full_path):
        raise HTTPException(404)
    return StreamingResponse(open(full_path, "rb"), media_type="audio/mpeg", headers={"Access-Control-Allow-Origin": "*"})

@app.get("/proxy")
def proxy(url: str):
    if url.endswith(".m3u8"):
        r = requests.get(url)
        lines = r.text.splitlines()
        for i, line in enumerate(lines):
            if line and not line.startswith("#"):
                lines[i] = f"/proxy?url={quote(urljoin(url, line))}"
        return Response("\n".join(lines), media_type="application/vnd.apple.mpegurl", headers={"Access-Control-Allow-Origin": "*"})
    r = requests.get(url, stream=True)
    return StreamingResponse(r.iter_content(1024 * 1024), media_type="video/MP2T", headers={"Access-Control-Allow-Origin": "*"})

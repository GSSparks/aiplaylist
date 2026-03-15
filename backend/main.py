from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

import subprocess
import requests
import json
import os
import glob
import random
import difflib
import string
import logging

from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote, urljoin, unquote

try:
    from mutagen import File as MutagenFile
    MUTAGEN_AVAILABLE = True
except Exception:
    MUTAGEN_AVAILABLE = False


# ---------------- LOGGING ----------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

log = logging.getLogger("aiplaylist")


# ---------------- CONFIG ----------------

ENV_FILE = os.getenv("ENV_FILE", ".env")

if os.path.exists(ENV_FILE):
    load_dotenv(ENV_FILE)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

LOCAL_LLM_URL = os.getenv(
    "LOCAL_LLM_URL",
    "http://localhost:8080/v1/chat/completions"
)

LOCAL_MUSIC_DIR = os.getenv(
    "LOCAL_MUSIC_DIR",
    "/mnt/server/Music"
)

API_PORT = int(os.getenv("PORT", "8000"))

NUM_TRACKS = int(os.getenv("NUM_TRACKS", "12"))

BASE_URL = os.getenv(
    "BASE_URL",
    f"http://localhost:{API_PORT}"
)

ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "*"
).split(",")

PROXY_ALLOWED_DOMAINS = os.getenv(
    "PROXY_ALLOWED_DOMAINS",
    "googlevideo.com,youtube.com,ytimg.com"
).split(",")

ENABLE_PROXY = os.getenv("ENABLE_PROXY", "true").lower() == "true"

LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "60"))

MAX_WORKERS = int(os.getenv("YT_WORKERS", "4"))

LIB_INDEX = []

log.info("Configuration:")
log.info(" LOCAL_LLM_URL=%s", LOCAL_LLM_URL)
log.info(" LOCAL_MUSIC_DIR=%s", LOCAL_MUSIC_DIR)
log.info(" PORT=%s", API_PORT)


# ---------------- FASTAPI ----------------

app = FastAPI(title="aiplaylist")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS if ALLOWED_ORIGINS != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/app", StaticFiles(directory="../frontend", html=True), name="frontend")
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

# ---------------- MODELS ----------------

class Prompt(BaseModel):
    prompt: str = Field(min_length=1, max_length=300)
    mode: str = Field(default="openai")
    source: str = Field(default="youtube")


# ---------------- UTILITIES ----------------

def normalize(text: str):
    text = text.lower()
    text = text.translate(str.maketrans("", "", string.punctuation))
    return text.strip()


def safe_json(text: str):

    text = text.replace("```json", "").replace("```", "").strip()

    try:
        data = json.loads(text)
    except Exception:
        log.warning("Invalid JSON from LLM")
        return None

    if "songs" in data:
        return {"playlist": [
            f"{s.get('title','')} - {s.get('artist','')}".strip(" -")
            for s in data["songs"]
        ]}

    if "playlist" in data and isinstance(data["playlist"], list):
        return {"playlist": [str(i) for i in data["playlist"]]}

    if isinstance(data, list) and all(isinstance(i, dict) for i in data):
        playlist = []
        for item in data:
            title = item.get("title", "")
            artist = item.get("artist", "")
            if title:
                playlist.append(f"{title} - {artist}".strip(" -"))
        if playlist:
            return {"playlist": playlist}

    return None


# ---------------- LLM PLAYLIST ----------------

def generate_playlist_openai(prompt: str):

    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY not configured")

    payload = {
        "model": "gpt-4o",
        "messages": [
            {"role": "user",
             "content": f"Create a JSON playlist of {NUM_TRACKS} songs for: '{prompt}'. "
                        "Return ONLY JSON with a single key 'playlist' containing a list of 'Song Title - Artist' strings."}
        ],
        "temperature": 0.7
    }

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    r = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=LLM_TIMEOUT
    )

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

    r = requests.post(
        LOCAL_LLM_URL,
        json=payload,
        timeout=LLM_TIMEOUT
    )

    r.raise_for_status()

    data = safe_json(r.json()["choices"][0]["message"]["content"])

    return data.get("playlist", []) if data else []


def generate_playlist(prompt: str, mode: str):

    try:
        songs = (
            generate_playlist_local_llm(prompt)
            if mode == "local"
            else generate_playlist_openai(prompt)
        )

        log.info("LLM songs: %s", songs)

        return songs

    except Exception as e:
        log.error("Playlist generation failed: %s", e)
        return []


# ---------------- YOUTUBE SEARCH ----------------

def search_youtube(song: str):

    try:
        cmd = [
            "yt-dlp",
            "-f",
            "bestaudio",
            f"ytsearch1:{song}",
            "--get-url",
            "--quiet"
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        url = result.stdout.strip()

        return url

    except Exception as e:
        log.warning("YT search failed: %s", e)
        return None


# ---------------- LOCAL MUSIC INDEX ----------------

def index_library():

    global LIB_INDEX
    LIB_INDEX = []

    files = glob.glob(
        os.path.join(LOCAL_MUSIC_DIR, "**/*.mp3"),
        recursive=True
    )

    for p in files:

        try:

            basename = os.path.basename(p)
            title_guess = os.path.splitext(basename)[0]

            rel = os.path.relpath(p, LOCAL_MUSIC_DIR)
            parts = rel.split(os.sep)

            artist_guess = parts[0] if len(parts) >= 3 else ""

            title_tag = None
            artist_tag = None

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

            norm_title = normalize(title)
            norm_artist = normalize(artist)

            key = f"{norm_title} - {norm_artist}"

            LIB_INDEX.append({
                "path": p,
                "rel": rel,
                "title": title,
                "artist": artist,
                "norm_title": norm_title,
                "norm_artist": norm_artist,
                "key": key
            })

        except Exception:
            continue

    log.info("Indexed %s tracks", len(LIB_INDEX))


index_library()


def find_local_track(song_query: str):

    if not song_query:
        return None

    q = song_query.strip()

    title, artist = (
        q.split(" - ", 1)
        if " - " in q else (q, "")
    )

    key = f"{normalize(title)} - {normalize(artist)}"

    for entry in LIB_INDEX:
        if entry["key"] == key or entry["norm_title"] == normalize(title):
            return entry["path"]

    return None


def get_random_local_tracks():

    if not LIB_INDEX:
        index_library()

    sample = random.sample(
        LIB_INDEX,
        min(NUM_TRACKS, len(LIB_INDEX))
    )

    return [e["path"] for e in sample]


# ---------------- ROUTES ----------------

@app.post("/playlist")
@limiter.limit("10/minute")
def create_playlist(request: Request, data: Prompt):

    songs = generate_playlist(data.prompt, data.mode)

    tracks = []

    if data.source == "local":

        for song in songs:

            path = find_local_track(song)

            if path:

                rel = os.path.relpath(path, LOCAL_MUSIC_DIR)

                tracks.append({
                    "title": os.path.basename(path),
                    "url": f"{BASE_URL}/local/{quote(rel)}"
                })

        if not tracks:

            files = get_random_local_tracks()

            tracks = [{
                "title": os.path.basename(f),
                "url": f"{BASE_URL}/local/{quote(os.path.relpath(f, LOCAL_MUSIC_DIR))}"
            } for f in files]

        return {"tracks": tracks}

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:

        futures = {
            executor.submit(search_youtube, s): s
            for s in songs
        }

        for future in as_completed(futures):

            url = future.result()

            if url:
                tracks.append({
                    "title": futures[future],
                    "url": url
                })

    if not tracks:

        fallback = search_youtube("chill music mix")

        tracks.append({
            "title": "Fallback Mix",
            "url": fallback
        })

    return {"tracks": tracks}


@app.get("/local/{path:path}")
def serve_local_mp3(path: str):

    safe_path = os.path.normpath(unquote(path)).lstrip("/")

    if safe_path.startswith(".."):
        raise HTTPException(400, "Invalid path")

    full_path = os.path.join(LOCAL_MUSIC_DIR, safe_path)

    if not os.path.isfile(full_path):
        raise HTTPException(404)

    def stream():
        with open(full_path, "rb") as f:
            while chunk := f.read(1024 * 1024):
                yield chunk

    return StreamingResponse(
        stream(),
        media_type="audio/mpeg"
    )


@app.get("/proxy")
def proxy(url: str):

    if not ENABLE_PROXY:
        raise HTTPException(403, "Proxy disabled")

    if not any(domain in url for domain in PROXY_ALLOWED_DOMAINS):
        raise HTTPException(403, "Domain not allowed")

    if url.endswith(".m3u8"):

        r = requests.get(url, timeout=30)

        lines = r.text.splitlines()

        for i, line in enumerate(lines):

            if line and not line.startswith("#"):
                lines[i] = f"/proxy?url={quote(urljoin(url, line))}"

        return Response(
            "\n".join(lines),
            media_type="application/vnd.apple.mpegurl"
        )

    r = requests.get(url, stream=True, timeout=30)

    return StreamingResponse(
        r.iter_content(1024 * 1024),
        media_type="video/MP2T"
    )

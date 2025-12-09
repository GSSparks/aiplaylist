from fastapi import FastAPI
from pydantic import BaseModel
import subprocess
import requests
import json
from dotenv import load_dotenv
import os
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.responses import Response


# Load .env variables
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY not found in environment")

app = FastAPI()

# Enable CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # OK for local development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

NUM_TRACKS = 12

class Prompt(BaseModel):
    prompt: str


def generate_playlist(prompt: str):
    env = os.environ.copy()
    env["OPENAI_API_KEY"] = OPENAI_API_KEY

    result = subprocess.run(
        [
            "openai", "api", "chat.completions.create",
            "-m", "gpt-4o",
            "-g", "user",
            f"Create a JSON object with a key 'playlist' containing {NUM_TRACKS} songs that match this prompt: '{prompt}'. Return ONLY raw JSON. No markdown. No backticks."
        ],
        capture_output=True,
        text=True,
        env=env
    )

    if result.returncode != 0:
        raise RuntimeError(f"OpenAI CLI error: {result.stderr}")

    raw = result.stdout.strip()

    if not raw:
        raise RuntimeError("OpenAI returned empty output")

    # ✅ Strip markdown fences BEFORE parsing
    if raw.startswith("```"):
        raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        raise RuntimeError(f"Invalid JSON from OpenAI: {raw}")

    return parsed["playlist"]



def search_youtube(song: str):
    result = subprocess.run(
        ["yt-dlp", "-x", "-f 234", f"ytsearch1:{song}", "--get-url"],
        capture_output=True,
        text=True
    )

    return result.stdout.strip()


@app.post("/playlist")
def create_playlist(data: Prompt):
    songs = generate_playlist(data.prompt)
    tracks = []

    for song in songs:
        url = search_youtube(song)
        if url:
            tracks.append({
                "title": song,
                "url": url
            })

    return {"tracks": tracks}

@app.get("/proxy")
def proxy(url: str):
    # Detect if this is a playlist
    if url.endswith(".m3u8"):
        r = requests.get(url)
        content = r.text
        lines = content.splitlines()
        for i, line in enumerate(lines):
            if line and not line.startswith("#"):
                # rewrite each segment to go through proxy
                lines[i] = f"/proxy?url={requests.utils.quote(requests.compat.urljoin(url, line))}"
        content = "\n".join(lines)
        return Response(
            content,
            media_type="application/vnd.apple.mpegurl",
            headers={"Access-Control-Allow-Origin": "*"}
        )

    # Otherwise, treat it as a segment
    else:
        r = requests.get(url, stream=True)
        return StreamingResponse(
            r.iter_content(chunk_size=1024*1024),
            media_type="video/MP2T",
            headers={"Access-Control-Allow-Origin": "*"}
        )


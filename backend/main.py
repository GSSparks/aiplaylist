from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
import subprocess
import json
import os
from dotenv import load_dotenv

# Load .env and initialize OpenAI client
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY not set in .env")
client = OpenAI(api_key=api_key)

app = FastAPI()

# CORS: Adjust as needed (Vite default = localhost:5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PromptRequest(BaseModel):
    prompt: str

@app.post("/generate")
async def generate_playlist(req: PromptRequest):
    prompt = req.prompt.strip()
    if not prompt:
        return {"error": "Prompt is empty."}

    gpt_prompt = (
        f"Create a JSON object with a key 'playlist' containing 12 songs that match this prompt: '{prompt}'. "
        "Respond ONLY with valid JSON. No markdown formatting, no explanation. Format: "
        "{\"playlist\": [\"artist - title\"]}"
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": gpt_prompt}],
        )
        content = response.choices[0].message.content.strip()

        # Clean any markdown code fences
        if content.startswith("```json"):
            content = content[len("```json"):].strip()
        if content.endswith("```"):
            content = content[:-3].strip()

        playlist_data = json.loads(content)
        playlist = playlist_data.get("playlist", [])

    except Exception as e:
        return {"error": f"Failed to generate or parse playlist: {str(e)}"}

    results = []

    for song in playlist:
        try:
            # Get audio URL via yt-dlp
            json_data = subprocess.check_output([
                "yt-dlp", f"ytsearch1:{song}",
                "--no-playlist", "--quiet", "--dump-json"
            ]).decode("utf-8")

            video_info = json.loads(json_data)
            formats = video_info.get("formats", [])

            # Select best audio-only stream
            best_audio = next(
                (f for f in formats if f.get("acodec") != "none" and f.get("vcodec") == "none"),
                None
            )

            audio_url = best_audio.get("url") if best_audio else None
            results.append({"title": song, "audio_url": audio_url})

        except subprocess.CalledProcessError:
            results.append({"title": song, "audio_url": None})

    return {"results": results}

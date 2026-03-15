# 🎶 aiplaylist

**aiplaylist** is an AI-powered playlist generator that turns natural language prompts into playable music playlists.

Give it a prompt like:

> *"lofi beats for late night coding"*

> *"80s workout montage music"*

> *"soft piano music for studying"*

…and **aiplaylist** will generate a playlist and stream the tracks automatically.

The project combines a **FastAPI backend**, a **lightweight web frontend**, and AI-powered playlist generation to create a simple local-first music discovery tool.

This project is designed for **learning, experimentation, and self-hosting**.

---

# ✨ Features

* 🎧 Generate playlists from natural language prompts
* 🤖 AI-curated song lists
* 🌐 Web-based playlist interface
* ▶️ Automatic track playback
* 📡 Streaming via HLS
* 🔎 YouTube search via `yt-dlp`
* 💿 Optional local music library support
* 🐳 Easy container deployment with Docker

---

# 🧱 Tech Stack

| Component   | Technology              |
| ----------- | ----------------------- |
| Backend     | FastAPI                 |
| Frontend    | HTML + JavaScript       |
| Streaming   | HLS.js                  |
| Media Tools | yt-dlp                  |
| AI          | OpenAI API or local LLM |
| Container   | Docker                  |

---

# 📦 Project Structure

```
aiplaylist/
│
├─ backend/
│   ├─ main.py
│   ├─ requirements.txt
│   └─ .env
│
├─ frontend/
│   └─ index.html
│
├─ Dockerfile
└─ README.md
```

---

# 🚀 Getting Started (Local Development)

## 1️⃣ Clone the repository

```
git clone https://github.com/yourusername/aiplaylist.git
cd aiplaylist
```

---

## 2️⃣ Create `.env`

Create a `.env` file inside the **backend directory**:

```
OPENAI_API_KEY=your_openai_key_here
```

Optional variables:

```
LOCAL_LLM_URL=http://localhost:8080/v1/chat/completions
LOCAL_MUSIC_DIR=/mnt/server/Music
PORT=8000
NUM_TRACKS=12
```

---

## 3️⃣ Install dependencies

System tools required:

* Python
* pip
* yt-dlp
* ffmpeg

Install Python packages:

```
pip install fastapi uvicorn python-dotenv requests
```

---

## 4️⃣ Run the backend

```
cd backend

uvicorn main:app --host 0.0.0.0 --port 8000
```

---

## 5️⃣ Run the frontend

Open the frontend directly or serve it locally:

```
cd frontend
python3 -m http.server 8080
```

Visit:

```
http://localhost:8080
```

---

# 🐳 Running with Docker

Docker is the easiest way to run **aiplaylist**.

## 1️⃣ Build the container

From the project root:

```
docker build -t aiplaylist .
```

---

## 2️⃣ Create an `.env` file

Example:

```
OPENAI_API_KEY=your_openai_api_key

LOCAL_LLM_URL=http://localhost:8080/v1/chat/completions

LOCAL_MUSIC_DIR=/music

PORT=8000

NUM_TRACKS=12
```

---

## 3️⃣ Run the container

```
docker run \
-p 8000:8000 \
--env-file backend/.env \
-v /mnt/server/Music:/music \
aiplaylist
```

Then open:

```
http://localhost:8000/app
```

---

# ⚙️ Environment Variables

| Variable          | Description                     | Default                                     |
| ----------------- | ------------------------------- | ------------------------------------------- |
| `OPENAI_API_KEY`  | OpenAI API key                  | required                                    |
| `LOCAL_LLM_URL`   | URL for local LLM API           | `http://localhost:8080/v1/chat/completions` |
| `LOCAL_MUSIC_DIR` | Directory for local music files | `/music`                                    |
| `PORT`            | FastAPI server port             | `8000`                                      |
| `NUM_TRACKS`      | Number of songs per playlist    | `12`                                        |

---

# 🎵 Example Prompts

Try prompts like:

```
90s alternative road trip music
lofi beats for studying
classic rock workout playlist
chill electronic sunset vibes
video game boss battle music
```

---

# ⚠️ Legal Note

This project is intended for **local development and experimentation**.

If deploying publicly, you should use **official streaming APIs** such as:

* YouTube IFrame Player API
* Spotify Web API
* Apple Music API

instead of proxying or restreaming media.

---

# 🎯 Project Goals

This project explores:

* AI-assisted media generation
* Local-first applications
* Lightweight self-hosted tools
* DevOps-friendly containerized software

---

# 🧪 Future Ideas

Possible improvements:

* Spotify integration
* Playlist saving
* Music recommendation feedback
* Voice prompt input
* Home Assistant integration
* Local LLM playlist generation
* Full React frontend

---

# 📜 License

MIT License

---

⭐ If you find this project interesting, consider giving it a star!

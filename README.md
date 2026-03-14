# 🎶 aiplaylist

**aiplaylist** is an AI-powered music playlist generator that turns natural language prompts into playable playlists. It combines a FastAPI backend with a lightweight HTML/JavaScript frontend to search, generate, and stream music.

This project is built for learning, experimentation, and local use.

---

## ✨ Features

- Generate playlists from text prompts (e.g., *"80s training montage music"*)
- AI-curated song lists
- Web-based playlist UI
- Auto-playing tracks
- Local streaming via HLS
- FastAPI backend

---

## 🧱 Tech Stack

- **Backend:** FastAPI (Python)
- **Frontend:** HTML + JavaScript
- **Streaming:** HLS.js
- **Media tools:** yt-dlp
- **AI:** OpenAI CLI

---

## 🚀 Getting Started

### 1. Clone the repo

```bash
git clone https://github.com/yourusername/aiplay.git
cd aiplay
```

### 2. Create and configure `.env`
Create a .env file in the backend/ directory:

```bash
OPENAI_API_KEY=your_api_key_here
```

### 3. Install dependencies

Make sure these tools are installed:

- `python`
- `pip`
- `yt-dlp`
- `openai CLI`

Python packages:

```bash
pip install fastapi uvicorn python-dotenv requests
```

### 4. Run the backend

```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 5. Run the frontend

Open `index.html` in your browser or serve it with:

```bash
python3 -m http.server 8080
```

Then visit:
```bash
http://localhost:8080
```

### Or run it Containerized

Clone the repo, add your `.env` file with your OpenAI api key in the `backend` directory. Then from the root directory:
```
docker build aiplay:latest .
```
Then
```
docker run -p 8000:8000 aiplay:latest
```

## ⚠️ Legal Note

This project is intended for local development and personal learning. If you plan to deploy it publicly, you should use official streaming APIs (such as the YouTube IFrame Player) instead of proxying or re-streaming content.

## Project Goal

This project is part of a larger effort to explore:
- AI-assisted media generation
- Local-first applications
- DevOps-friendly tooling

## License

MIT License

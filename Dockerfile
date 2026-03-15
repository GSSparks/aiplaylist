FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
ENV PORT=8000
ENV LOCAL_MUSIC_DIR=/music
ENV LOCAL_LLM_URL=http://localhost:8080/v1/chat/completions
ENV ENV_FILE=/app/.env

RUN apt-get update && \
    apt-get install -y ffmpeg curl wget git && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir yt-dlp

COPY backend/ ./backend/
COPY frontend/ ./frontend/

EXPOSE ${PORT}

WORKDIR /app/backend

CMD uvicorn main:app --host 0.0.0.0 --port ${PORT}

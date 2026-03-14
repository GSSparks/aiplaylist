# Use latest Python
FROM python:3.12-slim

# Set environment
ENV PYTHONUNBUFFERED=1
ENV LOCAL_MUSIC_DIR=/mnt/server/Music

# Install system dependencies for audio + yt-dlp
RUN apt-get update && \
    apt-get install -y ffmpeg curl wget git && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir yt-dlp

# Copy backend + frontend
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# Expose port
EXPOSE 8000

# Serve frontend + backend via FastAPI
WORKDIR /app/backend

# Start Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

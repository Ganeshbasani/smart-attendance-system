# Smart Attendance System - Backend (FastAPI + InsightFace, CPU)
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System libraries required by OpenCV / InsightFace
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Unprivileged runtime user; HOME points the InsightFace model cache at a
# directory this image owns (insightface resolves ~/.insightface via $HOME).
RUN useradd --create-home --shell /usr/sbin/nologin appuser
ENV HOME=/home/appuser

# Pre-download the InsightFace model pack so the image is self-contained
# (no model download on first request).
RUN python -c "from insightface.app import FaceAnalysis; a = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider']); a.prepare(ctx_id=-1, det_size=(640, 640))" \
    && chown -R appuser:appuser /home/appuser

# Runtime-writable dirs are created (and owned) BEFORE the copy so that a
# named volume mounted over /app/dataset inherits appuser ownership from
# the image instead of being created root-owned by the docker daemon.
RUN mkdir -p /app/uploads /app/dataset \
    && chown -R appuser:appuser /app

COPY --chown=appuser:appuser . .

USER appuser

# Hugging Face Spaces (and most PaaS) provide the listen port via $PORT.
# Default to 8000 for local `docker run`.
ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

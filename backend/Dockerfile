FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

ENV DATABASE_URL=sqlite+aiosqlite:///./data/keystroke_sentinel.db
ENV MODEL_STORAGE_PATH=./data/models
ENV ANOMALY_THRESHOLD=0.65
ENV ENROLLMENT_MIN_KEYSTROKES=300
ENV CORS_ORIGINS=["http://localhost:5173","http://localhost:4173","http://localhost:80"]

EXPOSE 8000
# --workers 1 required: enrollment buffers and session state are in-process dicts
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

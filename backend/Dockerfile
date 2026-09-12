# =========================================================
# Backend Dockerfile — FastAPI + LangGraph agent
# =========================================================

FROM python:3.11-slim

# Prevents Python from buffering stdout/stderr — logs show up immediately
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first so Docker can cache this layer
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the backend source code.
# .env, credentials.json and token.json are excluded via .dockerignore —
# they are mounted into the container at runtime instead (see docker-compose.yml).
COPY . .

EXPOSE 8000

CMD ["python", "agent.py"]

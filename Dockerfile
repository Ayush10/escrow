FROM python:3.12-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY server/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt python-dotenv httpx

# Copy server + frontend
COPY server/ /app/server/
COPY judge-frontend/ /app/judge-frontend/

WORKDIR /app/server

EXPOSE 8402

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8402"]

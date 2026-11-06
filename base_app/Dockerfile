FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Set default environment variables
ENV HOST=0.0.0.0
ENV PORT=7860
ENV DATABASE_URL=sqlite+aiosqlite:///./sellphi.db
ENV GEMINI_MODEL=gemini-3.1-flash-lite

EXPOSE 7860

# Run uvicorn server
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]

FROM python:3.11-slim

# Set up non-root user with UID 1000 (Required for Hugging Face Spaces & container security)
RUN useradd -m -u 1000 user

ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PORT=7860 \
    DATABASE_URL=sqlite+aiosqlite:////home/user/app/sellphi.db \
    GEMINI_MODEL=gemini-3.1-flash-lite

WORKDIR $HOME/app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Switch to non-root user
USER user

# Install Python packages into user environment
COPY --chown=user:user requirements.txt $HOME/app/
RUN pip install --no-cache-dir --user -r requirements.txt

# Copy application files
COPY --chown=user:user . $HOME/app/

EXPOSE 7860

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]

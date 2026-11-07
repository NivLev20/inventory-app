# ---- Backend image: Flask API served by gunicorn ----
FROM python:3.12-slim

# Do not write .pyc files, print logs immediately
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first (this layer is cached between builds)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Run as a regular user, not root (security best practice)
RUN useradd --create-home appuser
USER appuser

EXPOSE 5000

# Docker checks the app is alive every 30 seconds
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')" || exit 1

# 1 worker + threads keeps Prometheus metrics accurate in a single process
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "4", "app:create_app()"]

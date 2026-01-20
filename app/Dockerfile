# Use a lightweight Python image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies (sometimes needed for scientific libraries)
RUN apt-get update && apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements first (caching layer for faster builds)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the actual code
COPY . .

# Run the API server
# --host 0.0.0.0 is crucial! It allows outside access from other containers.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

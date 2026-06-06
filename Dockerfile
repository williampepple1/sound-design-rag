FROM python:3.12-slim

WORKDIR /app

# Install system deps: Tesseract for OCR, build tools for sentence-transformers
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . .

# Expose HF Spaces default port
EXPOSE 7860

# Run the API server
CMD ["python", "api.py"]

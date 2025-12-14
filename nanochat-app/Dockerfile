FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .
COPY simple_tokenizer.py .

# Copy tokenizer files to /app (accessible by non-root user)
COPY tokenizer ./tokenizer

# Verify files
RUN ls -la /app/tokenizer/

EXPOSE 8080

ENV INFERENCE_URL=https://nanochat-model-jeremycaine-dev.apps.rm2.thpm.p1.openshiftapps.com/v2/models/nanochat-model/infer

CMD ["python", "app.py"]

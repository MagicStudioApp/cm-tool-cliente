FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8080
WORKDIR /app
RUN python -m venv /app/work/ocr-env && /app/work/ocr-env/bin/pip install --no-cache-dir rapidocr-onnxruntime==1.4.4 pillow==11.3.0
RUN apt-get update && apt-get install -y --no-install-recommends libglib2.0-0 libgl1 && rm -rf /var/lib/apt/lists/*
COPY server.py analysis_import.py analysis_ocr.py ./
COPY deployment/hosted.py ./hosted.py
RUN useradd --uid 10001 --create-home appuser
USER appuser
EXPOSE 8080
CMD ["python", "hosted.py"]

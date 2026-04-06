FROM python:3.11-slim

WORKDIR /app

# 시스템 패키지 (PyPDF2 + faiss-cpu 빌드용)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# 의존성 먼저 설치 (캐시 활용)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# 앱 코드 복사
COPY app ./app
COPY main.py ./

# 벡터 스토어 디렉터리
RUN mkdir -p /app/vector_store

EXPOSE 8000

ENV PYTHONUNBUFFERED=1 \
    VECTOR_STORE_PATH=/app/vector_store

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libx11-6 \
    libgl1 \
    libgomp1 \
    libxi6 \
    libxrender1 \
    curl \
    xz-utils \
    && rm -rf /var/lib/apt/lists/*

# Blender 4.2 LTS headless für blender-rigify Provider
RUN curl -L https://download.blender.org/release/Blender4.2/blender-4.2.8-linux-x64.tar.xz \
    | tar -xJ -C /opt/ \
    && ln -sf /opt/blender-4.2.8-linux-x64/blender /usr/local/bin/blender

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

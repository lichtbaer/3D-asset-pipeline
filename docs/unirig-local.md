# UniRig lokal

Rigging ohne Hugging-Face-Space: lokale Inferenz mit CUDA und UniRig-Checkpoint.

## Voraussetzungen

- CUDA-fähige GPU (empfohlen: >8 GB VRAM)
- PyTorch mit CUDA
- UniRig-Repository und Checkpoint auf der Maschine (oder in gemounteten Pfaden im Container)

## Checkpoint (einmalig, etwa 5 GB)

```bash
huggingface-cli download VAST-AI/UniRig --local-dir ./models/unirig/
```

## UniRig-Repository

```bash
git clone https://github.com/VAST-AI-Research/UniRig ./unirig/
cd unirig && pip install -r requirements.txt
```

## Umgebungsvariablen

In `.env` (oder Compose):

```
UNIRIG_MODEL_PATH=./models/unirig/
UNIRIG_REPO_PATH=./unirig/
```

## GPU in Docker

In `docker-compose.yml` den auskommentierten **GPU-Block** für den `api`-Service aktivieren, wenn die API UniRig im Container nutzen soll.

Ohne CUDA oder ohne Checkpoint wird der Provider **`unirig-local`** nicht registriert — die API startet dennoch.

# Blender 4.2 LTS headless – minimales Image für Rigging-PoC
# Leichtgewichtiger als blenderkit/headless-blender (ohne X11/VNC)
FROM debian:bookworm-slim

# Blender 4.2 LTS benötigt diese Runtime-Dependencies (auch headless)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglu1-mesa \
    libx11-6 \
    libxcb1 \
    libxrender1 \
    libxi6 \
    libxxf86vm1 \
    libsm6 \
    libxfixes3 \
    libxkbcommon0 \
    libxcb-xkb1 \
    wget \
    xz-utils \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Blender 4.2 LTS Tarball (ca. 250MB komprimiert)
ARG BLENDER_VERSION=4.2.8
ARG BLENDER_URL=https://download.blender.org/release/Blender4.2/blender-${BLENDER_VERSION}-linux-x64.tar.xz

RUN wget -q "${BLENDER_URL}" -O /tmp/blender.tar.xz \
    && tar -xf /tmp/blender.tar.xz -C /opt \
    && rm /tmp/blender.tar.xz \
    && mv /opt/blender-${BLENDER_VERSION}-linux-x64 /opt/blender

ENV PATH="/opt/blender:${PATH}"

# Rigify ist in Blender 4.x standardmäßig enthalten
# Kein weiterer Addon-Setup nötig

WORKDIR /workspace

# Kein ENTRYPOINT – Aufruf: docker compose run blender --background --python script.py -- ...
# Oder: docker compose run blender --version
ENTRYPOINT ["blender"]

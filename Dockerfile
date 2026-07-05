# Multi-stage build to add tools to n8n image
# This works around apk being stripped from the official image

# Stage 1: Build dependencies in Alpine
FROM alpine:3.23 AS builder

RUN apk add --no-cache \
    ffmpeg \
    git \
    openssh-client \
    graphicsmagick \
    jq \
    curl

# Stage 2: Copy to n8n image
FROM n8nio/n8n:latest

USER root

# Copy binaries and libraries from builder
COPY --from=builder /usr/bin/ffmpeg /usr/bin/ffmpeg
COPY --from=builder /usr/bin/ffprobe /usr/bin/ffprobe
COPY --from=builder /usr/bin/git /usr/bin/git
COPY --from=builder /usr/bin/gm /usr/bin/gm
COPY --from=builder /usr/bin/jq /usr/bin/jq
COPY --from=builder /usr/bin/curl /usr/bin/curl
COPY --from=builder /usr/lib/libav*.so* /usr/lib/
COPY --from=builder /usr/lib/libsw*.so* /usr/lib/
COPY --from=builder /usr/lib/libcurl*.so* /usr/lib/
COPY --from=builder /usr/lib/libjq*.so* /usr/lib/
COPY --from=builder /usr/lib/libonig*.so* /usr/lib/

# Install canvas native build dependencies (needed for pdfjs-dist PDF parsing)
# n8n base image is Debian bookworm-slim — use apt-get, NOT apk
# canvas provides DOMMatrix, CanvasRenderingContext2D etc. in Node.js
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    make \
    g++ \
    pkg-config \
    libcairo2-dev \
    libpango1.0-dev \
    libjpeg-dev \
    libgif-dev \
    librsvg2-dev \
    libpixman-1-dev \
    && rm -rf /var/lib/apt/lists/*

# Install canvas so n8n's pdfjs-dist can use DOMMatrix
RUN npm install -g canvas 2>/dev/null || \
    echo "canvas install attempted - PDF parsing may use fallback"

# Expose task broker port for external runners (n8n 2.0)
EXPOSE 5679

USER node

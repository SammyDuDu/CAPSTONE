#!/usr/bin/env bash
set -euo pipefail

echo "================================"
echo "KoSPA Build Script for Render.com"
echo "================================"

# Update package lists
echo "[1/4] Updating package lists..."
apt-get update -qq

# Install ffmpeg (required for audio conversion)
echo "[2/4] Installing ffmpeg..."
apt-get install -y ffmpeg

# Verify ffmpeg installation
echo "[3/4] Verifying ffmpeg..."
ffmpeg -version | head -n 1

# Install Python dependencies
echo "[4/4] Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "================================"
echo "Build completed successfully!"
echo "================================"

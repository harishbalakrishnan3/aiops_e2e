#!/bin/bash
set -e

# Infer OS and architecture
OS="$(uname | tr '[:upper:]' '[:lower:]')"
ARCH="$(uname -m)"

echo "Detected OS: $OS"
echo "Detected architecture: $ARCH"

# Helper: run a command as root (sudo if available, else direct if already root)
# Check if tar is available
HAS_TAR=true
if ! command -v tar >/dev/null 2>&1; then
  echo "tar not found, will use Python as fallback..."
  HAS_TAR=false
  
  # Check if Python is available
  if ! command -v python3 >/dev/null 2>&1 && ! command -v python >/dev/null 2>&1; then
    echo "Error: neither tar nor python is available"
    echo "Please install either tar or python in the base image"
    exit 1
  fi
fi

# Map architecture to what Prometheus uses
case "$ARCH" in
  x86_64) ARCH="amd64" ;;
  aarch64) ARCH="arm64" ;;
  arm64) ARCH="arm64" ;;
  *)
    echo "Unsupported architecture: $ARCH"
    exit 1
    ;;
esac

# Construct the download URL
VERSION="3.0.1"
URL="https://github.com/prometheus/prometheus/releases/download/v${VERSION}/prometheus-${VERSION}.${OS}-${ARCH}.tar.gz"
DOWNLOAD_DIR="./prometheus_download"
TARBALL="prometheus-${VERSION}.${OS}-${ARCH}.tar.gz"

echo "Downloading Prometheus binary from $URL..."
mkdir -p "$DOWNLOAD_DIR"
curl -L "$URL" -o "${DOWNLOAD_DIR}/${TARBALL}"

echo "Extracting Prometheus binary..."
if [ "$HAS_TAR" = true ]; then
  tar -xzf "${DOWNLOAD_DIR}/${TARBALL}" -C "$DOWNLOAD_DIR"
else
  # Use Python to extract tar.gz
  PYTHON_CMD=$(command -v python3 || command -v python)
  $PYTHON_CMD - <<EOF
import tarfile
import os

tarball_path = "${DOWNLOAD_DIR}/${TARBALL}"
extract_dir = "${DOWNLOAD_DIR}"

with tarfile.open(tarball_path, "r:gz") as tar:
    tar.extractall(path=extract_dir)
print(f"Extracted {tarball_path} using Python")
EOF
fi

cp "${DOWNLOAD_DIR}/prometheus-${VERSION}.${OS}-${ARCH}/prometheus" .
cp "${DOWNLOAD_DIR}/prometheus-${VERSION}.${OS}-${ARCH}/promtool" .

chmod +x prometheus promtool

rm -rf "$DOWNLOAD_DIR"

echo "Prometheus and promtool have been downloaded and extracted successfully"

#!/bin/bash

# Exit on error
set -e

# Infer OS and architecture
OS="$(uname | tr '[:upper:]' '[:lower:]')"
ARCH="$(uname -m)"

echo "Detected OS: $OS"
echo "Detected architecture: $ARCH"

# Map architecture to what Prometheus uses
case "$ARCH" in
  x86_64) ARCH="amd64" ;;
  aarch64) ARCH="arm64" ;;
  arm64) ARCH="arm64" ;;
  *) echo "Unsupported architecture: $ARCH"; exit 1 ;;
esac

# Construct the download URL
VERSION="3.0.1"
URL="https://github.com/prometheus/prometheus/releases/download/v${VERSION}/prometheus-${VERSION}.${OS}-${ARCH}.tar.gz"
DOWNLOAD_DIR="./prometheus_download"

# Download Prometheus binary
echo "Downloading Prometheus binary from $URL..."

# Use curl to download the tar and put it in the DOWNLOAD_DIR
mkdir -p "$DOWNLOAD_DIR"
curl -L "$URL" -o "${DOWNLOAD_DIR}/prometheus-${VERSION}.${OS}-${ARCH}.tar.gz"

# Extract the binary
echo "Extracting Prometheus binary..."
tar -xzf "${DOWNLOAD_DIR}/prometheus-${VERSION}.${OS}-${ARCH}.tar.gz" -C "$DOWNLOAD_DIR"

# Copy the binary to the project directory
cp "${DOWNLOAD_DIR}/prometheus-${VERSION}.${OS}-${ARCH}/prometheus" .
cp "${DOWNLOAD_DIR}/prometheus-${VERSION}.${OS}-${ARCH}/promtool" .

# Give execute permissions
chmod +x prometheus
chmod +x promtool

# Cleanup
rm -rf "$DOWNLOAD_DIR"

# Output
echo "Prometheus and promtool have been downloaded and extracted"
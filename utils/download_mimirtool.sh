#!/bin/bash

# Exit on error
set -e

# Infer OS and architecture
OS="$(uname | tr '[:upper:]' '[:lower:]')"
ARCH="$(uname -m)"

echo "Detected OS: $OS"
echo "Detected architecture: $ARCH"

# Map architecture to what mimirtool uses
case "$ARCH" in
  x86_64) ARCH="amd64" ;;
  aarch64) ARCH="arm64" ;;
  arm64) ARCH="arm64" ;;
  *) echo "Unsupported architecture: $ARCH"; exit 1 ;;
esac

# Construct the download URL
URL="https://github.com/grafana/mimir/releases/latest/download/mimirtool-${OS}-${ARCH}"

# Download mimirtool binary
echo "Downloading mimirtool from $URL..."
curl -fLo mimirtool "$URL"

# Give execute permissions
chmod +x mimirtool

# Output
echo "mimirtool has been downloaded and is ready to use"
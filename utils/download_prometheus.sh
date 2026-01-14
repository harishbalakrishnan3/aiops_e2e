#!/bin/bash

# Exit on error
set -e

# Infer OS and architecture
OS="$(uname | tr '[:upper:]' '[:lower:]')"
ARCH="$(uname -m)"

echo "Detected OS: $OS"
echo "Detected architecture: $ARCH"

# Ensure tar is installed
if ! command -v tar >/dev/null 2>&1; then
  echo "tar not found, attempting to install..."

  case "$OS" in
    linux)
      if command -v apt-get >/dev/null 2>&1; then
        sudo apt-get update
        sudo apt-get install -y tar
      elif command -v yum >/dev/null 2>&1; then
        sudo yum install -y tar
      elif command -v apk >/dev/null 2>&1; then
        apk add --no-cache tar
      else
        echo "Unsupported Linux distribution: cannot install tar automatically"
        exit 1
      fi
      ;;
    darwin)
      if command -v brew >/dev/null 2>&1; then
        brew install gnu-tar
      else
        echo "Homebrew not found. Please install tar manually."
        exit 1
      fi
      ;;
    *)
      echo "Unsupported OS for automatic tar installation: $OS"
      exit 1
      ;;
  esac
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

# Download Prometheus binary
echo "Downloading Prometheus binary from $URL..."
mkdir -p "$DOWNLOAD_DIR"
curl -L "$URL" -o "${DOWNLOAD_DIR}/${TARBALL}"

# Extract the binary
echo "Extracting Prometheus binary..."
tar -xzf "${DOWNLOAD_DIR}/${TARBALL}" -C "$DOWNLOAD_DIR"

# Copy binaries to the project directory
cp "${DOWNLOAD_DIR}/prometheus-${VERSION}.${OS}-${ARCH}/prometheus" .
cp "${DOWNLOAD_DIR}/prometheus-${VERSION}.${OS}-${ARCH}/promtool" .

# Give execute permissions
chmod +x prometheus promtool

# Cleanup
rm -rf "$DOWNLOAD_DIR"

# Output
echo "Prometheus and promtool have been downloaded and extracted successfully"

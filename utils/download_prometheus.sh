#!/bin/bash
set -e

# Infer OS and architecture
OS="$(uname | tr '[:upper:]' '[:lower:]')"
ARCH="$(uname -m)"

echo "Detected OS: $OS"
echo "Detected architecture: $ARCH"

# Helper: run a command as root (sudo if available, else direct if already root)
run_as_root() {
  if command -v sudo >/dev/null 2>&1; then
    sudo "$@"
  elif [ "$(id -u)" -eq 0 ]; then
    "$@"
  else
    echo "Error: need root privileges to run: $*"
    echo "This environment has no sudo and is not running as root."
    echo "Fix: install 'tar' in the base image / runner, or run this job as root."
    exit 1
  fi
}

# Ensure tar is installed
if ! command -v tar >/dev/null 2>&1; then
  echo "tar not found, attempting to install..."

  case "$OS" in
    linux)
      if command -v apt-get >/dev/null 2>&1; then
        run_as_root apt-get update
        run_as_root apt-get install -y tar
      elif command -v yum >/dev/null 2>&1; then
        run_as_root yum install -y tar
      elif command -v apk >/dev/null 2>&1; then
        run_as_root apk add --no-cache tar
      else
        echo "Unsupported Linux distribution: cannot install tar automatically"
        exit 1
      fi
      ;;
    darwin)
      # macOS usually has bsdtar; but keep this here for completeness
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

echo "Downloading Prometheus binary from $URL..."
mkdir -p "$DOWNLOAD_DIR"
curl -L "$URL" -o "${DOWNLOAD_DIR}/${TARBALL}"

echo "Extracting Prometheus binary..."
tar -xzf "${DOWNLOAD_DIR}/${TARBALL}" -C "$DOWNLOAD_DIR"

cp "${DOWNLOAD_DIR}/prometheus-${VERSION}.${OS}-${ARCH}/prometheus" .
cp "${DOWNLOAD_DIR}/prometheus-${VERSION}.${OS}-${ARCH}/promtool" .

chmod +x prometheus promtool

rm -rf "$DOWNLOAD_DIR"

echo "Prometheus and promtool have been downloaded and extracted successfully"

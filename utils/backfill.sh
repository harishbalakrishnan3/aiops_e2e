#!/bin/bash

# TODO: Download promtool and mimirtool as per the OS and architecture

ADDRESS=$1
ID=$2
KEY=$3
UTILS_DIR=$4

# Cleanup existing blocks if present
/bin/rm -rf "$UTILS_DIR"/data/*

# Generate blocks from txt file
promtool tsdb create-blocks-from openmetrics "$UTILS_DIR"/historical_data.txt "$UTILS_DIR"/data

# Upload all blocks to prometheus one by one
for dir in "$UTILS_DIR"/data/*/; do
  # Remove the trailing slash from the directory name
  dir=${dir%/}
  # Backfill
  mimirtool backfill --address="$ADDRESS" --id="$ID" --key="$KEY" "$dir"
done

# Cleanup generated blocks finally
/bin/rm -rf "$UTILS_DIR"/data/*
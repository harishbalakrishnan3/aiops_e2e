#!/bin/bash

ADDRESS=$1
ID=$2
KEY=$3
UTILS_DIR=$4
DATA_BLOCK_DIR=$5
HISTORICAL_DATA_FILE=$6

# Cleanup existing blocks if present
/bin/rm -rf "$UTILS_DIR$DATA_BLOCK_DIR"*

# Generate blocks from txt file
"$UTILS_DIR"/promtool tsdb create-blocks-from --max-block-duration=12h openmetrics "$UTILS_DIR/$HISTORICAL_DATA_FILE" "$UTILS_DIR$DATA_BLOCK_DIR"

# Upload all blocks to prometheus one by one
for dir in "$UTILS_DIR$DATA_BLOCK_DIR"*/; do
  # Remove the trailing slash from the directory name
  dir=${dir%/}
  # Backfill
  "$UTILS_DIR"/mimirtool backfill --address="$ADDRESS" --id="$ID" --key="$KEY" "$dir"
done

# Cleanup generated blocks finally
/bin/rm -rf "$UTILS_DIR$DATA_BLOCK_DIR"*
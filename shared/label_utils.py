"""Shared label utility functions for Prometheus metric labels.

Used by both features/steps/ and scripts/ to avoid code duplication.
"""

import logging
import re


def sanitize_label_name(label_name: str) -> str:
    """
    Sanitize label name to conform to Prometheus naming rules.
    Label names must match [a-zA-Z_][a-zA-Z0-9_]* - only letters, numbers, underscores.
    Cannot start with a number.
    """
    sanitized = label_name.strip()
    sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", sanitized)

    if sanitized and sanitized[0].isdigit():
        sanitized = "_" + sanitized

    if sanitized != label_name.strip():
        logging.warning(f"Label name '{label_name}' sanitized to '{sanitized}'")

    return sanitized


def parse_labels(label_string: str) -> dict:
    """Parse label string in format 'key1=value1,key2=value2' into dict."""
    if not label_string:
        return {}
    labels = {}
    for pair in label_string.split(","):
        if "=" in pair:
            key, value = pair.split("=", 1)
            sanitized_key = sanitize_label_name(key)
            labels[sanitized_key] = value.strip()
    return labels


def format_labels(labels_dict: dict) -> str:
    """Format labels dict into Prometheus label string: key1="value1",key2="value2"."""
    return ",".join([f'{k}="{v}"' for k, v in labels_dict.items()])

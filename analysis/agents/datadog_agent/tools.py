from typing import List, Union
from datetime import datetime, timezone, timedelta
from langchain_core.tools import tool
from log_extractor import retrieve_logs
import json


@tool
def add_duration_to_iso_timestamp(
    iso_timestamp: Union[str, dict],
    days: int = 0,
    hours: int = 0,
    minutes: int = 0,
    seconds: int = 0,
) -> str:
    """
    Add duration to an ISO 8601 formatted timestamp and return the result.

    Args:
        iso_timestamp (Union[str, dict]): Timestamp in format "YYYY-MM-DD HH:MM:SS.ssssss+TZ"
                           where TZ is timezone offset (e.g., +00:00, -05:00)
                           Can also be a dict/JSON with all parameters
        days (int): Number of days to add (default: 0)
        hours (int): Number of hours to add (default: 0)
        minutes (int): Number of minutes to add (default: 0)
        seconds (int): Number of seconds to add (default: 0)

    Returns:
        str: Modified timestamp in ISO 8601 format

    Example:
        >>> add_duration_to_iso_timestamp("2022-07-20T04:53:06+00:00", hours=2, minutes=30)
        "2022-07-20T07:23:06+00:00"

    Raises:
        ValueError: If the ISO timestamp format is invalid
    """
    try:
        # Handle case where input is a JSON string or dict
        if isinstance(iso_timestamp, str) and iso_timestamp.strip().startswith("{"):
            params = json.loads(iso_timestamp)
            timestamp_str = params.get("iso_timestamp", "")
            days = params.get("days", 0)
            hours = params.get("hours", 0)
            minutes = params.get("minutes", 0)
            seconds = params.get("seconds", 0)
        elif isinstance(iso_timestamp, dict):
            timestamp_str = iso_timestamp.get("iso_timestamp", "")
            days = iso_timestamp.get("days", 0)
            hours = iso_timestamp.get("hours", 0)
            minutes = iso_timestamp.get("minutes", 0)
            seconds = iso_timestamp.get("seconds", 0)
        else:
            timestamp_str = str(iso_timestamp)

        # Handle both 'Z' and '+00:00' timezone formats
        normalized_timestamp = timestamp_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized_timestamp)

        # Add the duration
        new_dt = dt + timedelta(
            days=days, hours=hours, minutes=minutes, seconds=seconds
        )

        return new_dt.isoformat()
    except (ValueError, json.JSONDecodeError) as e:
        raise ValueError(
            f"Invalid ISO timestamp format or parameters: {iso_timestamp}"
        ) from e


@tool
def subtract_duration_from_iso_timestamp(
    iso_timestamp: Union[str, dict],
    days: int = 0,
    hours: int = 0,
    minutes: int = 0,
    seconds: int = 0,
) -> str:
    """
    Subtract duration from an ISO 8601 formatted timestamp and return the result.

    Args:
        iso_timestamp (Union[str, dict]): Timestamp in format "YYYY-MM-DD HH:MM:SS.ssssss+TZ"
                           where TZ is timezone offset (e.g., +00:00, -05:00)
                           Can also be a dict/JSON with all parameters
        days (int): Number of days to subtract (default: 0)
        hours (int): Number of hours to subtract (default: 0)
        minutes (int): Number of minutes to subtract (default: 0)
        seconds (int): Number of seconds to subtract (default: 0)

    Returns:
        str: Modified timestamp in ISO 8601 format

    Example:
        >>> subtract_duration_from_iso_timestamp("2022-07-20T04:53:06+00:00", hours=1, minutes=15)
        "2022-07-20T03:38:06+00:00"

    Raises:
        ValueError: If the ISO timestamp format is invalid
    """
    try:
        # Handle case where input is a JSON string or dict
        if isinstance(iso_timestamp, str) and iso_timestamp.strip().startswith("{"):
            params = json.loads(iso_timestamp)
            timestamp_str = params.get("iso_timestamp", "")
            days = params.get("days", 0)
            hours = params.get("hours", 0)
            minutes = params.get("minutes", 0)
            seconds = params.get("seconds", 0)
        elif isinstance(iso_timestamp, dict):
            timestamp_str = iso_timestamp.get("iso_timestamp", "")
            days = iso_timestamp.get("days", 0)
            hours = iso_timestamp.get("hours", 0)
            minutes = iso_timestamp.get("minutes", 0)
            seconds = iso_timestamp.get("seconds", 0)
        else:
            timestamp_str = str(iso_timestamp)

        # Handle both 'Z' and '+00:00' timezone formats
        normalized_timestamp = timestamp_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized_timestamp)

        # Subtract the duration
        new_dt = dt - timedelta(
            days=days, hours=hours, minutes=minutes, seconds=seconds
        )

        return new_dt.isoformat()
    except (ValueError, json.JSONDecodeError) as e:
        raise ValueError(
            f"Invalid ISO timestamp format or parameters: {iso_timestamp}"
        ) from e


@tool
def get_current_timestamp_iso() -> str:
    """
    Get the current timestamp in ISO 8601 format with UTC timezone.

    Returns:
        str: Current timestamp in format "YYYY-MM-DD HH:MM:SS.ssssss+00:00"

    Example:
        >>> get_current_timestamp_iso()
        "2025-01-20T15:30:45.123456+00:00"
    """
    return datetime.now(timezone.utc).isoformat()


@tool
def extract_datadog_logs_between_timestamps_for_tenant(
    start_time: Union[str, dict],
    end_time: str = "",
    log_level: str = "error",
    tenant_id: str = "",
    keywords: List[str] = None,
) -> str:
    """
    Extracts logs of a given log level from Datadog between two timestamps. Logs retrieved without filters are typically voluminous.
    If keywords are not supplied, to anchor to the relevant timestamps, typically you would first call this function to get the error logs between two timestamps.
    Once the exact timestamp of the error is found, use the same function to retrieve info or debug logs around that timestamp to get more context.
    If keywords are specified, anchoring to relevant timestamps is easier. In this case, you would pass in the keyword and use the info log level to get the relevant timestamps.
    In further iterations, you can re-invoke this function with appropriate context window around the anchored timestamps to get more context.

    Args:
        start_time (Union[str, dict]): Start time in ISO 8601 format (e.g., "2025-01-20T15:30:45+00:00")
                                     Can also be a dict/JSON with all parameters
        end_time (str): End time in ISO 8601 format (e.g., "2025-01-20T16:30:45+00:00")
        log_level (str): Log level to extract (error, debug, info)
        tenant_id (str): Tenant ID to filter logs by
        keywords (List[str]): List of keywords to filter logs by

    Returns:
        str: Filtered logs (in JSON format) between the two timestamps as a string
    """
    try:
        # Handle case where all parameters are passed as a JSON string or dict in start_time
        if isinstance(start_time, str) and start_time.strip().startswith("{"):
            params = json.loads(start_time)
            start_time_str = params.get("start_time", "")
            end_time = params.get("end_time", "")
            log_level = params.get("log_level", "error")
            tenant_id = params.get("tenant_id", "")
            keywords = params.get("keywords", None)
        elif isinstance(start_time, dict):
            start_time_str = start_time.get("start_time", "")
            end_time = start_time.get("end_time", "")
            log_level = start_time.get("log_level", "error")
            tenant_id = start_time.get("tenant_id", "")
            keywords = start_time.get("keywords", None)
        else:
            start_time_str = str(start_time)

        # Convert ISO timestamp strings to UTC datetime objects
        start_time_dt = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
        end_time_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))

        logs = retrieve_logs(
            start_time=start_time_dt,
            end_time=end_time_dt,
            log_level=log_level,
            tenant_id=tenant_id,
            keywords=keywords,
        )
        return "\n".join(str(log) for log in logs)

    except (ValueError, json.JSONDecodeError) as e:
        raise ValueError(f"Invalid parameters or timestamp format: {start_time}") from e


def get_tools():
    return [
        add_duration_to_iso_timestamp,
        subtract_duration_from_iso_timestamp,
        get_current_timestamp_iso,
        extract_datadog_logs_between_timestamps_for_tenant,
    ]

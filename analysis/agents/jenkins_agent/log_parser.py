import re
from datetime import datetime, timezone
from typing import List, Optional, Union


def should_append(level, epoch, levels, start_time, end_time):
    if levels and level not in levels:
        return False
    if start_time and epoch < start_time:
        return False
    if end_time and epoch > end_time:
        return False
    return True


def flush_buffer(buffer, last_timestamp, result, levels, start_time, end_time):
    if buffer and last_timestamp is not None:
        if should_append("INFO", last_timestamp, levels, start_time, end_time):
            result.append(
                {
                    "timestamp": last_timestamp,
                    "level": "INFO",
                    "log": buffer.rstrip("\n"),
                }
            )
        buffer = ""
    return buffer


def parse_log_file(
    file_path: str,
    levels: Optional[Union[str, List[str]]] = None,
    start_time: Optional[int] = None,
    end_time: Optional[int] = None,
):
    """
    Parses a log file and returns an array of log objects.
    Each object: {'timestamp': <epoch>, 'level': <str>, 'log': <str>}
    Can filter by log level(s), start_time, and end_time (all in epoch seconds).
    """
    if isinstance(levels, str):
        levels = [levels]
    if levels:
        levels = set(levels)
    print("here now 2")
    log_pattern = re.compile(r"^\s*\[(.*?)\] \[(.*?)\] (.*)$")
    alt_pattern = re.compile(r"^\s*(\w+):root:(.*)$")
    result = []
    last_timestamp = None
    buffer = ""

    with open(file_path, "r") as f:
        for line in f:
            match = log_pattern.match(line)
            if match:
                buffer = flush_buffer(
                    buffer, last_timestamp, result, levels, start_time, end_time
                )
                timestamp_str, level, log_msg = match.groups()

                try:
                    dt = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%SZ").replace(
                        tzinfo=timezone.utc
                    )
                    epoch = int(dt.timestamp())
                except Exception:
                    continue

                last_timestamp = epoch
                if should_append(level, epoch, levels, start_time, end_time):
                    result.append({"timestamp": epoch, "level": level, "log": log_msg})
            else:
                alt_match = alt_pattern.match(line.strip())
                if alt_match and last_timestamp is not None:
                    alt_level, alt_log = alt_match.groups()
                    alt_level = alt_level.upper()
                    if should_append(
                        alt_level, last_timestamp, levels, start_time, end_time
                    ):
                        result.append(
                            {
                                "timestamp": last_timestamp,
                                "level": alt_level,
                                "log": alt_log.strip(),
                            }
                        )
                else:
                    buffer += line if buffer == "" else "\n" + line.rstrip("\n")
        # Flush remaining buffer at end of file
        buffer = flush_buffer(
            buffer, last_timestamp, result, levels, start_time, end_time
        )
    return result


if __name__ == "__main__":
    try:
        file_path = "../../mock_data/analysis/processed/Anomaly/scenario_Testing_Anomaly_Detection_for_Connection_Stats_With_Simple_Linear_Spike.txt"
        levels = ["INFO", "ERROR"]
        # start_time = 1700000000  # Example epoch time
        # end_time = 1700003600    # Example epoch time
        logs = parse_log_file(file_path)
        print(logs)
    except Exception as e:
        print(f"Error parsing log file: {e}")

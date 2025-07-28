import os
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple
from dotenv import load_dotenv
from datadog_api_client import ApiClient, Configuration
from datadog_api_client.v2.api.logs_api import LogsApi
from datadog_api_client.v2.model.logs_list_request import LogsListRequest
from datadog_api_client.v2.model.logs_list_request_page import LogsListRequestPage
from datadog_api_client.v2.model.logs_query_filter import LogsQueryFilter
from datadog_api_client.v2.model.logs_sort import LogsSort
import json

# Load environment variables
load_dotenv()

DEFAULT_FILTERS = """service:{microservices}
env:staging
status:{log_level}
-"New scheduling"
-"Handling message with details"
-"Opened connection"
@tenant_id:{tenant_id}
"""


def get_microservices_text(feature_name: str) -> str:
    """
    Read microservices text from the appropriate feature folder under domain knowledge.

    Args:
        feature_name: Name of the feature folder (e.g., "100_ElephantFlows")

    Returns:
        Content of microservices.txt file, or default if not found
    """
    try:
        # Get the directory of the current script
        current_dir = os.path.dirname(os.path.abspath(__file__))
        microservices_file = os.path.join(
            current_dir, "domain_knowledge", feature_name, "microservices.txt"
        )

        if os.path.exists(microservices_file):
            with open(microservices_file, "r") as f:
                content = f.read().strip()
                print(f"Found microservices.txt for {feature_name}: {content}")
                return content
        else:
            # Default fallback if file not found
            default_microservices = "(ai-ops-orchestrator OR ai-ops-insights OR ai-ops-analytics OR vdb-applications OR ai-ops-alert-services)"
            print(
                f"microservices.txt not found for {feature_name}, using default: {default_microservices}"
            )
            return default_microservices

    except Exception as e:
        print(f"Error reading microservices.txt for {feature_name}: {e}")
        # Default fallback on error
        return "(ai-ops-orchestrator OR ai-ops-insights OR ai-ops-analytics OR vdb-applications OR ai-ops-alert-services)"


def construct_filter(
    log_level: Optional[str] = None,
    tenant_id: Optional[str] = None,
    feature_name: Optional[str] = "100_ElephantFlows",
) -> str:
    """
    Constructs a Datadog query string using DEFAULT_FILTERS.
    Replaces {log_level} placeholder with the provided log_level.
    Replaces {tenant_id} placeholder with the provided tenant_id.
    Replaces {microservices} placeholder with content from microservices.txt.

    Args:
        log_level: Log level to filter by ("error", "debug", "info")
        tenant_id: Tenant ID to filter logs by
        feature_name: Feature name to determine which microservices.txt to use

    Returns:
        Constructed Datadog query string
    """
    # Use DEFAULT_FILTERS and replace newlines with spaces
    query = DEFAULT_FILTERS.replace("\n", " ").strip()

    # Replace {log_level} placeholder if log_level is provided
    if log_level:
        query = query.replace("{log_level}", log_level)

    # Replace {tenant_id} placeholder if tenant_id is provided
    if tenant_id:
        query = query.replace("{tenant_id}", tenant_id)

    # Replace {microservices} placeholder with content from microservices.txt
    microservices_text = get_microservices_text(feature_name)
    query = query.replace("{microservices}", microservices_text)

    return query


def setup_datadog_client() -> ApiClient:
    """
    Setup Datadog API client with credentials from environment variables.

    Returns:
        Configured Datadog ApiClient instance
    """
    configuration = Configuration()
    configuration.api_key["apiKeyAuth"] = os.getenv("DD_API_KEY")
    configuration.api_key["appKeyAuth"] = os.getenv("DD_APPLICATION_KEY")

    # Set the custom Datadog site
    dd_site = os.getenv("DD_SITE", "datadoghq.com")
    configuration.server_variables["site"] = dd_site

    print(f"Connecting to Datadog site: {dd_site}")

    return ApiClient(configuration)


def get_time_range() -> Tuple[datetime, datetime]:
    """
    Calculate the time range for the last 6 hours in UTC.

    Returns:
        Tuple of (from_time, to_time) as datetime objects
    """
    now = datetime.now(timezone.utc)
    from_time = now - timedelta(hours=6)
    return from_time, now


def retrieve_logs(
    feature_name: str,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    log_level: Optional[str] = None,
    tenant_id: Optional[str] = None,
) -> List[dict]:
    """
    Retrieve logs from Datadog between the specified UTC datetime objects. log_level can be used to filter the logs by log level. log_level can be "error", "debug", "info".
    tenant_id is mandatory.
    First, use this function to retrieve the error logs between two timestamps. Once the exact timestamp of the error is found, use the same function to retrieve info or debug logs around that timestamp.

    Args:
        feature_name: Feature name to determine which microservices.txt to use (MANDATORY).
        start_time: Start time as UTC datetime object. If None, uses last 6 hours.
        end_time: End time as UTC datetime object. If None, uses current time.
        log_level: Log level filter ("error", "debug", "info"). Replaces {log_level} in filters.
        tenant_id: Tenant ID to filter logs by.

    Returns:
        List of log dictionaries containing timestamp, message, and other attributes

    Raises:
        ValueError: If feature_name is not provided or is empty
    """
    try:
        # Validate that feature_name is provided and not empty
        if not feature_name or not feature_name.strip():
            raise ValueError(
                "feature_name is mandatory and cannot be empty. Please provide a valid feature name (e.g., '100_ElephantFlows')"
            )

        # Setup API client
        with setup_datadog_client() as api_client:
            api_instance = LogsApi(api_client)

            # Get time range - use provided datetime objects or default to last 6 hours
            if start_time is not None and end_time is not None:
                from_time_dt, to_time_dt = start_time, end_time
            else:
                from_time_dt, to_time_dt = get_time_range()

            # Convert to ISO format for Datadog API
            from_time = from_time_dt.isoformat().replace("+00:00", "Z")
            to_time = to_time_dt.isoformat().replace("+00:00", "Z")

            print(f"Retrieving logs from {from_time} to {to_time}")

            # Setup query filter
            query = construct_filter(
                log_level=log_level, tenant_id=tenant_id, feature_name=feature_name
            )
            print(f"Filters: {query}")
            print("-" * 60)

            # Create the request
            body = LogsListRequest(
                filter=LogsQueryFilter(
                    query=query,
                    _from=from_time,
                    to=to_time,
                ),
                sort=LogsSort.TIMESTAMP_ASCENDING,
                page=LogsListRequestPage(limit=1000),  # Adjust as needed
            )

            # Make the API call
            response = api_instance.list_logs_with_pagination(body=body)

            # Process and display results
            if response:
                logs_data = []  # Collect logs for saving to file

                for i, log in enumerate(response, 1):
                    # Use timestamp as string
                    timestamp = log.attributes.timestamp

                    # Add log to our collection - start with timestamp
                    log_dict = {
                        "timestamp": str(timestamp),
                    }

                    # Add message if it exists
                    if hasattr(log.attributes, "message"):
                        log_dict["message"] = log.attributes.message

                    # Add additional attributes

                    if hasattr(log.attributes, "service"):
                        log_dict["service"] = log.attributes.service

                    # Add device-related fields if they exist
                    device_fields = [
                        "device_uid",
                        "device_uids",
                        "device_record_uids",
                        "device_record_uid",
                        "synchronization_uid",
                        "module_name",
                    ]
                    for field in device_fields:
                        if field in log.attributes.attributes:
                            field_value = log.attributes.attributes[field]
                            log_dict[field] = field_value

                    logs_data.append(log_dict)

                return logs_data

            else:
                print("No logs found for the specified time range and filters.")
                return []

    except Exception as e:
        print(f"Error retrieving logs: {str(e)}")
        return []


def save_logs_to_file(logs: List[dict]) -> None:
    """
    Save logs to a JSON file for further analysis.

    Args:
        logs: List of log dictionaries to save to file
    """
    output_file = f"datadog_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    if not logs:
        print("No logs to save to file.")
        return

    # Write logs to file
    with open(output_file, "w") as f:
        json.dump(logs, f, indent=2, default=str)

    print(f"\n{len(logs)} logs saved to: {output_file}")


# This is just for testing
def main() -> None:
    """
    Main function to execute the log retrieval process.
    """
    print("Datadog Log Extractor")
    print("=" * 40)

    # Check if required environment variables are set
    required_vars = ["DD_API_KEY", "DD_APPLICATION_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        print(
            f"Error: Missing required environment variables: {', '.join(missing_vars)}"
        )
        print("Please set these variables in your .env file:")
        for var in missing_vars:
            print(f"  {var}=your_{var.lower()}_here")
        return

    try:
        # Create time range using datetime objects
        now = datetime.now(timezone.utc)
        start_time = now - timedelta(hours=24)
        logs = retrieve_logs(
            log_level="info",
            start_time=start_time,
            end_time=now,
            tenant_id="af5f6035-7538-4709-b073-7b5f4b69543c",
            feature_name="100_ElephantFlows",
        )
        save_logs_to_file(logs)
        print("\nLog retrieval completed successfully!")
    except Exception as e:
        print(f"Failed to retrieve logs: {str(e)}")


if __name__ == "__main__":
    main()

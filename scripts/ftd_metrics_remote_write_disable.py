#!/usr/bin/env python3

import argparse
import base64
import json
import logging
import os
import sys
import yaml
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from features.steps.env import get_endpoints
from features.steps.cdo_apis import get, post

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

FMC_DOMAIN_UUID = "e276abec-e0f2-11e3-8169-6d9ed49b625f"


def get_fmce_device_uid():
    """
    Get the FMCE device UID from Aegis API.

    Returns:
        str: The device UID of the FMCE
    """
    logger.info("Fetching FMCE device UID from Aegis...")
    endpoints = get_endpoints()
    resp = get(endpoints.FMC_DETAILS_URL, print_body=False)

    if not resp or len(resp) == 0:
        raise Exception("No FMCE devices found in Aegis")

    # Use the first FMCE device found
    device_uid = resp[0]["uid"]
    logger.info(f"Found FMCE device UID: {device_uid}")
    return device_uid


def get_current_remote_write_config(device_uid, domain_uuid):
    """
    Get the current remote write configuration from FMC via device gateway.

    Args:
        device_uid: The FMCE device UID
        domain_uuid: The FMC domain UUID

    Returns:
        dict: The current remote write configuration containing 'enabled' and 'remoteWriteConfig'
    """
    logger.info("Fetching current remote write configuration...")
    endpoints = get_endpoints()

    payload = {
        "deviceUid": device_uid,
        "request": {
            "commands": [
                {
                    "method": "GET",
                    "link": f"/api/fmc_config/v1/domain/{domain_uuid}/integration/aiops/metricconfiguration?offset=0&limit=25",
                    "body": "",
                }
            ]
        },
    }

    response = post(
        endpoints.DEVICE_GATEWAY_COMMAND_URL,
        json.dumps(payload),
        expected_return_code=200,
    )
    response_data = response.json()

    if response_data.get("status") != "responded":
        raise Exception(
            f"Device gateway command failed with status: {response_data.get('status')}"
        )

    response_body = json.loads(response_data["data"]["responseBody"])

    if not response_body or len(response_body) == 0:
        raise Exception("No remote write configuration found")

    config = response_body[0]
    logger.info("Successfully retrieved current remote write configuration")

    return config


def modify_remote_write_config(encoded_config, uuid=None):
    """
    Modify the remote write configuration to disable metrics.

    Args:
        encoded_config: Base64 encoded remote write configuration
        uuid: Optional specific device UUID to disable. If None, disables all FTDs

    Returns:
        str: Modified base64 encoded configuration
    """
    # Decode the config
    decoded_config = base64.b64decode(encoded_config).decode("utf-8")
    logger.info(f"Current configuration:\n{decoded_config}")

    # Parse as YAML
    config_dict = yaml.safe_load(decoded_config)

    # Get existing write_relabel_configs or initialize
    write_relabel_configs = config_dict.get("write_relabel_configs", [])

    # Create new relabel configs based on whether uuid is provided
    if uuid:
        # Disable specific device by uuid
        logger.info(f"Modifying config to disable metrics for device UUID: {uuid}")
        drop_config = {"action": "drop", "source_labels": ["uuid"], "regex": uuid}
    else:
        # Disable all FTDs by instance
        logger.info("Modifying config to disable metrics for all FTDs")
        drop_config = {
            "action": "drop",
            "source_labels": ["instance"],
            "regex": "^127.*",
        }

    # Find the tenant_uuid replacement config (should be present in existing config)
    tenant_replacement_config = None
    for config in write_relabel_configs:
        if config.get("target_label") == "tenant_uuid":
            tenant_replacement_config = config
            break

    if not tenant_replacement_config:
        raise Exception(
            "No tenant_uuid configuration found in existing remote write config"
        )

    # Build new write_relabel_configs with drop rule first, then tenant_uuid replacement
    new_write_relabel_configs = [drop_config, tenant_replacement_config]

    config_dict["write_relabel_configs"] = new_write_relabel_configs

    # Convert back to YAML
    modified_config = yaml.dump(config_dict, default_flow_style=False, sort_keys=False)
    logger.info(f"Modified configuration:\n{modified_config}")

    # Encode back to base64
    encoded_modified_config = base64.b64encode(modified_config.encode("utf-8")).decode(
        "utf-8"
    )

    return encoded_modified_config


def update_remote_write_config(device_uid, domain_uuid, encoded_config):
    """
    Update the remote write configuration on FMC via device gateway.

    Args:
        device_uid: The FMCE device UID
        domain_uuid: The FMC domain UUID
        encoded_config: Base64 encoded remote write configuration

    Returns:
        dict: The response from the device gateway
    """
    logger.info("Updating remote write configuration...")
    endpoints = get_endpoints()

    body_payload = {"enabled": True, "remoteWriteConfig": encoded_config}

    payload = {
        "deviceUid": device_uid,
        "request": {
            "commands": [
                {
                    "method": "POST",
                    "link": f"/api/fmc_config/v1/domain/{domain_uuid}/integration/aiops/metricconfiguration",
                    "body": json.dumps(body_payload),
                }
            ]
        },
    }

    response = post(
        endpoints.DEVICE_GATEWAY_COMMAND_URL,
        json.dumps(payload),
        expected_return_code=200,
    )
    response_data = response.json()

    if response_data.get("status") != "responded":
        raise Exception(
            f"Device gateway command failed with status: {response_data.get('status')}"
        )

    if response_data["data"].get("responseStatus") != "SUCCESS":
        raise Exception(
            f"Failed to update configuration: {response_data['data'].get('responseStatus')}"
        )

    logger.info("Successfully updated remote write configuration")
    return response_data


def main():
    parser = argparse.ArgumentParser(
        description="Disable remote write of metrics from FTDs"
    )
    parser.add_argument(
        "--env", required=True, help="Environment name (e.g., prod, stage, etc.)"
    )
    parser.add_argument(
        "--uuid",
        required=False,
        help="Specific device UUID to disable. If not provided, disables all FTDs",
    )

    args = parser.parse_args()

    # Set environment variable for ENV
    os.environ["ENV"] = args.env

    # Load environment variables from .env file
    load_dotenv()

    # Verify CDO_TOKEN is set
    if not os.getenv("CDO_TOKEN"):
        logger.error("CDO_TOKEN not found in environment variables")
        sys.exit(1)

    try:
        # Step 1: Get FMCE device UID
        device_uid = get_fmce_device_uid()

        # Step 2: Get current remote write config
        current_config = get_current_remote_write_config(device_uid, FMC_DOMAIN_UUID)

        # Step 3: Modify the config
        modified_config = modify_remote_write_config(
            current_config["remoteWriteConfig"], uuid=args.uuid
        )

        # Step 4: Update the config
        result = update_remote_write_config(
            device_uid, FMC_DOMAIN_UUID, modified_config
        )

        logger.info("=" * 80)
        logger.info("SUCCESS: Remote write metrics disabled")
        if args.uuid:
            logger.info(f"Disabled metrics for device UUID: {args.uuid}")
        else:
            logger.info("Disabled metrics for all FTDs")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"Failed to disable remote write metrics: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

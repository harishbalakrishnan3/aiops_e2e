import logging
import os
from time import sleep

import requests

from features.steps.env import get_endpoints

# Configure logger
logger = logging.getLogger(__name__)

headers = {"Authorization": f"Bearer {os.getenv('HELIOS_TOKEN')}"}


#  KNOWLEDGE BASE ID : 212
#  ASSISTANT ID : 206
def create_knowledge_base():
    payload = {
        "name": "firewall",  # e.g, "test-kb"
        "description": "contextual knowledge for firewall related data",  # e.g, "test knowledge base"
        "type": "collection",
        "subtype": "self_managed",
        "access": "internal",
        "connector_id": 0,
        "metadata": {},
    }

    return requests.post(
        f"{get_endpoints()().HELIOS_KNOWLEDGE_BASE}", headers=headers, json=payload
    ).json()


def get_assistants():
    return requests.get(
        f"{get_endpoints().HELIOS_ASSISTANT}",
        headers=headers,
    ).json()


def link_assistant_with_kb(assistant_id: int, kb_id: int):
    payload = {
        "knowledge_bases": {
            "add": [
                {"id": kb_id},
            ],
        }
    }

    return requests.patch(
        f"{get_endpoints().HELIOS_ASSISTANT}/{assistant_id:int}",
        headers=headers,
        json=payload,
    ).json()


# [{'id': 8714, 'type': 'file', 'created_at': '2025-03-17T18:26:05.165383', 'status': 'active', 'filename': 'health-monitoring.pdf', 'access': 'public', 'bytes': 51491, 'synced_at': None, 'metadata': {'file_name': 'health-monitoring.pdf', 'file_ext': '.pdf', 'base_dir': '/tmp', 'file_path': 'knowledge_bases/212/health-monitoring.pdf', 'access': 'public', 'kb:212': True, 'knowledge_base.id': 212, 'knowledge_base.type': 'COLLECTION', 'knowledge_base.subtype': 'SELF_MANAGED', 'knowledge_base.share_reference': True, 'node_count': 36}}, {'id': 8715, 'type': 'file', 'created_at': '2025-03-17T18:26:05.165383', 'status': 'active', 'filename': 'elephant-flow-detection.pdf', 'access': 'public', 'bytes': 7372, 'synced_at': None, 'metadata': {'file_name': 'elephant-flow-detection.pdf', 'file_ext': '.pdf', 'base_dir': '/tmp', 'file_path': 'knowledge_bases/212/elephant-flow-detection.pdf', 'access': 'public', 'kb:212': True, 'knowledge_base.id': 212, 'knowledge_base.type': 'COLLECTION', 'knowledge_base.subtype': 'SELF_MANAGED', 'knowledge_base.share_reference': True, 'node_count': 6}}, {'id': 8716, 'type': 'file', 'created_at': '2025-03-17T18:26:05.165383', 'status': 'active', 'filename': 'elephant_flow.pdf', 'access': 'public', 'bytes': 6082, 'synced_at': None, 'metadata': {'file_name': 'elephant_flow.pdf', 'file_ext': '.pdf', 'base_dir': '/tmp', 'file_path': 'knowledge_bases/212/elephant_flow.pdf', 'access': 'public', 'kb:212': True, 'knowledge_base.id': 212, 'knowledge_base.type': 'COLLECTION', 'knowledge_base.subtype': 'SELF_MANAGED', 'knowledge_base.share_reference': True, 'node_count': 5}}]
def ingest_files(kb_id: str, context_dir: str):
    pdf_folder = context_dir
    file_paths = []

    for filename in os.listdir(pdf_folder):
        if filename.endswith(".pdf"):
            file_paths.append(os.path.join(pdf_folder, filename))
    files = [("files", open(file, "rb")) for file in file_paths]

    response = requests.post(
        f"{get_endpoints().HELIOS_KNOWLEDGE_BASE}/{kb_id}/files",
        headers=headers,
        files=files,
    ).json()
    print(response)


def create_thread():
    """Create a new thread for conversation with the assistant."""
    try:
        logger.debug("Creating new thread")
        response = requests.post(
            f"{get_endpoints().HELIOS_THREADS}", headers=headers, json={}
        )
        response.raise_for_status()
        thread_data = response.json()
        logger.debug(f"Successfully created thread with ID: {thread_data.get('id')}")
        return thread_data
    except Exception as e:
        logger.error(f"Failed to create thread: {str(e)}")
        raise


def message(thread_id: int, prompt: str):
    """Send a message to a specific thread."""
    payload = {"content": prompt}  # e.g, "What is CAMP?"

    try:
        logger.debug(f"Sending message to thread {thread_id}")
        response = requests.post(
            f"{get_endpoints().HELIOS_THREADS}/{thread_id}/messages",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to send message to thread {thread_id}: {str(e)}")
        raise


def run_message_on_assistant(assistant_id: int, thread_id: int):
    payload = {"assistant_id": assistant_id}

    return requests.post(
        f"{get_endpoints().HELIOS_THREADS}/{thread_id}/runs",
        headers=headers,
        json=payload,
    ).json()


def delete_thread(thread_id: int):
    """Delete a thread to clean up resources."""
    try:
        logger.debug(f"Deleting thread {thread_id}")
        response = requests.delete(
            f"{get_endpoints().HELIOS_THREADS}/{thread_id}", headers=headers
        )
        response.raise_for_status()
        logger.debug(f"Successfully deleted thread {thread_id}")
        return response.json()
    except Exception as e:
        logger.error(f"Failed to delete thread {thread_id}: {str(e)}")
        raise


def get_message_on_assistant(thread_id: int):
    return requests.get(
        f"{get_endpoints().HELIOS_THREADS}/{thread_id}/messages", headers=headers
    ).json()


def wait_on_response(thread_id: int, retry_attempts: int) -> str:
    """
    Wait for assistant response with retry logic.

    Args:
        thread_id (int): The thread ID to check for responses
        retry_attempts (int): Number of retry attempts

    Returns:
        str: The assistant's response content, or None if no response received
    """
    initial_attempts = retry_attempts
    logger.debug(
        f"Starting to wait for response on thread {thread_id} with {retry_attempts} retry attempts"
    )

    while retry_attempts > 0:
        try:
            messages = get_message_on_assistant(thread_id=thread_id)

            if (
                len(messages["items"]) != 0
                and messages["items"][0]["role"] == "assistant"
            ):
                response_content = messages["items"][0]["content"][0]["text"]["value"]
                logger.info(
                    f"Received assistant response after {initial_attempts - retry_attempts + 1} attempts"
                )
                return response_content

            logger.debug(
                f"No assistant response yet, {retry_attempts} retry attempts remaining"
            )
            sleep(5)
            retry_attempts -= 1

        except Exception as e:
            logger.warning(
                f"Error while waiting for response: {str(e)}, retries left: {retry_attempts}"
            )
            retry_attempts -= 1
            if retry_attempts > 0:
                sleep(5)
            else:
                logger.error("Failed to get response after all retry attempts")
                raise

    logger.warning(
        f"No response received from assistant after {initial_attempts} attempts"
    )
    return None


def send_message_to_assistant(assistant_id: int, prompt: str):
    """
    Send a message to the Helios assistant and return the response.

    Args:
        assistant_id (int): The ID of the assistant to send the message to
        prompt (str): The message content to send

    Returns:
        dict: The response messages from the assistant
    """
    logger.info(f"Starting message exchange with assistant {assistant_id}")
    logger.debug(
        f"Prompt content: {prompt[:100]}..."
        if len(prompt) > 100
        else f"Prompt content: {prompt}"
    )

    try:
        # Create thread
        logger.debug("Creating new thread")
        thread = create_thread()
        thread_id = thread["id"]
        logger.info(f"Created thread with ID: {thread_id}")

        # Send message
        logger.debug(f"Sending message to thread {thread_id}")
        message(thread_id, prompt)
        logger.info("Message sent successfully")

        # Run message on assistant
        logger.debug(
            f"Running message on assistant {assistant_id} for thread {thread_id}"
        )
        run_message_on_assistant(assistant_id, thread_id)
        logger.info("Assistant run initiated")

        # Get initial messages
        messages = get_message_on_assistant(thread_id)
        logger.debug(f"Retrieved {len(messages.get('items', []))} initial messages")

        # Wait for response
        logger.info("Waiting for assistant response...")
        response = wait_on_response(thread_id, retry_attempts=10)

        if response:
            logger.info("Successfully received response from Helios assistant")
            logger.debug(
                f"Response preview: {response[:200]}..."
                if len(response) > 200
                else f"Response: {response}"
            )
        else:
            logger.warning(
                "No response received from assistant after maximum retry attempts"
            )

        # Clean up thread
        logger.debug(f"Deleting thread {thread_id}")
        delete_thread(thread_id)
        logger.info("Thread cleanup completed")

        return messages

    except Exception as e:
        logger.error(f"Error in send_message_to_assistant: {str(e)}", exc_info=True)
        # Attempt to clean up thread if it exists
        if "thread_id" in locals():
            try:
                logger.debug(f"Attempting to clean up thread {thread_id} after error")
                delete_thread(thread_id)
            except Exception as cleanup_error:
                logger.error(
                    f"Failed to clean up thread {thread_id}: {str(cleanup_error)}"
                )
        raise

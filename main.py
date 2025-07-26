import os
import time
import requests
import logging
import uuid
import random
from typing import Optional, Literal, Set, List, Dict
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from socialmedia.truesocial import TrueSocial, Status

# Load environment variables FIRST to ensure LOG_LEVEL is available for logging configuration
load_dotenv()

# Get log level string from environment variable, default to "INFO"
log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()

# Convert string log level to numeric level using getattr
numeric_level = getattr(logging, log_level_str, None)

# Validate the obtained level. If invalid, fallback to INFO and warn.
if not isinstance(numeric_level, int):
    print(f"WARNING: Invalid LOG_LEVEL '{log_level_str}' in .env or environment. Defaulting to INFO.")
    configured_log_level = logging.INFO
else:
    configured_log_level = numeric_level

# Configure logging
logging.basicConfig(level=configured_log_level, format='%(asctime)s - %(levelname)s - %(message)s')
logging.info(f"Logging level set to: {logging.getLevelName(configured_log_level)}")

# --- Global Configuration and File Access Helpers ---
PROCESSED_STATUS_IDS_FILE = "processed_status_ids.txt"


def load_processed_status_ids() -> Set[str]:
    """Loads URLs of already processed articles from a file."""
    if not os.path.exists(PROCESSED_STATUS_IDS_FILE):
        return set()
    with open(PROCESSED_STATUS_IDS_FILE, "r") as f:
        return set(line.strip() for line in f if line.strip())


def save_processed_status_id(status_id: str):
    """Saves a URL to the file of processed articles."""
    with open(PROCESSED_STATUS_IDS_FILE, "a") as f:
        f.write(status_id + "\n")


# --- Pydantic Model for the Payload ---
class TruthSocialMonitorPayload(BaseModel):
    """
    Pydantic model for the data sent to the webservice.
    Defines structure, types, default values, and aliases for JSON fields.
    """
    uuid: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique ID for this payload instance."
    )
    type: Literal["web-monitor", "truthsocial", "twitter"] = Field(
        default="truthsocial",
        description="The type of monitor or source from which the data originates."
    )
    url: Optional[str] = Field(
        default=None,
        description="The URL of the monitored article or source."
    )
    username: Optional[str] = Field(
        default=None,
        description="Optional username associated with the content."
    )
    content_id: Optional[str] = Field(
        default="",
        alias="content-id",  # Important for JSON output
        description="Optional ID for the specific content (e.g., ID of a tweet or post, here article ID from URL)."
    )
    content: str = Field(
        description="The main content of the message or data point."
    )
    ip: str = Field(
        description="The IP address from which the data is sent (here, the public IP of the Fly.io container)."
    )


# --- Webservice Communication Function ---
def send_data_to_webservice(payload_obj: TruthSocialMonitorPayload, webservice_url: str):
    """
    Constructs the JSON payload and sends it to the specified webservice URL.
    Logs success or failure.
    """
    payload_dict = payload_obj.model_dump(by_alias=True)

    try:
        logging.info(
            f"Attempting to send data to {webservice_url} with payload (UUID: {payload_obj.uuid}, Content ID: {payload_obj.content_id}).")
        response = requests.post(webservice_url, json=payload_dict, timeout=10)
        response.raise_for_status()
        logging.info(f"Successfully sent data. Webservice responded with status: {response.status_code}")
        logging.debug(f"Webservice response content: {response.text}")
    except requests.exceptions.Timeout:
        logging.error(f"Request to webservice timed out after 10 seconds: {webservice_url}")
    except requests.exceptions.ConnectionError as e:
        logging.error(f"Failed to connect to webservice: {webservice_url}. Error: {e}")
    except requests.exceptions.HTTPError as e:
        logging.error(
            f"Webservice returned an HTTP error: {e.response.status_code} - {e.response.text}. Response: {e.response.text}")
    except requests.exceptions.RequestException as e:
        logging.error(f"An unexpected error occurred while sending data to webservice: {e}")


# --- Main Logic ---

def main():
    """
    Main function to load environment variables and periodically send data.
    """
    # --- Configuration from Environment Variables ---
    fly_public_ip = os.getenv("FLY_PUBLIC_IP")
    webservice_url = os.getenv("WEBSERVICE_URL")
    target_username = os.getenv("TARGET_USERNAME", "realDonaldTrump")
    fetch_interval_seconds_str = os.getenv("FETCH_INTERVAL_SECONDS", "60")
    initial_since_id = os.getenv("INITIAL_SINCE_ID")
    api_verbose_output_str = os.getenv("API_VERBOSE_OUTPUT", "False").lower()
    api_verbose_output = api_verbose_output_str in ("true", "1", "t", "yes")

    # Validate essential environment variables
    if not fly_public_ip:
        logging.error("Error: FLY_PUBLIC_IP environment variable not set. Exiting.")
        return
    if not webservice_url:
        logging.error("Error: WEBSERVICE_URL environment variable not set. Exiting.")
        return

    try:
        fetch_interval_seconds = int(fetch_interval_seconds_str)
        if fetch_interval_seconds <= 0:
            raise ValueError("Fetch interval must be a positive number.")
    except ValueError:
        logging.error(
            f"Error: FETCH_INTERVAL_SECONDS must be a positive integer. Got '{fetch_interval_seconds_str}'. Exiting.")
        return

    logging.info(f"Monitor configured to send IP '{fly_public_ip}' to '{webservice_url}'.")
    logging.info(f"Truth Social monitoring: User='{target_username}'.")
    logging.info(f"Checking for new statuses every {fetch_interval_seconds} seconds.")

    # Load previously processed status IDs at startup
    processed_status_ids = load_processed_status_ids()
    logging.info(f"Loaded {len(processed_status_ids)} previously processed status IDs.")

    # --- Main Loop ---
    ts_client = TrueSocial(
        username=target_username,
        fetch_interval_seconds=fetch_interval_seconds,
        api_verbose_output=api_verbose_output,
        initial_since_id=initial_since_id
    )

    while True:
        logging.info(f"\n--- Starting Truth Social check ({time.strftime('%Y-%m-%d %H:%M:%S')}) ---")
        
        statuses: List[Status] = ts_client.fetch_new_statuses()

        if not statuses:
            logging.info("No new statuses found in this cycle.")
        else:
            logging.info(f"Found {len(statuses)} new statuses.")

            for status in statuses:
                if str(status.id) in processed_status_ids:
                    logging.debug(f"Status '{status.id}' already processed.")
                    continue

                logging.info(f"NEW status identified: '{status.id}'")

                payload = TruthSocialMonitorPayload(
                    ip=fly_public_ip,
                    url=status.url,
                    username=target_username,
                    content_id=str(status.id),
                    content=status.content
                )

                logging.info(f"Sending new status data (ID: {status.id}) to webservice.")
                send_data_to_webservice(payload, webservice_url)

                save_processed_status_id(str(status.id))
                processed_status_ids.add(str(status.id))
                logging.info(f"Status {status.id} marked as processed.")

        logging.info(f"Waiting for {fetch_interval_seconds} seconds until next check...")
        time.sleep(fetch_interval_seconds)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("\nProgram terminated by user (Ctrl+C).")
    except Exception as e:
        logging.critical(f"An unhandled error occurred: {e}", exc_info=True)
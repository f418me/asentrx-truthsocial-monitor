
import logging
import os
from typing import List, Optional
from pydantic import BaseModel, Field
from truthbrush import Api

logger = logging.getLogger(__name__)

class Status(BaseModel):
    id: int
    content: str
    url: str
    created_at: str
    account: dict

class TrueSocial:
    def __init__(self, username: str, fetch_interval_seconds: int, api_verbose_output: bool, initial_since_id: Optional[str] = None):
        self.api = Api()
        self.username = username
        self.interval_seconds = fetch_interval_seconds
        self.api_verbose_output = api_verbose_output
        self.last_known_id = initial_since_id
        
        if not self.last_known_id:
            try:
                statuses_gen = self.api.pull_statuses(
                    username=self.username,
                    replies=False,
                    since_id=None,
                    verbose=self.api_verbose_output
                )
                statuses_list = list(statuses_gen)
                if statuses_list:
                    latest_status = statuses_list[0]
                    if 'id' in latest_status:
                        self.last_known_id = str(latest_status['id'])
                        logger.info(f"No initial_since_id provided. Set last_known_id to '{self.last_known_id}' from the latest status.")
            except Exception as e:
                logger.error(f"Could not fetch the latest status to set initial_since_id: {e}")


    def fetch_new_statuses(self) -> List[Status]:
        logger.debug(f"Attempting to fetch statuses for '{self.username}' since_id: {self.last_known_id or 'None'}.")
        try:
            statuses_generator = self.api.pull_statuses(
                username=self.username, replies=False, verbose=self.api_verbose_output, since_id=self.last_known_id
            )
            statuses_dicts = list(statuses_generator)
        except Exception as e:
            logger.error(f"Error during API call to fetch statuses for '{self.username}': {e}", exc_info=True)
            return []

        if not statuses_dicts:
            logger.info(f"No new statuses found for '{self.username}' since id {self.last_known_id or 'None'}.")
            return []

        statuses = [Status(**s) for s in statuses_dicts]

        # Update last_known_id to the ID of the newest status in the fetched batch
        if statuses:
            self.last_known_id = str(statuses[0].id)
            logger.info(f"Updating last_known_id to '{self.last_known_id}'.")

        return statuses

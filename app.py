#!/usr/bin/env python3

import os
import re
import logging
import time
logging.basicConfig(level=logging.DEBUG)

from slack_bolt import App, BoltContext
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk import WebClient


app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

parent_list = set()   # List of "thread_ts" values for "share your status" messages where we care about child messages
parent_max_age = 3600 * 24 * 7   # Drop parent messages from the list after 7 days
parent_regexp = re.compile(r'^Reminder: Hello')   # Regexp to determine if the message is "share your status" one
child_regexp = re.compile(r'^[Dd]one')

@app.event("message")
def message_hello(body: dict, client: WebClient, context: BoltContext, logger: logging.Logger):
    if "thread_ts" not in body:
        logger.info(f"Processing parent message {body}")

        if re.search(parent_regexp, body["event"]["text"]):
            parent_list.add(float(body["event"]["ts"]))
            logger.info("Added parent message as it matches regexp {body}")

            now = time.time()
            parent_expiring = now - parent_max_age
            parent_count_before = len(parent_list)
            parent_list = set(filter(lambda x: x < parent_expiring, parent_list))
            parent_count_after = len(parent_list)
            if parent_count_before != parent_count_after:
                logging.info(f"Expired some parent messages. Before we had {parent_count_before} and now we have {parent_count_after} of them")

    elif body["thread_ts"] in parent_list:
        logger.info(f"Processing child message {body}")

        if re.search(childs_regexp, body["event"]["text"]):
            logger.info(f"Yay, we have a status message {body}")

            ###api_response = client.reactions_add(
            ###    channel=context.channel_id,
            ###    timestamp=body["event"]["ts"],
            ###    name="eyes",
            ###)

if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()

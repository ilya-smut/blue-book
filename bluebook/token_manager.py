import os
import json
import logging
from flask import render_template
from bluebook.confguration import Configuration

# Initialize the logger
logger = logging.getLogger(__name__)


# Function to load configuration
def load_config():
    if os.path.exists(Configuration.SystemPath.CONFIG_PATH):
        with open(Configuration.SystemPath.CONFIG_PATH, "r") as f:
            logger.debug(f'Config has been read from {Configuration.SystemPath.CONFIG_PATH}')
            return json.load(f)
        logger.info(f'Config is empty or not present.')
    return {}


# Function to save configuration
def save_config(config):
    with open(Configuration.SystemPath.CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=4)
    logger.info(f'Config has been saved into {Configuration.SystemPath.CONFIG_PATH}')


def is_token_present(config):
    if "API_TOKEN" not in config:
        logger.debug(f'API TOKEN has not been found in {Configuration.SystemPath.CONFIG_PATH}')
        return False
    elif config["API_TOKEN"] == "":
        logger.debug(f'API TOKEN is empty in {Configuration.SystemPath.CONFIG_PATH}')
        return False
    else:
        logger.debug(f'API TOKEN found in {Configuration.SystemPath.CONFIG_PATH}')
        return True


# Function to ensure the API token is present
def ensure_token(config):
    if not is_token_present(config):
        return render_template("token_prompt.html.j2")
    return None


# Function to clear the API token
def clear_token():
    if os.path.exists(Configuration.SystemPath.CONFIG_PATH):
        with open(Configuration.SystemPath.CONFIG_PATH, "w") as f:
            json.dump({"API_TOKEN": ""}, f, indent=4)
    logger.info(f'API TOKEN has been cleared in {Configuration.SystemPath.CONFIG_PATH}')
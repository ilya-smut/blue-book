import os
import json
import logging
from flask import render_template

# Initialize the logger
logger = logging.getLogger(__name__)


# Determine the correct config directory based on OS
def get_config_directory():
    if os.name == "nt":  # Windows
        return os.path.join(os.getenv("APPDATA"), "bluebook")
    else:  # macOS/Linux
        return os.path.join(os.path.expanduser("~"), ".config", "bluebook")


# Ensure the directory exists
CONFIG_DIR = get_config_directory()
os.makedirs(CONFIG_DIR, exist_ok=True)

# Set the path for the config file
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")


# Function to load configuration
def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            logger.debug(f'Config has been read from {CONFIG_PATH}')
            return json.load(f)
        logger.info(f'Config is empty or not present.')
    return {}


# Function to save configuration
def save_config(config):
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=4)
    logger.info(f'Config has been saved into {CONFIG_PATH}')


def is_token_present(config):
    if "API_TOKEN" not in config:
        logger.debug(f'API TOKEN has not been found in {CONFIG_PATH}')
        return False
    elif config["API_TOKEN"] == "":
        logger.debug(f'API TOKEN is empty in {CONFIG_PATH}')
        return False
    else:
        logger.debug(f'API TOKEN found in {CONFIG_PATH}')
        return True


# Function to ensure the API token is present
def ensure_token(config):
    if not is_token_present(config):
        return render_template("token_prompt.html.j2")
    return None


# Function to clear the API token
def clear_token():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "w") as f:
            json.dump({"API_TOKEN": ""}, f, indent=4)
    logger.info(f'API TOKEN has been cleared in {CONFIG_PATH}')
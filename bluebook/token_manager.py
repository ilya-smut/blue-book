import json
import logging
from pathlib import Path
from typing import Optional

from flask import render_template

from bluebook.configuration import Configuration

# Initialize the logger
logger = logging.getLogger("bluebook.token_manager")


# Function to load configuration
def load_config() -> dict[str, Optional[str]]:
    """
    Loads the configuration from the config file.
    Returns:
        dict: The configuration dictionary loaded from the file.
    """
    if Path.exists(Configuration.SystemPath.CONFIG_PATH):
        with Path.open(Configuration.SystemPath.CONFIG_PATH) as f:
            logger.debug("Loading config from file",
                         extra={"config_path": Configuration.SystemPath.CONFIG_PATH})
            return json.load(f)
        logger.info("Config is empty or not present.")
    return {}


# Function to save configuration
def save_config(config: dict[str, Optional[str]]) -> None:
    """
    Saves the configuration to the config file.
    Args:
        config (dict): The configuration dictionary to save.
    """
    logger.debug("Saving config to file",
                 extra={"config_path": Configuration.SystemPath.CONFIG_PATH})
    with Path.open(Configuration.SystemPath.CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=4)
    logger.info("Config has been saved",
                extra={"config_path": Configuration.SystemPath.CONFIG_PATH})


def is_token_present(config: dict[str, Optional[str]]) -> bool:
    """
    Checks if the API token is present in the configuration.
    Args:
        config (dict): The configuration dictionary.
    Returns:
        bool: True if the API token is present and not empty, False otherwise.
    """
    if "API_TOKEN" not in config:
        logger.debug("API token not found in config",
                     extra={"config_path": Configuration.SystemPath.CONFIG_PATH})
        return False
    if config["API_TOKEN"] == "":
        logger.debug("API token not set",
                     extra={"config_path": Configuration.SystemPath.CONFIG_PATH})
        return False
    logger.debug("API token is present",
                 extra={"config_path": Configuration.SystemPath.CONFIG_PATH})
    return True


# Function to ensure the API token is present
def ensure_token(config: dict[str, Optional[str]]) -> str | None:
    """
    Ensures that the API token is present in the configuration.
    If not, it returns a prompt to the user to set the token.
    Args:
        config (dict): The configuration dictionary.
    """
    if not is_token_present(config):
        return render_template("token_prompt.html.j2")
    return None


# Function to clear the API token
def clear_token() -> None:
    """
    Clears the API token from the configuration file.
    This function sets the API token to an empty string in the configuration file.
    """
    logger.debug("Clearing API token",
                 extra={"config_path": Configuration.SystemPath.CONFIG_PATH})
    if Path.exists(Configuration.SystemPath.CONFIG_PATH):
        with Path.open(Configuration.SystemPath.CONFIG_PATH, "w") as f:
            json.dump({"API_TOKEN": ""}, f, indent=4)
    logger.debug("API token has been cleared",
                 extra={"config_path": Configuration.SystemPath.CONFIG_PATH})

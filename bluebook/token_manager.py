"""Token management for the Blue Book application.

This module handles API token configuration including loading, saving,
and validating tokens. It is designed to be Flask-agnostic for better
testability and separation of concerns.
"""
import json
import logging
from typing import Optional

from bluebook.configuration import Configuration

logger = logging.getLogger("bluebook.token_manager")

# Type alias for configuration dict
ConfigDict = dict[str, Optional[str]]


def load_config() -> ConfigDict:
    """Load configuration from the config file.
    
    Returns:
        The configuration dictionary loaded from the file, or empty dict if not found.
    """
    config_path = Configuration.SystemPath.CONFIG_PATH
    if config_path.exists():
        with config_path.open() as f:
            logger.debug("Loading config from file", extra={"config_path": str(config_path)})
            try:
                return json.load(f)
            except json.JSONDecodeError:
                logger.warning("Config file is corrupted, returning empty config")
                return {}
    logger.info("Config is empty or not present.")
    return {}


def save_config(config: ConfigDict) -> None:
    """Save configuration to the config file.
    
    Args:
        config: The configuration dictionary to save.
    """
    config_path = Configuration.SystemPath.CONFIG_PATH
    logger.debug("Saving config to file", extra={"config_path": str(config_path)})
    with config_path.open("w") as f:
        json.dump(config, f, indent=4)
    logger.info("Config has been saved", extra={"config_path": str(config_path)})


def is_token_present(config: ConfigDict) -> bool:
    """Check if the API token is present in the configuration.
    
    Args:
        config: The configuration dictionary.
        
    Returns:
        True if the API token is present and not empty, False otherwise.
    """
    token = config.get("API_TOKEN")
    if token is None:
        logger.debug("API token not found in config")
        return False
    if token == "":
        logger.debug("API token is empty string")
        return False
    logger.debug("API token is present")
    return True


def get_token(config: ConfigDict | None = None) -> str | None:
    """Get the API token from configuration.
    
    Args:
        config: Optional configuration dict. If None, loads from file.
        
    Returns:
        The API token if present, None otherwise.
    """
    if config is None:
        config = load_config()
    if is_token_present(config):
        return config.get("API_TOKEN")
    return None


def ensure_token(config: ConfigDict) -> str | None:
    """Check if token is present and return a template render if not.
    
    Note: This function returns a rendered template string for backwards
    compatibility with existing code. New code should use is_token_present()
    directly and handle the template rendering in the route.
    
    Args:
        config: The configuration dictionary.
        
    Returns:
        Rendered token prompt template if token is missing, None otherwise.
    """
    if not is_token_present(config):
        # Import here to avoid circular imports and keep module Flask-agnostic
        # when not using this specific function
        from flask import render_template
        return render_template("token_prompt.html.j2")
    return None


def clear_token() -> None:
    """Clear the API token from the configuration file.
    
    Sets the API token to an empty string in the configuration file.
    """
    config_path = Configuration.SystemPath.CONFIG_PATH
    logger.debug("Clearing API token", extra={"config_path": str(config_path)})
    if config_path.exists():
        with config_path.open("w") as f:
            json.dump({"API_TOKEN": ""}, f, indent=4)
    logger.debug("API token has been cleared", extra={"config_path": str(config_path)})

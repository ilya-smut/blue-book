import os
from pathlib import Path


# Determine the correct config directory based on OS
def get_config_directory() -> Path:
    """Returns the path to the configuration directory based on the operating system."""
    if os.name == "nt":  # Windows
        return Path(os.getenv("APPDATA")) / "bluebook" # type: ignore
    # macOS/Linux
    return Path.home() / ".config" / "bluebook"

# Ensuring config directory exists
Path(get_config_directory()).mkdir(parents=True, exist_ok=True)

class Configuration:

    class SystemPath:
        CONFIG_DIR = get_config_directory()
        CONFIG_PATH = Path(CONFIG_DIR) / "config.json"
        DATABASE_PATH = Path(CONFIG_DIR) / "storage.db"

        @classmethod
        def clear_persistent(cls) -> None:
            """Clears the persistent database file."""
            if Path.exists(cls.DATABASE_PATH):
                Path.unlink(cls.DATABASE_PATH)

    class DefaultValues:
        DEFAULT_EXAM_ID = 0     # CompTIA Security+ as a default exam

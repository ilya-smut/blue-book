import os
from pathlib import Path

# Determine the correct config directory based on OS
def get_config_directory() -> str:
    """Returns the path to the configuration directory based on the operating system."""
    if os.name == "nt":  # Windows
        return Path(os.getenv("APPDATA")) / "bluebook"
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
            if os.path.exists(cls.DATABASE_PATH):
                os.remove(cls.DATABASE_PATH)

    class DefaultValues:
        DEFAULT_EXAM_ID = 0     # CompTIA Security+ as a default exam

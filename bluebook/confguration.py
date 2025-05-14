import os

# Determine the correct config directory based on OS
def get_config_directory():
    if os.name == "nt":  # Windows
        return os.path.join(os.getenv("APPDATA"), "bluebook")
    else:  # macOS/Linux
        return os.path.join(os.path.expanduser("~"), ".config", "bluebook")

# Ensuring config directory exists
os.makedirs(get_config_directory(), exist_ok=True)

class Configuration:

    class SystemPath:
        CONFIG_DIR = get_config_directory()
        CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")
        DATABASE_PATH =os.path.join(CONFIG_DIR, "storage.db")
        
        @classmethod
        def clear_persistent(cls):
            if os.path.exists(cls.DATABASE_PATH):
                os.remove(cls.DATABASE_PATH)